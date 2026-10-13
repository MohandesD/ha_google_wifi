"""Client binding, explicit signal data, traffic and cautious summaries."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfDataRate, UnitOfInformation, UnitOfTime, EntityCategory

from .entity import WifiEntity, add_dynamic_entities

SENSORS = {
    "network": [
        ("connected_clients", "Connected clients"),
        ("weak_clients", "Clients with weak signal"),
        ("clients_with_signal", "Clients reporting signal"),
        ("clients_with_quality", "Clients reporting connection quality"),
        ("weak_mesh_points", "Points with weak mesh connection"),
        ("download_mbps", "Download traffic"),
        ("upload_mbps", "Upload traffic"),
        ("diagnosis", "Assessment"),
        ("saturation", "Radio saturation"),
        ("wan_status", "Internet connection"),
        ("wan_test_download_mbps", "Last Internet download test"),
        ("wan_test_upload_mbps", "Last Internet upload test"),
        ("wan_test_at", "Last Internet test time"),
        ("google_telemetry_at", "Google telemetry"),
    ],
    "point": [
        ("clients", "Observed clients"),
        ("weak_clients", "Clients with weak signal"),
        ("firmware", "Firmware"),
        ("uptime_seconds", "Uptime"),
        ("mesh_quality", "Mesh connection quality"),
        ("ip_address", "IP address"),
        ("last_seen", "Last seen by Google"),
        ("hardware_type", "Hardware"),
        ("led_brightness", "Point light brightness"),
        ("google_telemetry_at", "Google telemetry"),
        ("client_download_mbps", "Clients download traffic"),
        ("client_upload_mbps", "Clients upload traffic"),
    ],
    "client": [
        ("ip_address", "IP address"),
        ("mac_address", "MAC address"),
        ("wireless_band", "WiFi band"),
        ("connection_type", "Connection type"),
        ("point", "Connected point"),
        ("rssi", "WiFi RSSI"),
        ("signal_quality", "Signal quality"),
        ("download_mbps", "Download traffic"),
        ("upload_mbps", "Upload traffic"),
        ("last_seen", "Last seen by Google"),
        ("wireless_standard", "WiFi capability"),
        ("rx_spatial_streams", "Receive spatial streams"),
        ("google_telemetry_at", "Google telemetry"),
        ("wifi_bssid", "Current WiFi BSSID"),
        ("wifi_channel", "Current WiFi channel"),
    ],
}

EXTRA_SENSORS = {
    "network": [("capability_count", "Google capabilities"), ("last_operation", "Last Google operation"),
                ("peak_1h_download_mbps", "Peak download in last hour"), ("peak_1h_upload_mbps", "Peak upload in last hour")]
               + [(f"usage_{window}_{direction}", f"{direction.title()} usage {window}") for window in ("24h", "7d", "30d") for direction in ("download", "upload")],
    "point": [("mesh_test_mbps", "Last mesh speed test"), ("mesh_test_at", "Last mesh test time"), ("backhaul_type", "Backhaul type")],
    "client": [("wifi_test_mbps", "Last device WiFi speed test"), ("wifi_test_at", "Last device WiFi test time"),
               ("usage_24h_download", "Download usage 24h"), ("usage_24h_upload", "Upload usage 24h"),
               ("priority_until", "Priority until")],
}


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data

    def factory(network_id, kind, item_id, item):
        return [
            WifiSensor(coordinator, entry, network_id, kind, item_id, item, key, name)
            for key, name in SENSORS[kind]
            if key not in ("wifi_bssid", "wifi_channel")
            and (item.get("source") == "google_cloud" or key not in (
                "google_telemetry_at", "last_seen", "hardware_type", "led_brightness", "wireless_standard", "rx_spatial_streams",
                "wan_status", "wan_test_download_mbps", "wan_test_upload_mbps", "wan_test_at",
            ))
        ]

    add_dynamic_entities(coordinator, entry, async_add_entities, factory)
    def radio_factory(network_id, kind, item_id, item):
        if kind != "client" or not item.get("roaming_supported"):
            return []
        return [WifiSensor(coordinator, entry, network_id, kind, item_id, item, key, name)
                for key, name in SENSORS[kind] if key in ("wifi_bssid", "wifi_channel")]
    add_dynamic_entities(coordinator, entry, async_add_entities, radio_factory)
    def extra_factory(nid, kind, sid, item):
        return [WifiSensor(coordinator, entry, nid, kind, sid, item, key, name) for key, name in EXTRA_SENSORS[kind]] if item.get("source") == "google_cloud" else []
    add_dynamic_entities(coordinator, entry, async_add_entities, extra_factory)


class WifiSensor(WifiEntity, SensorEntity):
    def __init__(self, coordinator, entry, network_id, kind, item_id, item, key, name):
        super().__init__(coordinator, entry, network_id, kind, item_id, item, key)
        self._attr_translation_key = key
        self._attr_icon = "mdi:wifi"
        if key in ("ip_address", "mac_address", "wireless_band", "connection_type", "google_telemetry_at", "last_seen", "hardware_type", "led_brightness", "wireless_standard", "rx_spatial_streams", "wifi_bssid", "wifi_channel"):
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        if key in ("ip_address", "mac_address"):
            self._attr_icon = "mdi:ip-network" if key == "ip_address" else "mdi:identifier"
        if key.endswith("_mbps"):
            self._attr_native_unit_of_measurement = UnitOfDataRate.MEGABITS_PER_SECOND
            self._attr_device_class = SensorDeviceClass.DATA_RATE
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif key == "rssi":
            self._attr_native_unit_of_measurement = "dBm"
            self._attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif key in ("google_telemetry_at", "last_seen", "wan_test_at", "wifi_test_at", "mesh_test_at", "priority_until"):
            self._attr_device_class = SensorDeviceClass.TIMESTAMP
        elif key.startswith("usage_"):
            self._attr_native_unit_of_measurement = UnitOfInformation.BYTES
            self._attr_device_class = SensorDeviceClass.DATA_SIZE
            # Rolling-window totals decrease: never mark TOTAL_INCREASING.
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif key == "capability_count":
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
            self._attr_icon = "mdi:api"
        elif key == "last_operation":
            self._attr_icon = "mdi:progress-check"
        elif key == "led_brightness":
            self._attr_native_unit_of_measurement = "%"
            self._attr_icon = "mdi:brightness-6"
        elif key == "uptime_seconds":
            self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
            self._attr_device_class = SensorDeviceClass.DURATION
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif key in (
            "connected_clients",
            "clients",
            "weak_clients",
            "clients_with_signal",
            "clients_with_quality",
            "weak_mesh_points",
        ):
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif key in ("diagnosis", "signal_quality", "mesh_quality"):
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = (
                ["point_offline", "weak_mesh_detected", "weak_signal_detected", "quality_data_available", "insufficient_radio_data"]
                if key == "diagnosis"
                else ["excellent", "good", "fair", "weak"]
            )
        elif key == "wireless_band":
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = ["BAND_2400_MHZ", "BAND_5000_MHZ", "BAND_6000_MHZ", "NOT_APPLICABLE"]
        elif key == "connection_type":
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = ["WIRED", "WIRELESS"]

    @property
    def native_value(self):
        value = self.item.get("host") if self.kind == "point" and self.key == "ip_address" else self.item.get(self.key)
        if self.key in ("wireless_band", "connection_type") and value not in self._attr_options:
            return None
        return value
