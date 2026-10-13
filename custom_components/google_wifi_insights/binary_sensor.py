"""Explicit point connectivity and client connection states."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)

from .entity import WifiEntity, add_dynamic_entities


async def async_setup_entry(hass, entry, async_add_entities):
    def factory(network_id, kind, item_id, item):
        if kind == "network":
            return []
        return [
            WifiConnection(
                entry.runtime_data,
                entry,
                network_id,
                kind,
                item_id,
                item,
                "online" if kind == "point" else "connected",
            )
        ]

    add_dynamic_entities(entry.runtime_data, entry, async_add_entities, factory)


class WifiConnection(WifiEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_translation_key = "connected"

    @property
    def is_on(self):
        return self.item.get(self.key)
