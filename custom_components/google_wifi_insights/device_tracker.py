"""Network presence from Google, without treating missing data as away."""

from homeassistant.components.device_tracker import ScannerEntity, SourceType

from .entity import WifiEntity, add_dynamic_entities

# Shared coordinator and per-target locks bound all network work.
PARALLEL_UPDATES = 0

async def async_setup_entry(hass, entry, async_add_entities):
    def factory(network_id, kind, item_id, item):
        return (
            [
                WifiTracker(
                    entry.runtime_data,
                    entry,
                    network_id,
                    kind,
                    item_id,
                    item,
                    "tracker",
                )
            ]
            if kind == "client"
            else []
        )

    add_dynamic_entities(entry.runtime_data, entry, async_add_entities, factory)


class WifiTracker(WifiEntity, ScannerEntity):
    _attr_translation_key = "network_presence"

    @property
    def source_type(self):
        return SourceType.ROUTER

    @property
    def available(self):
        return super().available and isinstance(self.item.get("connected"), bool)

    @property
    def is_connected(self):
        return self.item.get("connected") is True

    @property
    def ip_address(self):
        return self.item.get("ip_address")
