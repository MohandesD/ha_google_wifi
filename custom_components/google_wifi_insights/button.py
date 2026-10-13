"""Explicit tests/restarts. No test or restart runs during polling."""
from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.const import EntityCategory
from .entity import WifiEntity, add_dynamic_entities

BUTTONS = {"network": ("restart_network", "test_internet", "clear_priority", "refresh_metrics"),
           "point": ("restart_point", "test_mesh", "test_local", "test_clients"),
           "client": ("prioritize_client",)}


async def async_setup_entry(hass, entry, async_add_entities):
    def factory(nid, kind, sid, item):
        if item.get("source") != "google_cloud":
            return []
        return [GoogleButton(entry.runtime_data, entry, nid, kind, sid, item, key) for key in BUTTONS[kind]
                if not (key == "test_mesh" and item.get("is_root") is True)]
    add_dynamic_entities(entry.runtime_data, entry, async_add_entities, factory)


class GoogleButton(WifiEntity, ButtonEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, entry, nid, kind, sid, item, key):
        super().__init__(coordinator, entry, nid, kind, sid, item, key)
        self._attr_translation_key = key
        self._attr_icon = "mdi:restart" if key.startswith("restart") else "mdi:speedometer" if key.startswith("test") else "mdi:refresh"
        if key.startswith("restart"):
            self._attr_device_class = ButtonDeviceClass.RESTART

    async def async_press(self):
        if self.key == "refresh_metrics":
            self.coordinator.client.invalidate(self.network_id)
            await self.coordinator.async_request_refresh()
        else:
            await self.coordinator.async_google_action(self.network_id, self.kind, self.item_id, self.key, context=self._context)
