"""Explicit point connectivity and client connection states."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)

from .entity import WifiEntity, add_dynamic_entities
from homeassistant.const import EntityCategory


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
    def information_factory(network_id, kind, item_id, item):
        keys = ("ipv6_enabled", "upnp_enabled", "guest_wifi_enabled") if kind == "network" else (
            "update_required", "wan_online", "ethernet_link", "lan0_link") if kind == "point" else ()
        return [WifiInformationFlag(entry.runtime_data, entry, network_id, kind, item_id, item, key) for key in keys]
    add_dynamic_entities(entry.runtime_data, entry, async_add_entities, information_factory)


class WifiInformationFlag(WifiEntity, BinarySensorEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, *args):
        super().__init__(*args)
        self._attr_translation_key = self.key
        self._attr_device_class = BinarySensorDeviceClass.UPDATE if self.key == "update_required" else (
            BinarySensorDeviceClass.CONNECTIVITY if self.key in ("wan_online", "ethernet_link", "lan0_link") else None)

    @property
    def is_on(self):
        value = self.item.get(self.key)
        return value if isinstance(value, bool) else None


class WifiConnection(WifiEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_translation_key = "connected"

    @property
    def is_on(self):
        return self.item.get(self.key)
