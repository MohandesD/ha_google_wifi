"""Exercise opt-in device areas, roaming and stale-data boundaries in real HA."""

import asyncio
import copy
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from homeassistant import config_entries
from homeassistant.core import Context
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import area_registry, device_registry
from homeassistant.helpers.storage import Store
from test_ha import real_hass as real_hass
from test_management import call, carrier
from test_stabilization_ha import DOMAIN, network_fixture, setup_fixture

MAC = "02:00:00:00:00:01"


async def setup(hass, monkeypatch):
    areas = area_registry.async_get(hass)
    first, second, manual = [areas.async_create(name) for name in ("Example office", "Example studio", "Manual area")]
    network = network_fixture()
    network["clients"]["client0"]["mac_address"] = MAC
    network["points"]["other"] = copy.deepcopy(network["points"]["point"])
    snapshot = {"networks": {"home": network, "second": copy.deepcopy(network)}}
    snapshot["networks"]["second"]["clients"] = {}
    entry = await setup_fixture(hass, monkeypatch, snapshot)
    coordinator = entry.runtime_data
    await coordinator.async_set_point_area("home", "point", first.id)
    await coordinator.async_set_point_area("home", "other", second.id)
    registry = device_registry.async_get(hass)
    own = registry.async_get_device_by_identifier((DOMAIN, f"{entry.entry_id}:home:client:client0"), entry.entry_id)
    return entry, snapshot, own.id, first, second, manual


def foreign_device(hass, index=0, mac=MAC, host=None):
    entry = config_entries.ConfigEntry(data={"host": host} if host else {}, domain="mqtt", discovery_keys=MappingProxyType({}), options={},
        source="user", title="Fictional device", unique_id=f"foreign-{index}", version=1, minor_version=1,
        subentries_data=None)
    hass.config_entries._entries[entry.entry_id] = entry
    return device_registry.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={("mqtt", f"fictional-{index}")},
        connections={(device_registry.CONNECTION_NETWORK_MAC, mac)} if mac else set(), name="Example phone"
    )


async def test_default_is_off_and_opted_in_clients_follow_points_without_new_google_requests(real_hass, monkeypatch):
    foreign = foreign_device(real_hass)
    entry, snapshot, device_id, first, second, manual = await setup(real_hass, monkeypatch)
    coordinator, registry = entry.runtime_data, device_registry.async_get(real_hass)
    registry.async_update_device(foreign.id, area_id=manual.id)
    registry.async_update_device(device_id, area_id=manual.id)
    await coordinator.async_refresh()
    assert registry.async_get(device_id).area_id == manual.id
    assert coordinator.client_areas.response("home")["enabled"] is False
    ids = {d.id for d in device_registry.async_entries_for_config_entry(registry, entry.entry_id)}
    polls = coordinator.client.snapshot.call_count
    await call(real_hass, "set_client_area_sync", {"entity_id": carrier(real_hass, "network", "diagnosis").entity_id, "enabled": True})
    assert coordinator.client.snapshot.call_count == polls
    assert registry.async_get(device_id).area_id == first.id
    assert registry.async_get(foreign.id).area_id == manual.id
    snapshot["networks"]["home"]["clients"]["client0"]["ap_id"] = "other"
    await coordinator.async_refresh()
    assert registry.async_get(device_id).area_id == second.id
    assert registry.async_get(foreign.id).area_id == manual.id
    assert {d.id for d in device_registry.async_entries_for_config_entry(registry, entry.entry_id)} == ids
    assert coordinator.client_areas.response("second")["enabled"] is False
    assert await real_hass.config_entries.async_reload(entry.entry_id)
    await real_hass.async_block_till_done()
    assert entry.runtime_data.client_areas.response("home")["enabled"] is True
    assert registry.async_get(device_id).area_id == second.id
    await entry.runtime_data.async_set_client_area_sync("home", False, False)
    registry.async_update_device(device_id, area_id=manual.id)
    await entry.runtime_data.async_refresh()
    assert registry.async_get(device_id).area_id == manual.id
    assert await real_hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize("change", ["disconnected", "wired", "point_offline", "network_failed", "point_missing", "unmapped"])
async def test_invalid_associations_keep_last_fixed_area(real_hass, monkeypatch, change):
    entry, snapshot, device_id, first, second, _ = await setup(real_hass, monkeypatch)
    await entry.runtime_data.async_set_client_area_sync("home", True, False)
    network = snapshot["networks"]["home"]
    client = network["clients"]["client0"]
    client["ap_id"] = "other"
    if change == "disconnected":
        client["connected"] = False
    elif change == "wired":
        client["connection_type"] = "WIRED"
    elif change == "point_offline":
        network["points"]["other"]["online"] = False
    elif change == "network_failed":
        network["reachable"] = False
    elif change == "point_missing":
        client["ap_id"] = "missing"
    else:
        await entry.runtime_data.management.async_set_area("home", "other", None)
    await entry.runtime_data.async_refresh()
    assert device_registry.async_get(real_hass).async_get(device_id).area_id == first.id
    assert await real_hass.config_entries.async_unload(entry.entry_id)


async def test_newly_discovered_clients_receive_area_before_another_poll(real_hass, monkeypatch):
    entry, snapshot, _, first, _, _ = await setup(real_hass, monkeypatch)
    await entry.runtime_data.async_set_client_area_sync("home", True, False)
    network = snapshot["networks"]["home"]
    network["clients"]["client1"] = {**copy.deepcopy(network["clients"]["client0"]), "name": "Example tablet", "mac_address": "02:00:00:00:00:02"}
    polls = entry.runtime_data.client.snapshot.call_count
    await entry.runtime_data.async_refresh()
    await real_hass.async_block_till_done()
    own = device_registry.async_get(real_hass).async_get_device_by_identifier((DOMAIN, f"{entry.entry_id}:home:client:client1"), entry.entry_id)
    assert own.area_id == first.id
    assert entry.runtime_data.client.snapshot.call_count == polls + 1
    assert await real_hass.config_entries.async_unload(entry.entry_id)


async def test_matched_devices_require_explicit_opt_in_and_exact_mac(real_hass, monkeypatch):
    first_match, second_match = foreign_device(real_hass), foreign_device(real_hass, 1)
    entry, snapshot, device_id, first, second, manual = await setup(real_hass, monkeypatch)
    registry = device_registry.async_get(real_hass)
    for device in (first_match, second_match):
        registry.async_update_device(device.id, area_id=manual.id)
    await entry.runtime_data.async_set_client_area_sync("home", True, True)
    assert registry.async_get(first_match.id).area_id == first.id
    assert registry.async_get(second_match.id).area_id == first.id
    snapshot["networks"]["home"]["clients"]["client0"]["ap_id"] = "other"
    await entry.runtime_data.async_refresh()
    assert registry.async_get(device_id).area_id == second.id
    assert registry.async_get(first_match.id).area_id == second.id
    assert registry.async_get(second_match.id).area_id == second.id
    assert await real_hass.config_entries.async_unload(entry.entry_id)


async def test_duplicate_connected_mac_in_another_home_does_not_move_matched_devices(real_hass, monkeypatch):
    foreign = foreign_device(real_hass)
    entry, snapshot, device_id, first, _, manual = await setup(real_hass, monkeypatch)
    registry = device_registry.async_get(real_hass)
    registry.async_update_device(foreign.id, area_id=manual.id)
    snapshot["networks"]["second"]["clients"]["duplicate"] = copy.deepcopy(snapshot["networks"]["home"]["clients"]["client0"])
    await entry.runtime_data.async_refresh()
    await entry.runtime_data.async_set_client_area_sync("home", True, True)
    assert registry.async_get(device_id).area_id == first.id
    assert registry.async_get(foreign.id).area_id == manual.id
    assert await real_hass.config_entries.async_unload(entry.entry_id)


async def test_ip_only_matches_do_not_move_devices_from_other_integrations(real_hass, monkeypatch):
    foreign = foreign_device(real_hass, mac=None, host="192.168.50.10")
    entry, snapshot, own_id, first, _, manual = await setup(real_hass, monkeypatch)
    registry = device_registry.async_get(real_hass)
    registry.async_update_device(foreign.id, area_id=manual.id)
    client = snapshot["networks"]["home"]["clients"]["client0"]
    client.update(mac_address=None, ip_address="192.168.50.10", ip_addresses=["192.168.50.10"])
    await entry.runtime_data.async_refresh()
    assert entry.runtime_data.data["networks"]["home"]["clients"]["client0"]["identity_match"] == "ip"
    await entry.runtime_data.async_set_client_area_sync("home", True, True)
    assert registry.async_get(own_id).area_id == first.id
    assert registry.async_get(foreign.id).area_id == manual.id
    assert await real_hass.config_entries.async_unload(entry.entry_id)


async def test_conflicting_interfaces_leave_the_shared_original_device_area_unchanged(real_hass, monkeypatch):
    foreign = foreign_device(real_hass)
    registry = device_registry.async_get(real_hass)
    second_mac = "02:00:00:00:00:02"
    registry.async_update_device(foreign.id, new_connections={
        (device_registry.CONNECTION_NETWORK_MAC, MAC), (device_registry.CONNECTION_NETWORK_MAC, second_mac)
    })
    entry, snapshot, _, first, second, manual = await setup(real_hass, monkeypatch)
    registry.async_update_device(foreign.id, area_id=manual.id)
    client = snapshot["networks"]["home"]["clients"]["client0"]
    snapshot["networks"]["home"]["clients"]["client1"] = {**copy.deepcopy(client), "ap_id": "other", "mac_address": second_mac}
    await entry.runtime_data.async_refresh()
    await entry.runtime_data.async_set_client_area_sync("home", True, True)
    assert registry.async_get(foreign.id).area_id == manual.id
    assert carrier(real_hass, "client", "associated_area", sid="client0").state == first.name
    assert carrier(real_hass, "client", "associated_area", sid="client1").state == second.name
    assert await real_hass.config_entries.async_unload(entry.entry_id)


async def test_outage_settings_persist_without_moving_from_stale_data(real_hass, monkeypatch):
    from custom_components.google_wifi_insights.api import ApiError

    entry, snapshot, device_id, first, _, _ = await setup(real_hass, monkeypatch)
    monkeypatch.setattr(entry.runtime_data.client, "snapshot", AsyncMock(side_effect=ApiError("Fixture outage")))
    await entry.runtime_data.async_refresh()
    entity = next(s.entity_id for s in real_hass.states.async_all() if s.attributes.get("gwi_kind") == "network" and s.attributes.get("gwi_network_id") == "home")
    await call(real_hass, "set_client_area_sync", {"entity_id": entity, "enabled": True})
    assert not entry.runtime_data.last_update_success
    assert device_registry.async_get(real_hass).async_get(device_id).area_id is None
    monkeypatch.setattr(entry.runtime_data.client, "snapshot", AsyncMock(side_effect=lambda: copy.deepcopy(snapshot)))
    await entry.runtime_data.async_refresh()
    assert device_registry.async_get(real_hass).async_get(device_id).area_id == first.id
    assert await real_hass.config_entries.async_unload(entry.entry_id)


async def test_area_following_checks_admin_target_storage_and_cleanup(real_hass, monkeypatch):
    entry, _, device_id, _, _, _ = await setup(real_hass, monkeypatch)
    entity = carrier(real_hass, "network", "diagnosis").entity_id
    real_hass.auth = SimpleNamespace(async_get_user=AsyncMock(return_value=SimpleNamespace(is_admin=False)))
    with pytest.raises(HomeAssistantError, match="administrator"):
        await call(real_hass, "set_client_area_sync", {"entity_id": entity, "enabled": True}, Context(user_id="not-admin"))
    with pytest.raises(HomeAssistantError, match="network entity"):
        await call(real_hass, "set_client_area_sync", {"entity_id": carrier(real_hass, "client", "point").entity_id, "enabled": True})
    with pytest.raises(HomeAssistantError, match="known Google"):
        await entry.runtime_data.async_set_client_area_sync("missing", True, False)
    assert device_registry.async_get(real_hass).async_get(device_id).area_id is None
    save = entry.runtime_data.client_areas._store.async_save
    monkeypatch.setattr(entry.runtime_data.client_areas._store, "async_save", AsyncMock(side_effect=OSError("Fixture disk failure")))
    with pytest.raises(OSError):
        await entry.runtime_data.async_set_client_area_sync("home", True, False)
    assert not entry.runtime_data.client_areas.response("home")["enabled"]
    monkeypatch.setattr(entry.runtime_data.client_areas._store, "async_save", save)
    await entry.runtime_data.async_set_client_area_sync("home", True, False)
    path = Path(real_hass.config.path(".storage", f"{DOMAIN}.{entry.entry_id}.client_areas"))
    assert path.is_file()
    assert await real_hass.config_entries.async_remove(entry.entry_id)
    assert not path.exists()


async def test_saved_options_accept_only_explicit_booleans(real_hass):
    from test_stabilization_ha import entry_for_test

    from custom_components.google_wifi_insights.area_sync import ClientAreaSync

    entry = entry_for_test()
    await Store(real_hass, 1, f"{DOMAIN}.{entry.entry_id}.client_areas").async_save({
        "valid": {"enabled": True, "include_matched_devices": True}, "invalid": [],
        "text": {"enabled": "true", "include_matched_devices": 1},
    })
    sync = ClientAreaSync(real_hass, entry)
    await asyncio.gather(sync.async_load(), sync.async_load())
    assert sync.response("valid") == {"supported": True, "enabled": True, "include_matched_devices": True}
    assert sync.response("text") == sync.response("missing")
    assert "invalid" not in sync.settings
