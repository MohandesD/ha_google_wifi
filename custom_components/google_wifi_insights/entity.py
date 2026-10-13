"""Dynamic entities with stable IDs and device relationships."""

from homeassistant.core import callback
from homeassistant.helpers import device_registry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


@callback
def add_dynamic_entities(coordinator, entry, async_add_entities, factory):
    seen = set()

    @callback
    def discover():
        entities = []
        for network_id, network in (coordinator.data or {}).get("networks", {}).items():
            for kind, items in (
                ("network", {network_id: network}),
                ("point", network["points"]),
                ("client", network["clients"]),
            ):
                for item_id, item in items.items():
                    key = (network_id, kind, item_id)
                    if key in seen:
                        continue
                    discovered = factory(network_id, kind, item_id, item)
                    if discovered:
                        seen.add(key)
                        entities.extend(discovered)
        if entities:
            async_add_entities(entities)

    discover()
    entry.async_on_unload(coordinator.async_add_listener(discover))


class WifiEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, network_id, kind, item_id, item, key):
        super().__init__(coordinator)
        self.network_id, self.kind, self.item_id = network_id, kind, item_id
        self.key = key
        self._entry_id = entry.entry_id
        self._scope = f"{entry.entry_id}:{network_id}"
        self._attr_unique_id = f"{entry.entry_id}:{network_id}:{kind}:{item_id}:{key}"
        network_identifier = f"{entry.entry_id}:{network_id}"
        identifier = (
            network_identifier
            if kind == "network"
            else f"{network_identifier}:{kind}:{item_id}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, identifier)},
            name=item["name"],
            manufacturer="Google" if kind != "client" else None,
            model="Google WiFi network"
            if kind == "network"
            else "Google WiFi point"
            if kind == "point"
            else "Network client",
        )
        if kind != "network":
            network = coordinator.data["networks"][network_id]
            parent = device_registry.async_get(coordinator.hass).async_get_or_create(
                config_entry_id=entry.entry_id,
                identifiers={(DOMAIN, network_identifier)},
                name=network["name"],
                manufacturer="Google",
                model="Google WiFi network",
            )
            self._attr_device_info["via_device_id"] = parent.id
        if kind == "point" and item.get("firmware"):
            self._attr_device_info["sw_version"] = item["firmware"]
        if kind == "client" and item.get("ha_device_id"):
            self._attr_device_info["configuration_url"] = f"homeassistant://config/devices/device/{item['ha_device_id']}"

    @property
    def item(self):
        network = (
            (self.coordinator.data or {}).get("networks", {}).get(self.network_id, {})
        )
        return (
            network
            if self.kind == "network"
            else network.get("points" if self.kind == "point" else "clients", {}).get(
                self.item_id, {}
            )
        )

    @property
    def available(self):
        return (
            super().available and bool(self.item) and self.item.get("reachable", True)
        )

    @property
    def extra_state_attributes(self):
        item = self.item
        attributes = {
            "data_source": item.get("source"),
            "gwi_kind": self.kind,
            "gwi_metric": self.key,
            "device_name": item.get("name"),
            "gwi_scope": self._scope,
            "gwi_network_id": self.network_id,
            "gwi_item_id": self.item_id,
        }
        if self.kind == "client":
            attributes.update(
                {
                    key: item.get(key)
                    for key in (
                        "point",
                        "ap_id",
                        "ip_address",
                        "ip_addresses",
                        "mac_address",
                        "google_name",
                        "ha_device_id",
                        "ha_device_name",
                        "identity_match",
                        "name_source",
                        "connection_type",
                        "roams_since_start",
                        "last_roam",
                        "connected",
                        "rssi",
                        "signal_quality",
                        "quality_source",
                        "google_rating",
                        "google_rating_index",
                        "wireless_band",
                        "download_mbps",
                        "upload_mbps",
                        "traffic_source",
                        "rssi_source",
                        "rssi_observed_at",
                        "wifi_bssid",
                        "wifi_channel",
                        "roaming_supported",
                        "radio_available",
                        "roam_rssi_threshold",
                        "roam_interval",
                        "gwi_device_id",
                    )
                }
            )
            own = device_registry.async_get(self.hass).async_get_device_by_identifier(
                (DOMAIN, f"{self._scope}:client:{self.item_id}"), self._entry_id
            )
            attributes["gwi_device_id"] = own.id if own else None
        if self.kind == "point" and self.key == "clients":
            network = self.coordinator.data["networks"][self.network_id]
            attributes.update(
                {
                    "devices": item.get("client_list", []),
                    "unassigned_clients": network.get("unassigned_clients"),
                    "unknown_connection_clients": network.get(
                        "unknown_connection_clients"
                    ),
                    "online": item.get("online"),
                    **{key: item.get(key) for key in (
                        "is_root", "root_ap_id", "mesh_quality", "mesh_rating",
                        "mesh_rating_index", "mesh_quality_source",
                    )},
                }
            )
        if self.key == "mesh_quality":
            attributes.update({key: item.get(key) for key in (
                "root_ap_id", "is_root", "mesh_rating", "mesh_rating_index", "mesh_quality_source",
            )})
            attributes["measurement"] = "Google mesh connection rating relative to the primary point; intermediate hops and measurement timestamp are not supplied"
        if self.key in ("diagnosis", "saturation"):
            attributes["assessment_limit"] = (
                "Connection and mesh ratings do not establish radio saturation. Channel utilization and retry rates are not supplied."
            )
        if self.key in ("weak_clients", "clients_with_quality"):
            clients = list(item.get("clients", {}).values()) if self.kind == "network" else [
                client for client in self.coordinator.data["networks"][self.network_id]["clients"].values()
                if client.get("ap_id") == self.item_id
            ]
            active = [client for client in clients if client.get("connected") is True]
            attributes["rated_clients"] = sum(client.get("signal_quality") is not None for client in active)
            attributes["observed_clients"] = len(active)
        if self.key == "rssi":
            attributes["measurement"] = (
                "Negative dBm measured by the client radio. Shelly samples are read locally and MAC-verified; Google connection ratings are separate."
            )
        if self.key == "google_telemetry_at":
            attributes["google_telemetry"] = item.get("google_telemetry", {})
            attributes["measurement"] = "Read-only Google telemetry; absent fields are not supplied. The timestamp is the HA retrieval time."
        if self.key in ("point", "clients", "google_telemetry_at", "mesh_test_mbps", "wifi_test_mbps"):
            attributes.update({key: item.get(key) for key in (
                "wifi_test_mbps", "wifi_test_at", "wifi_test_ap_id", "wifi_test_point",
                "mesh_test_mbps", "mesh_test_at", "backhaul_type", "internet_paused", "pause_until",
                "priority_active", "priority_until", "usage_windows", "usage_hourly") if key in item})
        if self.key in ("wifi_test_mbps", "mesh_test_mbps"):
            attributes["measurement"] = "Stored Google speed test, in Mbit/s. Use its timestamp and tested point; it is not current traffic or RSSI."
        if self.key.startswith("usage_"):
            window = {"24h": "hour", "7d": "day", "30d": "month"}.get(self.key.split("_")[1])
            attributes["usage_window"] = item.get("usage_windows", {}).get(window, {})
            attributes["measurement"] = "Bytes in a rolling requested UTC interval. Bucket timestamps are ends. Missing buckets leave the total unknown; observed partial totals are in usage_window."
        if self.key == "capability_count":
            attributes["capabilities"] = item.get("capabilities", {})
        if self.key == "last_operation":
            attributes["operations"] = item.get("operations", [])
        if self.kind == "point" and item.get("source") == "local_status":
            attributes["local_status"] = item.get("local_status", {})
            attributes["local_status_at"] = item.get("local_status_at")
        if self.key in ("client_download_mbps", "client_upload_mbps"):
            attributes["measurement"] = "Sum of current Google traffic measurements for clients explicitly associated with this point. This is not a backhaul or radio capacity measurement; incomplete samples remain unknown."
        if self.key == "uptime_seconds":
            attributes["measurement_source"] = item.get("uptime_source", item.get("source"))
        if self.kind == "client" and self.key in ("download_mbps", "upload_mbps"):
            attributes["measurement"] = "Current traffic in Mbit/s; omitted numeric rates in a present Google traffic message default to zero. Missing messages or stale associations remain unknown."
        return attributes
