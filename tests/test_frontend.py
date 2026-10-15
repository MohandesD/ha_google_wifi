"""Verify HACS assets and real HA panel ownership/reload behaviour."""

import json
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from homeassistant.components import frontend
from test_ha import real_hass as real_hass

ROOT = Path(__file__).resolve().parents[1]


def test_hacs_download_contains_all_frontend_dependencies():
    from gwi_test.frontend import FRONTEND_VERSION

    component = ROOT / "custom_components/google_wifi_insights"
    manifest = json.loads((component / "manifest.json").read_text())
    assert manifest["version"] == FRONTEND_VERSION
    assets = list((component / "frontend").glob("*.js"))
    assert len(assets) == 6
    for asset in assets:
        text = asset.read_text(encoding="utf-8")
        for module, version in re.findall(r"['\"]\./([^'\"?]+)\?v=([^'\"]+)['\"]", text):
            assert (asset.parent / module).is_file()
            assert version == manifest["version"]
        mirror = ROOT / "www" / asset.name
        if mirror.exists():
            assert mirror.read_bytes() == asset.read_bytes()


@pytest.mark.asyncio
async def test_shared_panel_unload_and_reload_in_real_ha(real_hass, monkeypatch):
    from custom_components.google_wifi_insights.frontend import (
        PANEL_NAME,
        STATIC_URL,
        async_setup_frontend,
        async_unload_frontend,
    )

    register_static = AsyncMock()
    monkeypatch.setattr(real_hass, "http", SimpleNamespace(async_register_static_paths=register_static))
    real_hass.config.components.add("frontend")
    await async_setup_frontend(real_hass, "local-entry")
    await async_setup_frontend(real_hass, "cloud-entry")
    assert register_static.await_count == 1
    config = register_static.call_args.args[0][0]
    assert config.url_path == STATIC_URL
    assert config.path.endswith("frontend")
    panel = real_hass.data[frontend.DATA_PANELS]["google-wifi-insights"]
    assert panel.config["_panel_custom"]["name"] == PANEL_NAME
    assert panel.config["_panel_custom"]["embed_iframe"] is False
    assert panel.config["map_path"] == "/google-wifi-insights/mapa"
    async_unload_frontend(real_hass, "local-entry")
    assert frontend.async_panel_exists(real_hass, "google-wifi-insights")
    async_unload_frontend(real_hass, "cloud-entry")
    assert not frontend.async_panel_exists(real_hass, "google-wifi-insights")
    await async_setup_frontend(real_hass, "cloud-entry")
    assert register_static.await_count == 1
    assert frontend.async_panel_exists(real_hass, "google-wifi-insights")
    async_unload_frontend(real_hass, "cloud-entry")


@pytest.mark.asyncio
async def test_existing_dashboard_and_replaced_panel_are_preserved(real_hass, monkeypatch):
    from custom_components.google_wifi_insights.frontend import (
        async_setup_frontend,
        async_unload_frontend,
    )

    # Headless HA remains usable without the optional browser frontend.
    await async_setup_frontend(real_hass, "headless")
    assert not frontend.async_panel_exists(real_hass, "google-wifi-insights")
    real_hass.config.components.add("frontend")
    monkeypatch.setattr(real_hass, "http", SimpleNamespace(async_register_static_paths=AsyncMock()))
    frontend.async_register_built_in_panel(real_hass, "lovelace", frontend_url_path="google-wifi-insights")
    original = real_hass.data[frontend.DATA_PANELS]["google-wifi-insights"]
    await async_setup_frontend(real_hass, "cloud")
    assert real_hass.data[frontend.DATA_PANELS]["google-wifi-insights"] is original
    assert frontend.async_panel_exists(real_hass, "google-wifi-insights-integration")
    frontend.async_register_built_in_panel(real_hass, "other", frontend_url_path="google-wifi-insights-integration", update=True)
    replacement = real_hass.data[frontend.DATA_PANELS]["google-wifi-insights-integration"]
    async_unload_frontend(real_hass, "cloud")
    assert real_hass.data[frontend.DATA_PANELS]["google-wifi-insights-integration"] is replacement
    assert real_hass.data[frontend.DATA_PANELS]["google-wifi-insights"] is original
