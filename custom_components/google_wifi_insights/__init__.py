"""Google WiFi Insights custom integration."""

from .const import PLATFORMS
from .coordinator import WifiCoordinator
from .frontend import async_setup_frontend, async_unload_frontend
from .services import register_services


async def async_setup_entry(hass, entry):
    coordinator = WifiCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    register_services(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_setup_frontend(hass, entry.entry_id)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_reload_entry(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        async_unload_frontend(hass, entry.entry_id)
    return unloaded
