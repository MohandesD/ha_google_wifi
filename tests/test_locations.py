"""Location labels remain local, scoped, durable and safe during outages."""
import copy
import json
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from gwi_test.management import WifiManagement, location_details, location_label
from homeassistant import config_entries
from homeassistant.core import Context
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import area_registry, device_registry
from test_ha import real_hass as real_hass
from test_management import call, carrier
from test_stabilization_ha import DOMAIN, network_fixture, setup_fixture


@pytest.mark.parametrize("value,expected", [
    (None, None), ("", None), ("   ", None), ("  Example   home  ", "Example home"),
    ("Ｈｏｍｅ", "Home"), ("a" * 64, "a" * 64),
])
def test_normalized_location_labels(value, expected):
    assert location_label(value) == expected
    assert location_details(None) is None
    assert location_details("Home")["id"] == location_details("HOME")["id"]


@pytest.mark.parametrize("value", [False, 7, {}, "a" * 65, "Bad\nname", "Bad\x00name", "Bad\u200bname"])
def test_location_labels_reject_nontext_controls_and_long_names(value):
    with pytest.raises(HomeAssistantError, match="printable"):
        location_label(value)


async def test_location_saved_without_google_requests_or_registry_changes(real_hass, monkeypatch):
    from custom_components.google_wifi_insights.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    network = network_fixture()
    entry = await setup_fixture(real_hass, monkeypatch, {"networks": {"home": network, "remote": copy.deepcopy(network)}})
    coordinator = entry.runtime_data
    before_reads = coordinator.client.snapshot.call_count
    write = AsyncMock()
    monkeypatch.setattr(coordinator.client, "action", write)
    devices = device_registry.async_get(real_hass)
    before = {d.id: (d.area_id, d.name_by_user) for d in device_registry.async_entries_for_config_entry(devices, entry.entry_id)}
    network_state = carrier(real_hass, "network", "diagnosis")
    response = await call(real_hass, "set_network_location", {"entity_id": network_state.entity_id, "name": "  Example   home "})
    await real_hass.async_block_till_done()
    assert response == {"scope": f"{entry.entry_id}:home", "location": location_details("Example home")}
    state = carrier(real_hass, "network", "diagnosis")
    assert state.attributes["network_location"] == "Example home"
    assert state.attributes["network_location_id"] == response["location"]["id"]
    assert state.attributes["gwi_entry_id"] == entry.entry_id
    assert not carrier(real_hass, "network", "diagnosis", "remote").attributes["network_location"]
    assert coordinator.client.snapshot.call_count == before_reads
    write.assert_not_awaited()
    assert {d.id: (d.area_id, d.name_by_user) for d in device_registry.async_entries_for_config_entry(devices, entry.entry_id)} == before
    assert not area_registry.async_get(real_hass).areas
    assert not coordinator.names.summary("home")["enabled"]
    assert (await call(real_hass, "get_management", {"entity_id": state.entity_id}))["location"] == response["location"]
    assert await real_hass.config_entries.async_reload(entry.entry_id)
    await real_hass.async_block_till_done()
    assert carrier(real_hass, "network", "diagnosis").attributes["network_location"] == "Example home"
    diagnostics = await async_get_config_entry_diagnostics(real_hass, entry)
    assert "Example home" not in json.dumps(diagnostics)
    path = Path(real_hass.config.path(".storage", f"{DOMAIN}.{entry.entry_id}.locations"))
    assert path.is_file()
    await call(real_hass, "set_network_location", {"entity_id": state.entity_id, "name": None})
    assert not entry.runtime_data.management.locations
    assert await real_hass.config_entries.async_remove(entry.entry_id)
    assert not path.exists()


async def test_local_network_labels_do_not_enable_cloud_actions(real_hass, monkeypatch):
    from custom_components.google_wifi_insights.api import LocalClient

    network = network_fixture(0)
    network["source"] = "local_status"
    monkeypatch.setattr(LocalClient, "snapshot", AsyncMock(return_value={"networks": {"local": network}}))
    entry = config_entries.ConfigEntry(data={"mode": "local", "points": []}, domain=DOMAIN,
        discovery_keys=MappingProxyType({}), options={}, source="user", title="Fictional local entry",
        unique_id="local-fixture", version=1, minor_version=1, subentries_data=None)
    await real_hass.config_entries.async_add(entry)
    await real_hass.async_block_till_done()
    state = carrier(real_hass, "network", "diagnosis", "local")
    response = await call(real_hass, "set_network_location", {"entity_id": state.entity_id, "name": "Example building"})
    assert response["location"]["name"] == "Example building"
    assert entry.runtime_data.client.snapshot.await_count == 1
    with pytest.raises(HomeAssistantError, match="Google account"):
        await call(real_hass, "google_action", {"entity_id": state.entity_id, "action": "restart_network"})
    with pytest.raises(HomeAssistantError, match="network entity"):
        await call(real_hass, "set_network_location", {"entity_id": carrier(real_hass, "point", "clients", "local").entity_id, "name": "Bad target"})
    assert await real_hass.config_entries.async_unload(entry.entry_id)


async def test_location_metadata_can_change_during_outage_without_clearing_failure(real_hass, monkeypatch):
    from custom_components.google_wifi_insights.api import ApiError

    entry = await setup_fixture(real_hass, monkeypatch, {"networks": {"home": network_fixture()}})
    monkeypatch.setattr(entry.runtime_data.client, "snapshot", AsyncMock(side_effect=ApiError("Fixture outage")))
    await entry.runtime_data.async_refresh()
    await real_hass.async_block_till_done()
    state = carrier(real_hass, "network", "diagnosis")
    assert state.state == "unavailable"
    await call(real_hass, "set_network_location", {"entity_id": state.entity_id, "name": "Example offline home"})
    await real_hass.async_block_till_done()
    assert not entry.runtime_data.last_update_success
    assert carrier(real_hass, "network", "diagnosis").state == "unavailable"
    assert carrier(real_hass, "network", "diagnosis").attributes["network_location"] == "Example offline home"
    assert not carrier(real_hass, "client", "associated_area").attributes.get("associated_area_id")
    assert entry.runtime_data.client.snapshot.await_count == 1
    assert await real_hass.config_entries.async_unload(entry.entry_id)


async def test_failed_location_storage_and_nonadmin_cannot_change_label(real_hass, monkeypatch):
    entry = await setup_fixture(real_hass, monkeypatch, {"networks": {"home": network_fixture()}})
    target = {"entity_id": carrier(real_hass, "network", "diagnosis").entity_id, "name": "Example home"}
    monkeypatch.setattr(entry.runtime_data.management._locations_store, "async_save", AsyncMock(side_effect=OSError("Fixture disk error")))
    with pytest.raises(OSError, match="disk"):
        await call(real_hass, "set_network_location", target)
    assert not entry.runtime_data.management.locations
    with pytest.raises(HomeAssistantError, match="known Google WiFi network"):
        await entry.runtime_data.async_set_network_location("missing", "Bad target")
    real_hass.auth = SimpleNamespace(async_get_user=AsyncMock(return_value=SimpleNamespace(is_admin=False)))
    with pytest.raises(HomeAssistantError, match="administrator"):
        await call(real_hass, "set_network_location", target, Context(user_id="non-admin"))
    assert await real_hass.config_entries.async_unload(entry.entry_id)


async def test_saved_location_validation_ignores_malformed_rows(real_hass, monkeypatch):
    management = WifiManagement(real_hass, SimpleNamespace(entry_id="fixture-validation"))
    monkeypatch.setattr(management._store, "async_load", AsyncMock(return_value={}))
    monkeypatch.setattr(management._locations_store, "async_load", AsyncMock(return_value={"home": "  Example home ", "long": "a" * 65, "control": "bad\nname", "empty": "", "wrong": {"name": "nested"}, 4: "invalid key"}))
    await management.async_load()
    await management.async_load()
    assert management.locations == {"home": "Example home"}
    assert management._locations_store.async_load.await_count == 1
