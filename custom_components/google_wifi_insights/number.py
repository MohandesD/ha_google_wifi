"""Confirmed Shelly roaming threshold and scan interval controls."""
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory, UnitOfTime
from .entity import WifiEntity, add_dynamic_entities


async def async_setup_entry(hass, entry, async_add_entities):
    def factory(network_id, kind, item_id, item):
        if kind != "client" or not item.get("roaming_supported"):
            return []
        return [RoamingNumber(entry.runtime_data, entry, network_id, kind, item_id, item, key)
                for key in ("roam_rssi_threshold", "roam_interval")]
    add_dynamic_entities(entry.runtime_data, entry, async_add_entities, factory)
    def google_factory(nid, kind, sid, item):
        return [PointBrightness(entry.runtime_data, entry, nid, kind, sid, item, "set_point_light")] if kind == "point" and item.get("source") == "google_cloud" else []
    add_dynamic_entities(entry.runtime_data, entry, async_add_entities, google_factory)


class RoamingNumber(WifiEntity, NumberEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX
    _attr_native_step = 1

    def __init__(self, coordinator, entry, network_id, kind, item_id, item, key):
        super().__init__(coordinator, entry, network_id, kind, item_id, item, key)
        self._attr_translation_key = key
        self._attr_native_min_value = -100 if key == "roam_rssi_threshold" else 0
        self._attr_native_max_value = -40 if key == "roam_rssi_threshold" else 3600
        self._attr_native_unit_of_measurement = "dBm" if key == "roam_rssi_threshold" else UnitOfTime.SECONDS
        self._attr_icon = "mdi:wifi-strength-alert-outline" if key == "roam_rssi_threshold" else "mdi:timer-outline"

    @property
    def available(self):
        return super().available and self.item.get("radio_available") is True

    @property
    def native_value(self):
        return self.item.get(self.key)

    async def async_set_native_value(self, value):
        await self.coordinator.async_set_roaming(self.network_id, self.item_id,
            "rssi_thr" if self.key == "roam_rssi_threshold" else "interval", value)


class PointBrightness(WifiEntity, NumberEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.SLIDER
    _attr_translation_key = "set_point_light"
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "%"
    _attr_icon = "mdi:brightness-6"

    @property
    def native_value(self):
        return self.item.get("led_brightness")

    async def async_set_native_value(self, value):
        await self.coordinator.async_google_action(self.network_id, self.kind, self.item_id, "set_point_light", {"brightness": value}, self._context)
