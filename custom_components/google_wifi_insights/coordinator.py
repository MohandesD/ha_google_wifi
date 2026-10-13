"""One bounded poll shared by all Google WiFi entities."""

import logging
import asyncio
from collections import Counter
from copy import deepcopy
from datetime import timedelta

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ApiError, AuthError, CloudClient, LocalClient, RateLimitError
from .const import CONF_INTERVAL, DEFAULT_INTERVAL, DOMAIN
from .model import apply_roaming
from .identity import enrich_snapshot
from .shelly_radio import ShellyRadio
from .telemetry import timestamp
from .actions import build_action
from .capabilities import ADVANCED
from .operations import MONITORED_ACTIONS
from homeassistant.exceptions import HomeAssistantError
from datetime import UTC, datetime

OPERATION_POLL_SECONDS = 5


class WifiCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        super().__init__(
            hass,
            logging.getLogger(__name__),
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(
                seconds=entry.options.get(CONF_INTERVAL, DEFAULT_INTERVAL)
            ),
        )
        session = async_get_clientsession(hass)
        self.radio = ShellyRadio(session)
        self._radio_update_lock = asyncio.Lock()
        self._operation_tasks = {}
        self._stopping = False
        entry.async_on_unload(self._cancel_operation_tasks)
        data = entry.data
        self.client = (
            LocalClient(session, data["points"])
            if data["mode"] == "local"
            else CloudClient(
                session,
                hass.async_add_executor_job,
                data["email"],
                data["master_token"],
                data["android_id"],
            )
        )

    async def _async_update_data(self):
        try:
            snapshot = enrich_snapshot(self.hass, self.config_entry, apply_roaming(await self.client.snapshot(), self.data))
            self._merge_local_points(snapshot)
            async with self._radio_update_lock:
                snapshot = await self.radio.enrich(snapshot)
            if isinstance(self.client, CloudClient):
                for nid, network in snapshot["networks"].items():
                    operations = deepcopy(self.client._operations.get(nid, []))
                    network.update(operations=operations, last_operation=operations[-1]["state"] if operations else "NONE")
            return snapshot
        except AuthError:
            raise ConfigEntryAuthFailed("Google authentication needs renewal") from None
        except RateLimitError as error:
            raise UpdateFailed(
                "Google requested a polling pause", retry_after=error.retry_after
            ) from None
        except ApiError as error:
            raise UpdateFailed(str(error)) from None

    def _merge_local_points(self, snapshot):
        """Reuse recent LAN status already collected by our local-mode entry."""
        if self.config_entry.data["mode"] != "cloud":
            return
        recent = {}
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            other = getattr(entry, "runtime_data", None)
            if entry is self.config_entry or entry.data.get("mode") != "local" or not isinstance(other, WifiCoordinator) or not other.last_update_success:
                continue
            for network in (other.data or {}).get("networks", {}).values():
                for point in network["points"].values():
                    observed = timestamp(point.get("local_status_at"))
                    if point.get("reachable") and observed and 0 <= (datetime.now(UTC)-observed).total_seconds() <= max(300, 2*entry.options.get(CONF_INTERVAL, DEFAULT_INTERVAL)):
                        recent[point["host"]] = point
        current_networks = [network for network in snapshot["networks"].values()
                            if any(p.get("is_root") is True and p.get("online") is True for p in network["points"].values())]
        hosts = Counter(p.get("host") for network in current_networks for p in network["points"].values() if p.get("online") is True)
        for network in current_networks:
            for point in network["points"].values():
                if point.get("online") is not True or hosts[point.get("host")] != 1:
                    continue
                local = recent.get(point.get("host"))
                if local:
                    role = local.get("local_status", {}).get("system", {}).get("groupRole")
                    if role not in ("root", "leaf") or (role == "root") != point.get("is_root"):
                        continue
                    point["uptime_seconds"] = local.get("uptime_seconds")
                    point["uptime_source"] = "google_local_status"
                    point["google_telemetry"]["localStatus"] = deepcopy(local.get("local_status", {}))
                    point["google_telemetry"]["localStatusRetrievedAt"] = local["local_status_at"]

    async def async_set_roaming(self, network_id, client_id, key, value):
        async with self._radio_update_lock:
            item = (self.data or {}).get("networks", {}).get(network_id, {}).get("clients", {}).get(client_id, {})
            measured = await self.radio.set_roaming(item, key, value)
            updated = deepcopy(self.data)
            updated["networks"][network_id]["clients"][client_id].update(measured)
            self.async_set_updated_data(updated)

    async def async_google_action(self, network_id, kind, item_id, action, parameters=None, context=None):
        """Write only explicit cloud targets; report acknowledgement truthfully."""
        if context and context.user_id:
            user = await self.hass.auth.async_get_user(context.user_id)
            if not user or not user.is_admin:
                raise HomeAssistantError("Google network controls require a Home Assistant administrator")
        elif action in ADVANCED:
            raise HomeAssistantError("Advanced Google actions require an interactive administrator")
        network = (self.data or {}).get("networks", {}).get(network_id, {})
        method, path, payload = build_action(network, network_id, action, kind, item_id, parameters or {})
        if not isinstance(self.client, CloudClient):
            raise HomeAssistantError("Google account access is required")
        item = network if kind == "network" else network["points" if kind == "point" else "clients"][item_id]
        preparation = {}
        if action == "test_mesh":
            from urllib.parse import quote
            server_id = next(pid for pid, point in network["points"].items() if point.get("is_root") is True)
            preparation["prepare_path"] = "accesspoints/"+quote(server_id, safe="")+"/localSpeedTest"
        try:
            result = await self.client.action(network_id, action, path, method, payload,
                                             target_kind=kind, target_id=item_id, target_name=item["name"],
                                             on_update=lambda: self._publish_operations(network_id), **preparation)
        except ApiError as error:
            self._publish_operations(network_id)
            raise HomeAssistantError(str(error)) from None
        updated = deepcopy(self.data)
        current = updated["networks"][network_id]
        current["last_operation"] = result["state"]
        current["operations"] = deepcopy(self.client._operations.get(network_id, []))
        current.get("capabilities", {}).get("actions", {}).get(action, {}).update(state="accepted")
        if action in MONITORED_ACTIONS:
            self.data = updated
            self.async_update_listeners()
            if network_id not in self._operation_tasks:
                self._operation_tasks[network_id] = self.config_entry.async_create_background_task(
                    self.hass, self._watch_operations(network_id), f"{DOMAIN} operation status", eager_start=False)
        else:
            # Read back settings and completed test results without optimistic values.
            self.async_set_updated_data(updated)
            await self.async_request_refresh()
        return result

    def _publish_operations(self, network_id):
        if self._stopping or network_id not in (self.data or {}).get("networks", {}):
            return
        updated = deepcopy(self.data)
        operations = deepcopy(self.client._operations.get(network_id, []))
        updated["networks"][network_id].update(operations=operations, last_operation=operations[-1]["state"] if operations else "NONE")
        # A successful operation lookup is not a successful network-metrics poll.
        self.data = updated
        self.async_update_listeners()

    async def _watch_operations(self, network_id):
        """Poll only operation status every five seconds after an explicit action."""
        try:
            while self.client.has_pending_operations(network_id):
                await asyncio.sleep(OPERATION_POLL_SECONDS)
                before = deepcopy(self.client._operations.get(network_id, []))
                try:
                    await self.client._poll_operations(network_id)
                except RateLimitError:
                    pass  # The client honours Google's retry window on the next poll.
                except AuthError:
                    break  # Normal coordinator refresh starts the HA reauthentication flow.
                finally:
                    if before != self.client._operations.get(network_id, []):
                        self._publish_operations(network_id)
        finally:
            self._operation_tasks.pop(network_id, None)
        if not self._stopping:
            self.config_entry.async_create_background_task(
                self.hass, self.async_request_refresh(), f"{DOMAIN} operation readback")

    def _cancel_operation_tasks(self):
        self._stopping = True
        for task in self._operation_tasks.values():
            task.cancel()
        self._operation_tasks.clear()
