"""Enable or disable Shelly roaming without touching WiFi credentials."""
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from .entity import WifiEntity, add_dynamic_entities


async def async_setup_entry(hass, entry, async_add_entities):
    def factory(network_id, kind, item_id, item):
        return [RoamingSwitch(entry.runtime_data, entry, network_id, kind, item_id, item, "roaming_enabled")] if kind == "client" and item.get("roaming_supported") else []
    add_dynamic_entities(entry.runtime_data, entry, async_add_entities, factory)
    def google_factory(nid, kind, sid, item):
        return [InternetPauseSwitch(entry.runtime_data, entry, nid, kind, sid, item, "internet_paused")] if kind == "client" and item.get("source") == "google_cloud" else []
    add_dynamic_entities(entry.runtime_data, entry, async_add_entities, google_factory)


class RoamingSwitch(WifiEntity, SwitchEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "roaming_enabled"
    _attr_icon = "mdi:access-point-network"

    @property
    def available(self):
        return super().available and self.item.get("radio_available") is True

    @property
    def is_on(self):
        interval = self.item.get("roam_interval")
        return interval > 0 if interval is not None else None

    async def async_turn_on(self, **kwargs):
        await self.coordinator.async_set_roaming(self.network_id, self.item_id, "enabled", True)

    async def async_turn_off(self, **kwargs):
        await self.coordinator.async_set_roaming(self.network_id, self.item_id, "enabled", False)


class InternetPauseSwitch(WifiEntity, SwitchEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "internet_paused"
    _attr_icon = "mdi:pause-circle-outline"

    @property
    def is_on(self):
        return self.item.get("internet_paused")

    async def async_turn_on(self, **kwargs):
        await self.coordinator.async_google_action(self.network_id, self.kind, self.item_id, "pause_client", context=self._context)

    async def async_turn_off(self, **kwargs):
        await self.coordinator.async_google_action(self.network_id, self.kind, self.item_id, "resume_client", context=self._context)
