"""Serve the bundled UI and register a panel without editing user dashboards."""

import logging
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
DATA_FRONTEND = f"{DOMAIN}_frontend"
STATIC_URL = f"/{DOMAIN}/static"
PANEL_NAME = "google-wifi-insights-panel"
FRONTEND_VERSION = "0.8.2"
PANEL_PATHS = ("google-wifi-insights", "google-wifi-insights-integration")


async def async_setup_frontend(hass, entry_id):
    """Share static registration across entries and preserve existing panels."""
    if "frontend" not in hass.config.components or hass.http is None:
        return
    state = hass.data.setdefault(DATA_FRONTEND, {"entries": set()})
    if not state.get("static_registered"):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL, str(Path(__file__).parent / "frontend"), False)]
        )
        state["static_registered"] = True
    if not state.get("panel_path"):
        path = next(
            (candidate for candidate in PANEL_PATHS if not frontend.async_panel_exists(hass, candidate)),
            None,
        )
        if path is None:
            _LOGGER.warning("Google WiFi panel paths are already in use; existing panels were preserved")
            return
        await panel_custom.async_register_panel(
            hass,
            frontend_url_path=path,
            webcomponent_name=PANEL_NAME,
            sidebar_title="Google WiFi",
            sidebar_icon="mdi:access-point-network",
            module_url=f"{STATIC_URL}/google-wifi-insights-panel.js?v={FRONTEND_VERSION}",
            embed_iframe=False,
            config={"map_path": f"/{path}/mapa"},
        )
        state["panel_path"] = path
    state["entries"].add(entry_id)


def async_unload_frontend(hass, entry_id):
    """Remove only our panel after its last integration entry is unloaded."""
    if not (state := hass.data.get(DATA_FRONTEND)):
        return
    state["entries"].discard(entry_id)
    if state["entries"] or not (path := state.get("panel_path")):
        return
    panel = hass.data.get(frontend.DATA_PANELS, {}).get(path)
    if panel and (panel.config or {}).get("_panel_custom", {}).get("name") == PANEL_NAME:
        frontend.async_remove_panel(hass, path)
    state.pop("panel_path", None)
    # HTTP routes persist until HA stops; never register duplicate routes on reload.
