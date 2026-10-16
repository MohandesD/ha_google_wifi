"""One bounded poll shared by all Google WiFi entities."""

import asyncio
import logging
from collections import Counter
from copy import deepcopy
from datetime import UTC, datetime, timedelta

from homeassistant.core import callback
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers import area_registry, device_registry
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .actions import build_action
from .api import ApiError, AuthError, CloudClient, LocalClient, RateLimitError
from .capabilities import ADVANCED, DESTRUCTIVE
from .const import (
    CONF_ADVANCED,
    CONF_DESTRUCTIVE,
    CONF_INTERVAL,
    DEFAULT_INTERVAL,
    DOMAIN,
)
from .identity import enrich_snapshot
from .information import apply_network_information, apply_point_information
from .lan import LanDiagnostics
from .management import WifiManagement
from .model import apply_roaming
from .naming import NameSync
from .operations import MONITORED_ACTIONS
from .shelly_radio import ShellyRadio
from .telemetry import timestamp

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
        self.lan = hass.data.setdefault(DOMAIN, {}).setdefault("lan_diagnostics", LanDiagnostics(session))
        self.radio = ShellyRadio(session)
        self._radio_update_lock = asyncio.Lock()
        self._operation_tasks = {}
        self._failed_networks = set()
        self._stopping = False
        self.management = WifiManagement(hass, entry)
        self.names = NameSync(self)
        self._name_task = None
        entry.async_on_unload(self._cancel_name_task)
        entry.async_on_unload(hass.bus.async_listen(area_registry.EVENT_AREA_REGISTRY_UPDATED, self._areas_changed))
        entry.async_on_unload(self._cancel_operation_tasks)
        data = entry.data
        self.client = (
            LocalClient(session, data["points"], self.lan)
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
            await self.management.async_load()
            await self.names.async_load()
            snapshot = enrich_snapshot(self.hass, self.config_entry, apply_roaming(await self.client.snapshot(), self.data))
            self._merge_local_points(snapshot)
            if isinstance(self.client, CloudClient):
                configured_hosts = {p["host"] for entry in self.hass.config_entries.async_entries(DOMAIN)
                                    if entry.data.get("mode") == "local" for p in entry.data.get("points", [])}
                await self.lan.enrich_cloud(snapshot, configured_hosts, self.config_entry.options.get("lan_gateway"))
            for network in snapshot["networks"].values():
                for point in network["points"].values():
                    apply_point_information(point)
                apply_network_information(network)
            async with self._radio_update_lock:
                snapshot = await self.radio.enrich(snapshot)
            self._update_device_metadata(snapshot)
            if isinstance(self.client, CloudClient):
                for nid, network in snapshot["networks"].items():
                    operations = deepcopy(self.client._operations.get(nid, []))
                    network.update(operations=operations, last_operation=operations[-1]["state"] if operations else "NONE")
                failures = snapshot.get("network_errors", {})
                # Reuse only identities/layout from a failed network. All its entities
                # become unavailable; no stale RSSI, traffic or controls look current.
                for nid in failures:
                    previous = (self.data or {}).get("networks", {}).get(nid)
                    if previous:
                        snapshot["networks"][nid] = {**deepcopy(previous), "reachable": False}
                if set(failures) != self._failed_networks:
                    logger = logging.getLogger(__name__)
                    if failures:
                        logger.warning("%d Google WiFi network(s) unavailable; other networks continue updating", len(failures))
                    else:
                        logger.info("All Google WiFi networks are available again")
                    self._failed_networks = set(failures)
            for nid, network in snapshot["networks"].items():
                network["name_sync"] = self.names.summary(nid)
            return self.management.apply(snapshot)
        except AuthError:
            raise ConfigEntryAuthFailed("Google authentication needs renewal") from None
        except RateLimitError as error:
            raise UpdateFailed(
                "Google requested a polling pause", retry_after=error.retry_after
            ) from None
        except ApiError as error:
            raise UpdateFailed(str(error)) from None

    @callback
    def async_start_name_sync(self):
        self.config_entry.async_on_unload(self.async_add_listener(self._schedule_name_sync))
        self._schedule_name_sync()

    @callback
    def _schedule_name_sync(self):
        if (not self._stopping and self.last_update_success and self.data
                and isinstance(self.client, CloudClient) and not self.names._write_lock.locked()
                and (self._name_task is None or self._name_task.done()) and self.names.automatic_due()):
            self._name_task = self.config_entry.async_create_background_task(
                self.hass, self.names.async_automatic(), f"{DOMAIN} automatic names", eager_start=False)

    @callback
    def _cancel_name_task(self):
        if self._name_task and not self._name_task.done():
            self._name_task.cancel()

    @callback
    def _publish_name_status(self, nid):
        if nid in (self.data or {}).get("networks", {}):
            updated = deepcopy(self.data)
            updated["networks"][nid]["name_sync"] = self.names.summary(nid)
            self.data = updated
            self.async_update_listeners()

    @callback
    def _publish_verified_name(self, nid, sid, name):
        if self._stopping or sid not in (self.data or {}).get("networks", {}).get(nid, {}).get("clients", {}):
            return
        updated = deepcopy(self.data)
        updated["networks"][nid]["clients"][sid]["google_name"] = name
        self.data = enrich_snapshot(self.hass, self.config_entry, updated)
        # A name read-back is not a successful full network-metrics poll.
        self.async_update_listeners()

    @callback
    def _areas_changed(self, event):
        """Area renames/deletions update local sensors without a Google request."""
        if self.data and self.last_update_success:
            self.async_set_updated_data(self.management.apply(deepcopy(self.data)))

    async def async_set_point_area(self, nid, pid, area_id):
        network = self._current_network(nid)
        if pid not in network["points"]:
            raise HomeAssistantError("Select a current Google WiFi point")
        await self.management.async_set_area(nid, pid, area_id)
        # A poll can fail while storage is being written. Saving a local mapping
        # must not turn stale cloud measurements into a successful update.
        if self.last_update_success:
            self.async_set_updated_data(self.management.apply(deepcopy(self.data)))

    async def async_set_network_location(self, nid, name):
        """Save local organization even during outages, without polling Google."""
        if self._stopping or nid not in (self.data or {}).get("networks", {}):
            raise HomeAssistantError("Select a known Google WiFi network")
        location = await self.management.async_set_location(nid, name)
        if not self._stopping:
            # Updating metadata must not clear an existing coordinator failure.
            updated = self.management.apply(deepcopy(self.data))
            if self.last_update_success:
                self.async_set_updated_data(updated)
            else:
                self.data = updated
                self.async_update_listeners()
        return location

    def _update_device_metadata(self, snapshot):
        """Refresh only our network/point records, retaining user names and IDs."""
        registry = device_registry.async_get(self.hass)
        for nid, network in snapshot["networks"].items():
            rows = [(f"{self.config_entry.entry_id}:{nid}", network)]
            rows.extend((f"{self.config_entry.entry_id}:{nid}:point:{pid}", point)
                        for pid, point in network["points"].items())
            for identifier, item in rows:
                own = registry.async_get_device_by_identifier((DOMAIN, identifier), self.config_entry.entry_id)
                if not own:
                    continue
                changes = {}
                if item.get("name") and own.name != item["name"]:
                    changes["name"] = item["name"]
                if item.get("firmware") and own.sw_version != item["firmware"]:
                    changes["sw_version"] = item["firmware"]
                if changes:
                    registry.async_update_device(own.id, **changes)

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
            network = self._current_network(network_id)
            item = network.get("clients", {}).get(client_id, {})
            measured = await self.radio.set_roaming(item, key, value)
            updated = deepcopy(self.data)
            updated["networks"][network_id]["clients"][client_id].update(measured)
            self.async_set_updated_data(updated)

    def _current_network(self, network_id):
        """Reject writes using an unsuccessful poll or a stale network snapshot."""
        network = (self.data or {}).get("networks", {}).get(network_id, {})
        if not self.last_update_success or not network or network.get("reachable") is False:
            raise HomeAssistantError("Google WiFi network is unavailable; wait for a successful update")
        return network

    async def async_google_action(self, network_id, kind, item_id, action, parameters=None, context=None):
        """Write only explicit cloud targets; report acknowledgement truthfully."""
        if context and context.user_id:
            user = await self.hass.auth.async_get_user(context.user_id)
            if not user or not user.is_admin:
                raise HomeAssistantError("Google network controls require a Home Assistant administrator")
        elif action in ADVANCED:
            raise HomeAssistantError("Advanced Google actions require an interactive administrator")
        network = self._current_network(network_id)
        if action in ADVANCED and not self.config_entry.options.get(CONF_ADVANCED, False):
            raise HomeAssistantError("Experimental Google actions are disabled in the integration options")
        if action in DESTRUCTIVE and not self.config_entry.options.get(CONF_DESTRUCTIVE, False):
            raise HomeAssistantError("Destructive Google actions are disabled in the integration options")
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
