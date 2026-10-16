"""Test area following, persistence and conservative name proposals in isolated HA."""

import copy
import json
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from gwi_test.management import generic_name, name_proposals
from homeassistant import config_entries
from homeassistant.core import Context
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import area_registry, device_registry
from test_ha import real_hass as real_hass
from test_stabilization_ha import DOMAIN, network_fixture, setup_fixture


@pytest.mark.parametrize("name,expected", [
    ("", True), ("client0", True), ("Unnamed Device", True), ("Unknown device", True),
    ("Dispositivo sem nome", True), ("1020ba7b29c*", True), ("02:00:00:00:00:01", True),
    ("Example phone", False), ("ESP sensor", False), ("coffee", False),
], ids=["blank", "id", "unnamed", "unknown", "localized", "hex", "mac", "custom", "host", "short"])
def test_only_explicit_placeholder_names_are_generic(name, expected):
    assert generic_name(name, "client0") is expected


def test_name_proposals_reject_ip_only_ambiguous_duplicate_and_custom_names():
    clients = {"ok": {"google_name": "Unnamed Device", "mac_address": "020000000001"},
               "ip": {"google_name": "Unnamed Device", "ip_address": "192.0.2.10"},
               "custom": {"google_name": "My chosen name", "mac_address": "02:00:00:00:00:01"},
               "conflict": {"google_name": "Unknown device", "mac_address": "02:00:00:00:00:02"}}
    records = [{"id": "ha1", "name": "Example phone", "macs": ["02:00:00:00:00:01"], "ips": ["192.0.2.10"]},
               {"id": "ha2", "name": "First", "macs": ["02:00:00:00:00:02"]},
               {"id": "ha3", "name": "Second", "macs": ["02:00:00:00:00:02"]}]
    original = copy.deepcopy(clients)
    candidates, skipped = name_proposals(clients, records)
    assert candidates == []  # Even a personalized station sharing this MAC is ambiguous.
    assert skipped == {"ambiguous_mac_match": 2, "no_exact_mac_match": 1, "personalized_name": 1}
    clients.pop("custom")
    candidates, _ = name_proposals(clients, records)
    assert candidates == [{"station_id": "ok", "google_name": "Unnamed Device", "proposed_name": "Example phone",
                           "mac_address": "02:00:00:00:00:01", "ha_device_id": "ha1", "match": "mac"}]
    assert original["ok"] == clients["ok"]  # Preview never changes the cached Google name.
    records.append({"id": "ha0", "name": "Example phone", "macs": ["02:00:00:00:00:01"]})
    assert name_proposals(clients, records)[0][0]["ha_device_id"] == "ha0"
    records[0]["name"] = "Unsafe\nname"
    records[-1]["name"] = "Unsafe\nname"
    assert name_proposals(clients, records)[0] == []


def carrier(hass, kind, metric, nid="home", sid=None):
    return next(s for s in hass.states.async_all() if s.attributes.get("gwi_network_id") == nid
                and s.attributes.get("gwi_kind") == kind and s.attributes.get("gwi_metric") == metric
                and (sid is None or s.attributes.get("gwi_item_id") == sid))


async def call(hass, service, data, context=None):
    return await hass.services.async_call(DOMAIN, service, data, context=context, blocking=True, return_response=True)


async def test_area_follows_roaming_and_never_changes_fixed_device_area(real_hass, monkeypatch):
    areas = area_registry.async_get(real_hass)
    first, second = areas.async_create("Example office"), areas.async_create("Example studio")
    network = network_fixture()
    network["points"]["other"] = {**copy.deepcopy(network["points"]["point"]), "name": "Other point"}
    snapshot = {"networks": {"home": network, "second-network": copy.deepcopy(network)}}
    entry = await setup_fixture(real_hass, monkeypatch, snapshot)
    registry = device_registry.async_get(real_hass)
    own = registry.async_get_device_by_identifier((DOMAIN, f"{entry.entry_id}:home:client:client0"), entry.entry_id)
    registry.async_update_device(own.id, area_id=first.id)
    ids = {device.id for device in device_registry.async_entries_for_config_entry(registry, entry.entry_id)}
    point = carrier(real_hass, "point", "clients", sid="point")
    other = carrier(real_hass, "point", "clients", sid="other")
    response = await call(real_hass, "set_point_area", {"entity_id": point.entity_id, "area_id": first.id})
    assert response["scope"] == f"{entry.entry_id}:home"
    await call(real_hass, "set_point_area", {"entity_id": other.entity_id, "area_id": second.id})
    await real_hass.async_block_till_done()
    assert carrier(real_hass, "client", "associated_area").state == first.name
    assert carrier(real_hass, "client", "associated_area", "second-network").state == "unknown"
    assert carrier(real_hass, "client", "point").attributes["associated_area_id"] == first.id
    network["clients"]["client0"]["ap_id"] = "other"
    await entry.runtime_data.async_refresh()
    await real_hass.async_block_till_done()
    assert carrier(real_hass, "client", "associated_area").state == second.name
    assert registry.async_get(own.id).area_id == first.id
    assert {device.id for device in device_registry.async_entries_for_config_entry(registry, entry.entry_id)} == ids
    assert await real_hass.config_entries.async_reload(entry.entry_id)
    await real_hass.async_block_till_done()
    assert carrier(real_hass, "client", "associated_area").state == second.name
    areas.async_update(second.id, name="Renamed studio")
    await real_hass.async_block_till_done()
    assert carrier(real_hass, "client", "associated_area").state == "Renamed studio"
    areas.async_delete(second.id)
    await real_hass.async_block_till_done()
    assert carrier(real_hass, "client", "associated_area").state == "unknown"
    await call(real_hass, "set_point_area", {"entity_id": point.entity_id, "area_id": None})
    assert entry.runtime_data.management.mappings["home"] == {"other": second.id}
    assert registry.async_get(own.id).area_id == first.id
    assert await real_hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize("change", ["disconnected", "wired", "missing-ap", "offline-point", "unreachable", "failed-network"], ids=str)
async def test_noncurrent_wireless_area_is_unknown(real_hass, monkeypatch, change):
    area = area_registry.async_get(real_hass).async_create("Example office")
    network = network_fixture()
    snapshot = {"networks": {"home": network}}
    entry = await setup_fixture(real_hass, monkeypatch, snapshot)
    await call(real_hass, "set_point_area", {"entity_id": carrier(real_hass, "point", "clients").entity_id, "area_id": area.id})
    client = network["clients"]["client0"]
    if change == "disconnected":
        client["connected"] = False
    elif change == "wired":
        client["connection_type"] = "WIRED"
    elif change == "missing-ap":
        client["ap_id"] = "missing"
    elif change == "offline-point":
        network["points"]["point"]["online"] = False
    elif change == "unreachable":
        network["points"]["point"]["reachable"] = False
    else:
        snapshot["networks"] = {}
        snapshot["network_errors"] = {"home": {"state": "denied"}}
    await entry.runtime_data.async_refresh()
    await real_hass.async_block_till_done()
    state = carrier(real_hass, "client", "associated_area")
    assert state.state == ("unavailable" if change == "failed-network" else "unknown")
    assert not state.attributes.get("associated_area_id")
    assert await real_hass.config_entries.async_unload(entry.entry_id)


async def test_management_services_are_cached_admin_scoped_and_validate_targets(real_hass, monkeypatch):
    entry = await setup_fixture(real_hass, monkeypatch, {"networks": {"home": network_fixture()}})
    coordinator = entry.runtime_data
    snapshot, write = coordinator.client.snapshot, AsyncMock()
    monkeypatch.setattr(coordinator.client, "action", write)
    point, network = carrier(real_hass, "point", "clients"), carrier(real_hass, "network", "diagnosis")
    initial_reads = snapshot.call_count
    data = await call(real_hass, "get_management", {"entity_id": network.entity_id})
    assert data["rename"] == {"state": "request_schema_unverified", "writable": False}
    assert data["points"][0]["entity_id"] == point.entity_id
    assert snapshot.call_count == initial_reads
    with pytest.raises(HomeAssistantError, match="existing Home Assistant area"):
        await call(real_hass, "set_point_area", {"entity_id": point.entity_id, "area_id": "invented"})
    with pytest.raises(HomeAssistantError, match="point entity"):
        await call(real_hass, "set_point_area", {"entity_id": network.entity_id, "area_id": None})
    with pytest.raises(HomeAssistantError, match="current Google WiFi point"):
        await coordinator.async_set_point_area("home", "missing-point", None)
    real_hass.auth = SimpleNamespace(async_get_user=AsyncMock(return_value=SimpleNamespace(is_admin=False)))
    for service, service_data in [("get_management", {"entity_id": network.entity_id}),
                                  ("set_point_area", {"entity_id": point.entity_id, "area_id": None})]:
        with pytest.raises(HomeAssistantError, match="administrator"):
            await call(real_hass, service, service_data, Context(user_id="non-admin"))
    write.assert_not_awaited()
    assert await real_hass.config_entries.async_unload(entry.entry_id)


async def test_area_registry_event_does_not_turn_failed_poll_into_success(real_hass, monkeypatch):
    from custom_components.google_wifi_insights.api import ApiError

    entry = await setup_fixture(real_hass, monkeypatch, {"networks": {"home": network_fixture()}})
    area = area_registry.async_get(real_hass).async_create("Example office")
    await call(real_hass, "set_point_area", {"entity_id": carrier(real_hass, "point", "clients").entity_id, "area_id": area.id})
    monkeypatch.setattr(entry.runtime_data.client, "snapshot", AsyncMock(side_effect=ApiError("Fixture poll failure")))
    await entry.runtime_data.async_refresh()
    area_registry.async_get(real_hass).async_update(area.id, name="Renamed during outage")
    await real_hass.async_block_till_done()
    assert entry.runtime_data.last_update_success is False
    assert carrier(real_hass, "client", "associated_area").state == "unavailable"
    assert await real_hass.config_entries.async_unload(entry.entry_id)


async def test_names_use_discovered_mac_and_stay_private_to_management(real_hass, monkeypatch):
    from custom_components.google_wifi_insights.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    other = config_entries.ConfigEntry(data={}, domain="mqtt", discovery_keys=MappingProxyType({}), options={},
        source="user", title="Fictional discovery", unique_id="fixture-mqtt", version=1, minor_version=1,
        subentries_data=None)
    # Represent another loaded integration without starting its transport.
    real_hass.config_entries._entries[other.entry_id] = other
    matched = device_registry.async_get(real_hass).async_get_or_create(config_entry_id=other.entry_id,
        identifiers={("mqtt", "fictional-device")}, connections={(device_registry.CONNECTION_NETWORK_MAC, "02:00:00:00:00:01")},
        name="Example phone")
    network = network_fixture()
    network["clients"]["client0"].update(name="Unnamed Device", google_name="Unnamed Device", mac_address="02:00:00:00:00:01")
    snapshot = {"networks": {"home": network}}
    entry = await setup_fixture(real_hass, monkeypatch, snapshot)
    data = await call(real_hass, "get_management", {"entity_id": carrier(real_hass, "network", "diagnosis").entity_id})
    assert data["name_candidates"][0]["ha_device_id"] == matched.id
    assert data["name_candidates"][0]["proposed_name"] == "Example phone"
    assert data["name_candidates"][0]["entity_id"] == carrier(real_hass, "client", "point").entity_id
    exported = json.dumps(await async_get_config_entry_diagnostics(real_hass, entry))
    assert "Example phone" not in exported and matched.id not in exported and "02:00:00:00:00:01" not in exported
    # A later personalized name is preserved and no longer offered for remediation.
    network["clients"]["client0"]["google_name"] = "My custom Google label"
    await entry.runtime_data.async_refresh()
    data = await call(real_hass, "get_management", {"entity_id": carrier(real_hass, "network", "diagnosis").entity_id})
    assert data["name_candidates"] == []
    assert await real_hass.config_entries.async_remove(entry.entry_id)


async def test_removing_entry_cleans_mapping_storage(real_hass, monkeypatch):
    area = area_registry.async_get(real_hass).async_create("Example office")
    entry = await setup_fixture(real_hass, monkeypatch, {"networks": {"home": network_fixture()}})
    await call(real_hass, "set_point_area", {"entity_id": carrier(real_hass, "point", "clients").entity_id, "area_id": area.id})
    path = Path(real_hass.config.path(".storage", f"{DOMAIN}.{entry.entry_id}.areas"))
    assert path.is_file()
    assert await real_hass.config_entries.async_remove(entry.entry_id)
    assert not path.exists()


async def test_poll_failure_during_mapping_save_keeps_entities_unavailable(real_hass, monkeypatch):
    from custom_components.google_wifi_insights.api import ApiError

    area = area_registry.async_get(real_hass).async_create("Example office")
    entry = await setup_fixture(real_hass, monkeypatch, {"networks": {"home": network_fixture()}})
    coordinator = entry.runtime_data
    save = coordinator.management._store.async_save

    async def save_during_outage(data):
        await save(data)
        monkeypatch.setattr(coordinator.client, "snapshot", AsyncMock(side_effect=ApiError("Fixture outage")))
        await coordinator.async_refresh()

    monkeypatch.setattr(coordinator.management._store, "async_save", save_during_outage)
    await coordinator.async_set_point_area("home", "point", area.id)
    await real_hass.async_block_till_done()
    assert coordinator.management.mappings["home"]["point"] == area.id
    assert coordinator.last_update_success is False
    assert carrier(real_hass, "client", "associated_area").state == "unavailable"
    assert await real_hass.config_entries.async_unload(entry.entry_id)
