"""Local network organization and conservative Google name proposals."""

import asyncio
import hashlib
import re
import unicodedata
from collections import Counter

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import area_registry, device_registry, entity_registry
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .identity import ha_records, identity_index, normalize_mac


def location_label(value):
    """Validate a local display label, never a Google home ID or LAN anchor."""
    if value is None:
        return None
    if not isinstance(value, str) or any(not c.isprintable() for c in value):
        raise HomeAssistantError("Use a printable location name of at most 64 characters")
    value = " ".join(unicodedata.normalize("NFKC", value).split())
    if len(value) > 64:
        raise HomeAssistantError("Use a printable location name of at most 64 characters")
    return value or None


def location_details(label):
    """Group equal labels across entries without changing network identity."""
    return {"id": hashlib.sha256(label.casefold().encode()).hexdigest()[:24], "name": label} if label else None


def generic_name(name, station_id):
    """Do not treat arbitrary hostnames or manufacturer names as placeholders."""
    value = (name or "").strip()
    return (
        not value or value == station_id
        or value.casefold() in {
            "unnamed device", "unknown device", "unnamed", "dispositivo sem nome",
            "dispositivo desconhecido",
        }
        or bool(re.fullmatch(r"[0-9a-fA-F]{8,12}\*?", value))
        or normalize_mac(value) is not None
    )


def name_proposals(clients, records):
    """Propose names only for unique station MACs with one agreed HA name."""
    index, _ = identity_index(records)
    counts = Counter(normalize_mac(c.get("mac_address")) for c in clients.values())
    candidates, skipped = [], Counter()
    for sid, client in clients.items():
        original = client.get("google_name", client.get("name", ""))
        if not generic_name(original, sid):
            skipped["personalized_name"] += 1
            continue
        mac = normalize_mac(client.get("mac_address"))
        matches = index.get(mac, []) if mac else []
        if not mac or not matches:
            skipped["no_exact_mac_match"] += 1
            continue
        names = {record["name"].strip() for record in matches}
        if counts[mac] != 1 or len(names) != 1:
            skipped["ambiguous_mac_match"] += 1
            continue
        proposed = next(iter(names))
        if generic_name(proposed, sid) or len(proposed) > 255 or any(ord(c) < 32 for c in proposed):
            skipped["unsuitable_ha_name"] += 1
            continue
        candidates.append({"station_id": sid, "google_name": original,
                           "proposed_name": proposed, "mac_address": mac,
                           "ha_device_id": min(record["id"] for record in matches), "match": "mac"})
    return sorted(candidates, key=lambda row: (row["proposed_name"].casefold(), row["station_id"])), dict(skipped)


class WifiManagement:
    """Persist point mappings while keeping client device areas independent."""

    def __init__(self, hass, entry):
        self.hass = hass
        self.entry = entry
        self._store = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.areas")
        self._locations_store = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.locations")
        self._lock = asyncio.Lock()
        self._loaded = False
        self.mappings = {}
        self.locations = {}

    async def async_load(self):
        if self._loaded:
            return
        async with self._lock:
            if self._loaded:
                return
            saved = await self._store.async_load()
            if isinstance(saved, dict):
                self.mappings = {nid: {pid: aid for pid, aid in points.items()
                                       if isinstance(pid, str) and isinstance(aid, str)}
                                 for nid, points in saved.items() if isinstance(nid, str) and isinstance(points, dict)}
            saved_locations = await self._locations_store.async_load()
            if isinstance(saved_locations, dict):
                for nid, label in saved_locations.items():
                    if isinstance(nid, str) and isinstance(label, str):
                        try:
                            if valid := location_label(label):
                                self.locations[nid] = valid
                        except HomeAssistantError:
                            continue
            self._loaded = True

    def apply(self, snapshot):
        registry = area_registry.async_get(self.hass)
        for nid, network in snapshot["networks"].items():
            network["location"] = location_details(self.locations.get(nid))
            for pid, point in network["points"].items():
                area = registry.async_get_area(self.mappings.get(nid, {}).get(pid, ""))
                point.update(mapped_area_id=area.id if area else None, mapped_area=area.name if area else None)
                self.sync_point_device_area(nid, pid, point.get("mapped_area_id"))
            for client in network["clients"].values():
                point = network["points"].get(client.get("ap_id"), {})
                current = (network.get("reachable") is not False and client.get("connected") is True
                           and client.get("connection_type") == "WIRELESS" and point.get("online") is True
                           and point.get("reachable") is not False)
                client.update(associated_area_id=point.get("mapped_area_id") if current else None,
                              associated_area=point.get("mapped_area") if current else None,
                              area_source="wifi_point" if current and point.get("mapped_area_id") else None)
        return snapshot

    def sync_point_device_area(self, nid, pid, area_id, previous_area_id=None):
        """Fill an unassigned point area; retain a different manual HA assignment."""
        if not area_id or not area_registry.async_get(self.hass).async_get_area(area_id):
            return
        registry = device_registry.async_get(self.hass)
        own = registry.async_get_device_by_identifier(
            (DOMAIN, f"{self.entry.entry_id}:{nid}:point:{pid}"), self.entry.entry_id
        )
        if own and own.area_id != area_id and own.area_id in (None, previous_area_id):
            registry.async_update_device(own.id, area_id=area_id)

    async def async_set_location(self, nid, name):
        label = location_label(name)
        async with self._lock:
            updated = dict(self.locations)
            if label:
                updated[nid] = label
            else:
                updated.pop(nid, None)
            await self._locations_store.async_save(updated)
            self.locations = updated
        return location_details(label)

    async def async_set_area(self, nid, pid, area_id):
        if area_id and not area_registry.async_get(self.hass).async_get_area(area_id):
            raise HomeAssistantError("Select an existing Home Assistant area")
        async with self._lock:
            previous_area_id = self.mappings.get(nid, {}).get(pid)
            updated = {key: dict(points) for key, points in self.mappings.items()}
            points = updated.setdefault(nid, {})
            if area_id:
                points[pid] = area_id
            else:
                points.pop(pid, None)
            await self._store.async_save(updated)
            self.mappings = updated
            self.sync_point_device_area(nid, pid, area_id, previous_area_id)

    def response(self, nid, network):
        """Use cached discovery; opening management does not poll Google."""
        registry = entity_registry.async_get(self.hass)
        entities = {entity.unique_id: entity.entity_id for entity in
                    entity_registry.async_entries_for_config_entry(registry, self.entry.entry_id)
                    if not entity.disabled_by and self.hass.states.get(entity.entity_id)}

        def target(kind, sid, metric):
            return entities.get(f"{self.entry.entry_id}:{nid}:{kind}:{sid}:{metric}")

        candidates, skipped = name_proposals(network["clients"], ha_records(self.hass))
        for row in candidates:
            row["entity_id"] = target("client", row["station_id"], "point")
        return {
            "network_id": nid, "scope": f"{self.entry.entry_id}:{nid}", "name": network["name"],
            "location": location_details(self.locations.get(nid)),
            "client_area_sync": self.entry.runtime_data.client_areas.response(nid),
            "entity_id": target("network", nid, "diagnosis"),
            "areas": sorted([{"id": area.id, "name": area.name} for area in
                             area_registry.async_get(self.hass).areas.values()], key=lambda row: row["name"].casefold()),
            "points": [{"id": pid, "name": point["name"], "entity_id": target("point", pid, "clients"),
                        "area_id": point.get("mapped_area_id"), "area_name": point.get("mapped_area"),
                        "online": point.get("online"), "is_root": point.get("is_root")}
                       for pid, point in network["points"].items()],
            "name_candidates": candidates, "names_skipped": skipped,
            "rename": self.entry.runtime_data.names.response(nid),
            "available": self.entry.runtime_data.last_update_success and network.get("reachable") is not False,
        }
