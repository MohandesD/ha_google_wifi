"""Exercise 0.9.3 failure recovery and upgrade defaults in an isolated HA."""

import copy
from types import MappingProxyType, SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from homeassistant import config_entries
from homeassistant.core import Context
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry, entity_registry
from test_ha import DOMAIN
from test_ha import real_hass as real_hass


def entry_for_test(options=None, disabled_by=None):
    return config_entries.ConfigEntry(
        data={"mode": "cloud", "email": "tester@example.invalid", "master_token": "fictional", "android_id": "0" * 16},
        domain=DOMAIN, discovery_keys=MappingProxyType({}), options=options or {}, source="user",
        title="Fixture WiFi", unique_id="stabilization", version=1, minor_version=1, subentries_data=None,
        disabled_by=disabled_by,
    )


def network_fixture(count=1):
    from custom_components.google_wifi_insights.model import cloud_network

    stations = [{"id": f"client{i}", "friendlyName": f"Example client {i}", "connected": True,
                 "apId": "point", "connectionType": "WIRELESS"} for i in range(count)]
    return cloud_network(
        {"name": "Example WiFi", "accessPoints": [{"id": "point"}]},
        {"apStatuses": [{"apId": "point", "apState": "AP_ONLINE"}]}, stations, {},
    )


async def setup_fixture(hass, monkeypatch, snapshot, options=None):
    from custom_components.google_wifi_insights.api import CloudClient

    monkeypatch.setattr(CloudClient, "snapshot", AsyncMock(side_effect=lambda: copy.deepcopy(snapshot)))
    entry = entry_for_test(options)
    await hass.config_entries.async_add(entry)
    await hass.async_block_till_done()
    assert entry.state == config_entries.ConfigEntryState.LOADED
    return entry


async def test_enum_states_use_valid_translation_keys_and_preserve_raw_map_attributes(real_hass, monkeypatch):
    network = network_fixture()
    network["clients"]["client0"]["wireless_band"] = "BAND_5000_MHZ"
    entry = await setup_fixture(real_hass, monkeypatch, {"networks": {"home": network}})
    states = {s.attributes.get("gwi_metric"): s for s in real_hass.states.async_all()
              if s.attributes.get("gwi_kind") == "client"}
    assert states["wireless_band"].state == "band_5000_mhz"
    assert states["connection_type"].state == "wireless"
    assert states["point"].attributes["wireless_band"] == "BAND_5000_MHZ"
    assert states["point"].attributes["connection_type"] == "WIRELESS"
    assert await real_hass.config_entries.async_unload(entry.entry_id)


async def test_partial_failure_marks_only_failed_network_unavailable_and_recovers_ids(real_hass, monkeypatch):
    snapshot = {"networks": {"first": network_fixture(), "second": network_fixture()}, "network_errors": {}}
    entry = await setup_fixture(real_hass, monkeypatch, snapshot)
    registry = device_registry.async_get(real_hass)
    device_ids = {device.id for device in device_registry.async_entries_for_config_entry(registry, entry.entry_id)}
    state_ids = {state.entity_id for state in real_hass.states.async_all()}
    failed = next(s.entity_id for s in real_hass.states.async_all()
                  if s.attributes.get("gwi_network_id") == "second" and s.attributes.get("gwi_metric") == "point")
    snapshot["networks"].pop("second")
    snapshot["network_errors"] = {"second": {"state": "denied", "http_status": 403}}
    await entry.runtime_data.async_refresh()
    await real_hass.async_block_till_done()
    assert entry.runtime_data.last_update_success
    states = real_hass.states.async_all()
    assert all(s.state == "unavailable" for s in states if s.attributes.get("gwi_network_id") == "second")
    healthy = next(s for s in states if s.attributes.get("gwi_network_id") == "first"
                   and s.attributes.get("gwi_metric") == "connected_clients")
    assert healthy.state == "1"
    write = AsyncMock()
    monkeypatch.setattr(entry.runtime_data.client, "action", write)
    with pytest.raises(HomeAssistantError, match="unavailable"):
        await real_hass.services.async_call(DOMAIN, "google_action", {"entity_id": failed, "action": "pause_client"}, blocking=True)
    with pytest.raises(HomeAssistantError, match="unavailable"):
        await entry.runtime_data.async_set_roaming("second", "client0", "interval", 60)
    write.assert_not_awaited()
    snapshot["networks"]["second"] = network_fixture()
    snapshot["network_errors"] = {}
    await entry.runtime_data.async_refresh()
    await real_hass.async_block_till_done()
    assert real_hass.states.get(failed).state != "unavailable"
    assert {s.entity_id for s in real_hass.states.async_all()} == state_ids
    assert {device.id for device in device_registry.async_entries_for_config_entry(registry, entry.entry_id)} == device_ids
    assert await real_hass.config_entries.async_unload(entry.entry_id)


async def test_experimental_and_destructive_actions_need_separate_explicit_opt_in(real_hass, monkeypatch):
    entry = await setup_fixture(real_hass, monkeypatch, {"networks": {"home": network_fixture()}})
    coordinator = entry.runtime_data
    write = AsyncMock(return_value={"state": "CREATED"})
    monkeypatch.setattr(coordinator.client, "action", write)
    real_hass.auth = SimpleNamespace(async_get_user=AsyncMock(return_value=SimpleNamespace(is_admin=True)))
    admin = Context(user_id="administrator")
    for action, parameters in (("create_device_group", {}), ("remove_network", {})):
        with pytest.raises(HomeAssistantError, match="Experimental"):
            await coordinator.async_google_action("home", "network", "home", action, parameters, admin)
    # Use a synthetic options view here so the same coordinator is exercised.
    coordinator.config_entry = SimpleNamespace(options={"allow_advanced_actions": True})
    with pytest.raises(HomeAssistantError, match="Destructive"):
        await coordinator.async_google_action("home", "network", "home", "remove_network", {}, admin)
    coordinator.config_entry.options["allow_destructive_actions"] = True
    with pytest.raises(HomeAssistantError, match="exact network"):
        await coordinator.async_google_action("home", "network", "home", "remove_network", {}, admin)
    with pytest.raises(HomeAssistantError, match="interactive administrator"):
        await coordinator.async_google_action("home", "network", "home", "remove_network", {}, None)
    write.assert_not_awaited()
    coordinator.config_entry = entry
    assert await real_hass.config_entries.async_unload(entry.entry_id)


async def test_controls_options_preserve_polling_and_require_both_removal_flags(real_hass, monkeypatch):
    snapshot = {"networks": {"home": network_fixture()}}
    entry = await setup_fixture(real_hass, monkeypatch, snapshot, {"scan_interval": 300})
    original_ids = {state.entity_id for state in real_hass.states.async_all()}
    options = await real_hass.config_entries.options.async_init(entry.entry_id)
    form = await real_hass.config_entries.options.async_configure(options["flow_id"], {"next_step_id": "controls"})
    invalid = await real_hass.config_entries.options.async_configure(form["flow_id"], {
        "allow_advanced_actions": False, "allow_destructive_actions": True,
    })
    assert invalid["errors"] == {"base": "advanced_required"}
    assert entry.options == {"scan_interval": 300}
    result = await real_hass.config_entries.options.async_configure(form["flow_id"], {
        "allow_advanced_actions": True, "allow_destructive_actions": False,
    })
    assert result["type"] == "create_entry"
    await real_hass.async_block_till_done()
    assert entry.options == {"scan_interval": 300, "allow_advanced_actions": True, "allow_destructive_actions": False}
    assert {state.entity_id for state in real_hass.states.async_all()} == original_ids
    assert await real_hass.config_entries.async_unload(entry.entry_id)


async def test_existing_enabled_diagnostic_survives_new_disabled_default_and_reload(real_hass, monkeypatch):
    from custom_components.google_wifi_insights.api import CloudClient

    snapshot = {"networks": {"home": network_fixture()}}
    monkeypatch.setattr(CloudClient, "snapshot", AsyncMock(side_effect=lambda: copy.deepcopy(snapshot)))
    entry = entry_for_test(disabled_by=config_entries.ConfigEntryDisabler.USER)
    await real_hass.config_entries.async_add(entry)
    registry = entity_registry.async_get(real_hass)
    unique_id = f"{entry.entry_id}:home:client:client0:google_telemetry_at"
    existing = registry.async_get_or_create("sensor", DOMAIN, unique_id, config_entry=entry,
                                           suggested_object_id="existing_client_telemetry", disabled_by=None)
    await real_hass.config_entries.async_set_disabled_by(entry.entry_id, None)
    await real_hass.async_block_till_done()
    assert registry.async_get(existing.entity_id).disabled_by is None
    assert real_hass.states.get(existing.entity_id) is not None
    defaults = [entity for entity in entity_registry.async_entries_for_config_entry(registry, entry.entry_id)
                if entity.translation_key in {"rx_spatial_streams", "wireless_standard"}]
    assert defaults and all(entity.disabled_by == entity_registry.RegistryEntryDisabler.INTEGRATION for entity in defaults)
    original_ids = {entity.entity_id for entity in entity_registry.async_entries_for_config_entry(registry, entry.entry_id)}
    assert await real_hass.config_entries.async_reload(entry.entry_id)
    await real_hass.async_block_till_done()
    assert real_hass.states.get(existing.entity_id) is not None
    assert {entity.entity_id for entity in entity_registry.async_entries_for_config_entry(registry, entry.entry_id)} == original_ids
    assert await real_hass.config_entries.async_unload(entry.entry_id)


async def test_manual_stale_device_removal_refuses_live_devices_and_partial_outages(real_hass, monkeypatch):
    from custom_components.google_wifi_insights import async_remove_config_entry_device

    snapshot = {"networks": {"home": network_fixture()}}
    entry = await setup_fixture(real_hass, monkeypatch, snapshot)
    registry = device_registry.async_get(real_hass)
    client = registry.async_get_device_by_identifier((DOMAIN, f"{entry.entry_id}:home:client:client0"), entry.entry_id)
    assert not await async_remove_config_entry_device(real_hass, entry, client)
    entry.runtime_data.data["networks"]["home"]["clients"].clear()
    assert await async_remove_config_entry_device(real_hass, entry, client)
    entry.runtime_data.data["network_errors"] = {"other": {"state": "denied"}}
    assert not await async_remove_config_entry_device(real_hass, entry, client)
    foreign = SimpleNamespace(identifiers={("shelly", "foreign")})
    entry.runtime_data.data["network_errors"] = {}
    assert not await async_remove_config_entry_device(real_hass, entry, foreign)
    assert await real_hass.config_entries.async_unload(entry.entry_id)


async def test_read_services_use_current_registry_targets_and_filter_credentials(real_hass, monkeypatch):
    entry = await setup_fixture(real_hass, monkeypatch, {"networks": {"home": network_fixture()}})
    states = real_hass.states.async_all()
    network = next(s.entity_id for s in states if s.attributes.get("gwi_kind") == "network" and s.attributes.get("gwi_metric") == "diagnosis")
    point = next(s.entity_id for s in states if s.attributes.get("gwi_kind") == "point" and s.attributes.get("gwi_metric") == "clients")
    client = next(s.entity_id for s in states if s.attributes.get("gwi_kind") == "client" and s.attributes.get("gwi_metric") == "point")
    coordinator = entry.runtime_data
    coordinator.data["networks"]["home"]["google_telemetry"] = {"firmware": "1.2.3", "password": "fictional-secret"}
    coordinator.client._optional_cache = {"home": {"speedTestResults": {"download": 123}, "oauth_token": "fictional-secret"}}

    async def read(service, target=network, context=None):
        return await real_hass.services.async_call(DOMAIN, service, {"entity_id": target}, blocking=True, return_response=True, context=context)

    result = await read("get_google_metrics")
    assert result["metrics"] == {"firmware": "1.2.3"}
    assert result["saved_results"] == {"speedTestResults": {"download": 123}}
    assert "capabilities" in await read("get_capabilities")
    with pytest.raises(HomeAssistantError, match="not per point"):
        await read("get_usage_history", point)
    with pytest.raises(HomeAssistantError, match="not supplied"):
        await read("get_usage_history", client)
    with pytest.raises(HomeAssistantError, match="Select an entity"):
        await read("get_google_metrics", "sensor.not_registered")
    coordinator.last_update_success = False
    with pytest.raises(HomeAssistantError, match="unavailable"):
        await read("get_capabilities")
    coordinator.last_update_success = True
    real_hass.auth = SimpleNamespace(async_get_user=AsyncMock(return_value=SimpleNamespace(is_admin=False)))
    for service in ("get_google_metrics", "get_capabilities", "get_usage_history"):
        with pytest.raises(HomeAssistantError, match="administrator"):
            await read(service, context=Context(user_id="reader"))
    assert await real_hass.config_entries.async_unload(entry.entry_id)


async def test_provider_point_metadata_refresh_preserves_user_name_and_device_id(real_hass, monkeypatch):
    snapshot = {"networks": {"home": network_fixture()}}
    original = snapshot["networks"]["home"]["points"]["point"]
    original.update(name="Example point A", firmware="1.2.3")
    entry = await setup_fixture(real_hass, monkeypatch, snapshot)
    registry = device_registry.async_get(real_hass)
    device = registry.async_get_device_by_identifier((DOMAIN, f"{entry.entry_id}:home:point:point"), entry.entry_id)
    assert device.sw_version == "1.2.3"
    registry.async_update_device(device.id, name_by_user="My point name")
    original.update(name="Example point B", firmware="1.2.4")
    await entry.runtime_data.async_refresh()
    await real_hass.async_block_till_done()
    updated = registry.async_get(device.id)
    assert updated.sw_version == "1.2.4" and updated.name == "Example point B"
    assert updated.name_by_user == "My point name"
    assert await real_hass.config_entries.async_unload(entry.entry_id)


async def test_entry_removal_unloads_only_its_devices_and_services_fail_cleanly(real_hass, monkeypatch):
    entry = await setup_fixture(real_hass, monkeypatch, {"networks": {"home": network_fixture()}})
    registry = device_registry.async_get(real_hass)
    states = {s.entity_id for s in real_hass.states.async_all() if s.attributes.get("gwi_kind")}
    unrelated = {s.entity_id for s in real_hass.states.async_all()} - states
    network = next(s.entity_id for s in real_hass.states.async_all() if s.attributes.get("gwi_kind") == "network")
    assert await real_hass.config_entries.async_remove(entry.entry_id) == {"require_restart": False}
    await real_hass.async_block_till_done()
    assert not device_registry.async_entries_for_config_entry(registry, entry.entry_id)
    assert not states & {s.entity_id for s in real_hass.states.async_all()}
    assert unrelated <= {s.entity_id for s in real_hass.states.async_all()}
    assert real_hass.services.has_service(DOMAIN, "get_capabilities")
    with pytest.raises(HomeAssistantError):
        await real_hass.services.async_call(DOMAIN, "get_capabilities", {"entity_id": network}, blocking=True, return_response=True)
