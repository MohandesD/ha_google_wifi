"""Opt-in Google display-name remediation with durable intent and read-back."""

import asyncio
import time
from copy import deepcopy
from uuid import uuid4

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store

from .api import ApiError, CloudClient
from .const import DOMAIN
from .identity import ha_records, normalize_mac
from .management import name_proposals
from .operations import now_iso

AUTO_INTERVAL = 300
AUTO_BATCH_SIZE = 3
HISTORY_LIMIT = 100


class NameSync:
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.hass = coordinator.hass
        self._store = Store(self.hass, 1, f"{DOMAIN}.{coordinator.config_entry.entry_id}.names")
        self._storage_lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()
        self._loaded = False
        self._data = {}
        self._next_auto = 0

    async def async_load(self):
        if self._loaded:
            return
        async with self._storage_lock:
            if not self._loaded:
                saved = await self._store.async_load()
                self._data = {nid: row for nid, row in (saved or {}).items() if isinstance(nid, str) and isinstance(row, dict)} if isinstance(saved, dict) else {}
                for row in self._data.values():
                    if any(r.get("state") == "unconfirmed" for r in row.get("history", [])):
                        row["paused_reason"] = row.get("paused_reason") or "previous_write_unconfirmed"
                self._loaded = True

    def network(self, nid):
        return self._data.get(nid, {})

    def summary(self, nid):
        data = self.network(nid)
        history = data.get("history", [])
        return {"enabled": data.get("enabled") is True, "paused_reason": data.get("paused_reason"),
                "last_state": history[-1]["state"] if history else "idle",
                "verified_count": sum(r["state"] == "verified" for r in history),
                "unconfirmed_count": sum(r["state"] == "unconfirmed" for r in history)}

    def response(self, nid):
        history = self.network(nid).get("history", [])
        return {**self.summary(nid), "writable": True, "state": "schema_verified_android_client",
                "provider_state": history[-1]["state"] if history else "not_tested",
                "history": deepcopy(self.network(nid).get("history", [])[-20:]),
                "excluded_station_ids": list(self.network(nid).get("excluded", []))}

    async def _change(self, nid, change):
        async with self._storage_lock:
            updated = deepcopy(self._data)
            row = updated.setdefault(nid, {"enabled": False, "history": [], "excluded": []})
            change(row)
            await self._store.async_save(updated)
            self._data = updated
        self.coordinator._publish_name_status(nid)

    async def async_set_enabled(self, nid, enabled):
        def update(row):
            row.update(enabled=enabled, paused_reason=None)
        await self._change(nid, update)
        if enabled:
            self._next_auto = 0

    def _client(self, nid, sid):
        if self.coordinator._stopping:
            raise HomeAssistantError("Google WiFi integration is unloading")
        network = self.coordinator._current_network(nid)
        if not isinstance(self.coordinator.client, CloudClient) or sid not in network["clients"]:
            raise HomeAssistantError("Select a current Google account client")
        return network

    def _proposal(self, nid, sid, expected_name, expected_mac, expected_ha_name):
        network = self._client(nid, sid)
        candidates, _ = name_proposals(network["clients"], ha_records(self.hass))
        row = next((r for r in candidates if r["station_id"] == sid), None)
        if not row or (row["google_name"], row["mac_address"], row["proposed_name"]) != (expected_name, normalize_mac(expected_mac), expected_ha_name):
            raise HomeAssistantError("The Google name or exact HA MAC match changed; refresh the preview")
        if not network["clients"][sid].get("connected"):
            raise HomeAssistantError("The selected client must be connected")
        name = row["proposed_name"]
        if not 1 <= len(name) <= 63 or any(ord(c) < 32 or ord(c) == 127 for c in name):
            raise HomeAssistantError("Automatic names must contain 1 to 63 characters without control characters")
        return row

    def _pending(self, nid, sid):
        return any(r["station_id"] == sid and r["state"] == "unconfirmed" for r in self.network(nid).get("history", []))

    async def _record(self, nid, record, *, exclude=False):
        def update(row):
            history = row.setdefault("history", [])
            if len(history) >= HISTORY_LIMIT:
                removable = next((r for r in history if r["state"] != "unconfirmed"), None)
                if removable is None:
                    raise HomeAssistantError("Resolve unconfirmed name changes before adding more")
                history.remove(removable)
            history.append(record)
            if exclude:
                row["excluded"] = list(set(row.get("excluded", [])) | {record["station_id"]})
        await self._change(nid, update)

    async def _finish(self, nid, request_id, state, *, pause=None, observed_name=None):
        def update(row):
            record = next(r for r in row["history"] if r["request_id"] == request_id)
            record.update(state=state, updated_at=now_iso())
            if observed_name is not None:
                record["observed_name"] = observed_name
            if pause:
                row["paused_reason"] = pause
        await self._change(nid, update)

    async def _send(self, nid, record, name, *, restore_automatic=False):
        """Intent is already durable. An empty 2xx response proves no completion."""
        request_id, sid = record["request_id"], record["station_id"]
        acknowledged = False
        try:
            self._client(nid, sid)
            await self.coordinator.client.set_station_name(nid, sid, name)
            acknowledged = True
            if self.coordinator._stopping:
                return deepcopy(record)
            fresh = await self.coordinator.client.station_identity(nid, sid)
            matches = fresh["name"] == name if name is not None else (
                restore_automatic and (not fresh["raw_name"] or fresh["name"] == fresh["automatic_name"] or fresh["name"] == record["new_name"]))
            if fresh["mac"] != record["mac_address"] or not matches:
                await self._finish(nid, request_id, "unconfirmed", pause="readback_mismatch")
            else:
                await self._finish(nid, request_id, "verified", observed_name=fresh["name"])
                self.coordinator._publish_verified_name(nid, sid, fresh["name"])
        except (ApiError, TimeoutError) as error:
            if self.coordinator._stopping:
                return deepcopy(record)
            rejected = not acknowledged and isinstance(error, ApiError) and error.status is not None and 400 <= error.status < 500
            await self._finish(nid, request_id, "rejected" if rejected else "unconfirmed", pause="request_rejected" if rejected else "delivery_or_readback_unconfirmed")
        return deepcopy(next(r for r in self.network(nid)["history"] if r["request_id"] == request_id))

    async def async_rename(self, nid, sid, expected_name, expected_mac, expected_ha_name, *, automatic=False):
        async with self._write_lock:
            row = self._proposal(nid, sid, expected_name, expected_mac, expected_ha_name)
            if self._pending(nid, sid):
                raise HomeAssistantError("Verify the unconfirmed name change before sending another request")
            async with self.coordinator.client._action_lock:
                try:
                    fresh = await self.coordinator.client.station_identity(nid, sid)
                except (ApiError, TimeoutError):
                    raise HomeAssistantError("Fresh Google identity could not be verified; no rename was sent") from None
                if (fresh["name"], fresh["mac"]) != (expected_name, row["mac_address"]):
                    raise HomeAssistantError("The current Google name or MAC changed; no rename was sent")
                self._proposal(nid, sid, expected_name, expected_mac, expected_ha_name)
                if automatic and (not self.network(nid).get("enabled") or self.network(nid).get("paused_reason") or sid in self.network(nid).get("excluded", [])):
                    return None
                record = {"request_id": uuid4().hex, "station_id": sid, "mac_address": row["mac_address"],
                          "ha_device_id": row["ha_device_id"], "old_name": fresh["name"], "new_name": row["proposed_name"],
                          "restore_automatic": not fresh["raw_name"] or fresh["raw_name"] == fresh["automatic_name"],
                          "state": "unconfirmed", "kind": "rename", "automatic": automatic, "updated_at": now_iso()}
                await self._record(nid, record)
                try:
                    self._proposal(nid, sid, expected_name, expected_mac, expected_ha_name)
                except HomeAssistantError:
                    if not self.coordinator._stopping:
                        await self._finish(nid, record["request_id"], "cancelled")
                    raise
                if automatic and not self.network(nid).get("enabled"):
                    await self._finish(nid, record["request_id"], "cancelled")
                    return None
                return await self._send(nid, record, row["proposed_name"])

    async def async_verify(self, nid, request_id):
        async with self._write_lock:
            record = self._find(nid, request_id)
            self._client(nid, record["station_id"])
            try:
                fresh = await self.coordinator.client.station_identity(nid, record["station_id"])
            except (ApiError, TimeoutError):
                raise HomeAssistantError("Google read-back is unavailable; no write was sent") from None
            desired = record["new_name"]
            matches = fresh["name"] == desired or (record["kind"] == "undo" and record["restore_automatic"] and (not fresh["raw_name"] or fresh["name"] == fresh["automatic_name"]))
            if fresh["mac"] == record["mac_address"] and matches:
                await self._finish(nid, request_id, "verified", observed_name=fresh["name"])
                self.coordinator._publish_verified_name(nid, record["station_id"], fresh["name"])
            return deepcopy(self._find(nid, request_id))

    def _find(self, nid, request_id):
        record = next((r for r in self.network(nid).get("history", []) if r["request_id"] == request_id), None)
        if not record:
            raise HomeAssistantError("Select a name change from this network's history")
        return record

    async def async_undo(self, nid, request_id):
        async with self._write_lock:
            original = self._find(nid, request_id)
            sid = original["station_id"]
            self._client(nid, sid)
            if original["kind"] != "rename" or original["state"] != "verified" or self._pending(nid, sid):
                raise HomeAssistantError("Only a verified rename without an unconfirmed request can be undone")
            if next(r for r in reversed(self.network(nid)["history"]) if r["station_id"] == sid)["request_id"] != request_id:
                raise HomeAssistantError("A later request exists for this client; select the latest change")
            async with self.coordinator.client._action_lock:
                try:
                    fresh = await self.coordinator.client.station_identity(nid, sid)
                except (ApiError, TimeoutError):
                    raise HomeAssistantError("Fresh Google identity could not be verified; no undo was sent") from None
                if fresh["name"] != original["new_name"] or fresh["mac"] != original["mac_address"]:
                    raise HomeAssistantError("Google name or MAC changed since this rename; undo was refused")
                record = {**original, "request_id": uuid4().hex, "undo_of": request_id, "kind": "undo",
                          "old_name": original["new_name"], "new_name": original["old_name"], "state": "unconfirmed", "automatic": False, "updated_at": now_iso()}
                await self._record(nid, record, exclude=True)
                self._client(nid, sid)
                return await self._send(nid, record, None if original["restore_automatic"] else original["old_name"], restore_automatic=original["restore_automatic"])

    def automatic_due(self):
        return time.monotonic() >= self._next_auto and any(row.get("enabled") and not row.get("paused_reason") for row in self._data.values())

    async def async_automatic(self):
        self._next_auto = time.monotonic() + AUTO_INTERVAL
        remaining = AUTO_BATCH_SIZE
        for nid, network in list((self.coordinator.data or {}).get("networks", {}).items()):
            settings = self.network(nid)
            if not settings.get("enabled") or settings.get("paused_reason") or network.get("reachable") is False:
                continue
            candidates, _ = name_proposals(network["clients"], ha_records(self.hass))
            for row in candidates:
                if not remaining:
                    return
                sid = row["station_id"]
                attempted = any(r["station_id"] == sid and r["state"] != "cancelled" for r in settings.get("history", []))
                if sid in settings.get("excluded", []) or attempted or not network["clients"][sid].get("connected") or len(row["proposed_name"]) > 63:
                    continue
                remaining -= 1
                try:
                    await self.async_rename(nid, sid, row["google_name"], row["mac_address"], row["proposed_name"], automatic=True)
                except HomeAssistantError:
                    continue
                if self.network(nid).get("paused_reason"):
                    break
