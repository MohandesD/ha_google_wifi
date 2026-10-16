"""Exercise verified name writes, uncertain delivery, undo and automatic opt-in."""

import asyncio
import copy
import json
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from homeassistant import config_entries
from homeassistant.core import Context
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry
from test_ha import real_hass as real_hass
from test_management import call, carrier
from test_stabilization_ha import network_fixture, setup_fixture

MAC = "02:00:00:00:00:01"
OLD = "Unnamed Device"
NAME = "Example phone"


async def setup_names(hass, monkeypatch):
    other = config_entries.ConfigEntry(data={}, domain="mqtt", discovery_keys=MappingProxyType({}), options={},
        source="user", title="Fictional discovery", unique_id="fixture-mqtt", version=1, minor_version=1, subentries_data=None)
    hass.config_entries._entries[other.entry_id] = other
    device = device_registry.async_get(hass).async_get_or_create(config_entry_id=other.entry_id,
        identifiers={("mqtt", "fictional-device")}, connections={(device_registry.CONNECTION_NETWORK_MAC, MAC)}, name=NAME)
    network = network_fixture()
    network["clients"]["client0"].update(name=OLD, google_name=OLD, mac_address=MAC)
    snapshot = {"networks": {"home": network, "other": copy.deepcopy(network)}}
    entry = await setup_fixture(hass, monkeypatch, snapshot)
    provider = {"name": OLD, "raw_name": OLD, "automatic_name": OLD, "mac": MAC}
    identity = AsyncMock(side_effect=lambda *args: dict(provider))

    async def write(nid, sid, name):
        names = entry.runtime_data.names
        record = names.network(nid)["history"][-1]
        assert record["state"] == "unconfirmed"
        path = Path(hass.config.path(".storage", f"google_wifi_insights.{entry.entry_id}.names"))
        assert record["request_id"] in path.read_text(encoding="utf-8")
        value = OLD if name is None else name
        provider.update(name=value, raw_name=value)
        return {}  # Google's UpdateStationNameResponse is empty.

    writer = AsyncMock(side_effect=write)
    monkeypatch.setattr(entry.runtime_data.client, "station_identity", identity)
    monkeypatch.setattr(entry.runtime_data.client, "set_station_name", writer)
    return entry, provider, identity, writer, device, snapshot


async def rename(entry):
    return await entry.runtime_data.names.async_rename("home", "client0", OLD, MAC, NAME)


async def test_verified_rename_persists_intent_updates_map_and_can_restore_automatic_name(real_hass, monkeypatch):
    from custom_components.google_wifi_insights.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    entry, provider, identity, writer, device, _ = await setup_names(real_hass, monkeypatch)
    assert entry.runtime_data.names.summary("home")["enabled"] is False
    result = await rename(entry)
    assert result["state"] == "verified" and result["restore_automatic"] is True
    assert carrier(real_hass, "client", "point").attributes["google_name"] == NAME
    assert carrier(real_hass, "client", "point").attributes["device_name"] == NAME
    assert provider["name"] == NAME and writer.call_count == 1 and identity.call_count == 2
    assert entry.runtime_data.names.response("other")["history"] == []
    diagnostics = json.dumps(await async_get_config_entry_diagnostics(real_hass, entry))
    assert result["request_id"] not in diagnostics and MAC not in diagnostics and device.id not in diagnostics
    undone = await entry.runtime_data.names.async_undo("home", result["request_id"])
    assert undone["state"] == "verified" and provider["name"] == OLD
    assert writer.call_args.args == ("home", "client0", None)
    assert "client0" in entry.runtime_data.names.response("home")["excluded_station_ids"]
    with pytest.raises(HomeAssistantError, match="later request"):
        await entry.runtime_data.names.async_undo("home", result["request_id"])
    assert await real_hass.config_entries.async_remove(entry.entry_id)


@pytest.mark.parametrize("failure", ["google-name", "mac", "ha-name", "preview", "preflight", "too-long"], ids=str)
async def test_stale_or_unverified_identity_never_sends_a_write(real_hass, monkeypatch, failure):
    from custom_components.google_wifi_insights.api import ApiError

    entry, provider, identity, writer, device, _ = await setup_names(real_hass, monkeypatch)
    expected = NAME
    if failure == "google-name":
        provider["name"] = "A manager chose this name"
    elif failure == "mac":
        provider["mac"] = "02:00:00:00:00:02"
    elif failure == "ha-name":
        device_registry.async_get(real_hass).async_update_device(device.id, name_by_user="Changed HA name")
    elif failure == "preview":
        expected = "Unapproved replacement"
    elif failure == "too-long":
        expected = "x" * 64
        device_registry.async_get(real_hass).async_update_device(device.id, name_by_user=expected)
    else:
        identity.side_effect = ApiError("Fresh identity unavailable")
    with pytest.raises(HomeAssistantError):
        await entry.runtime_data.names.async_rename("home", "client0", OLD, MAC, expected)
    writer.assert_not_awaited()
    assert entry.runtime_data.names.response("home")["history"] == []
    assert await real_hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize("failure", ["lost-response", "readback-denied", "ignored-write", "rejected"], ids=str)
async def test_failed_delivery_or_readback_is_never_retried_or_reported_complete(real_hass, monkeypatch, failure):
    from custom_components.google_wifi_insights.api import ApiError

    entry, provider, identity, writer, _, _ = await setup_names(real_hass, monkeypatch)
    if failure == "lost-response":
        writer.side_effect = ApiError("Connection closed")
    elif failure == "readback-denied":
        identity.side_effect = [dict(provider), ApiError("Read-back denied", status=403)]
    elif failure == "ignored-write":
        writer.side_effect = None
        writer.return_value = {}
    else:
        writer.side_effect = ApiError("Write rejected", status=400)
    result = await rename(entry)
    assert result["state"] == ("rejected" if failure == "rejected" else "unconfirmed")
    assert carrier(real_hass, "client", "point").attributes["google_name"] == OLD
    assert entry.runtime_data.names.summary("home")["paused_reason"]
    if result["state"] == "unconfirmed":
        with pytest.raises(HomeAssistantError, match="unconfirmed"):
            await rename(entry)
    assert writer.call_count == 1
    assert await real_hass.config_entries.async_unload(entry.entry_id)


async def test_verify_uncertain_write_is_read_only_and_undo_preserves_subsequent_manager_changes(real_hass, monkeypatch):
    from custom_components.google_wifi_insights.api import ApiError

    entry, provider, identity, writer, _, _ = await setup_names(real_hass, monkeypatch)
    identity.side_effect = [dict(provider), ApiError("Read-back unavailable")]
    result = await rename(entry)
    identity.side_effect = lambda *args: dict(provider)
    verified = await entry.runtime_data.names.async_verify("home", result["request_id"])
    assert verified["state"] == "verified" and writer.call_count == 1
    provider["name"] = "Later manager change"
    with pytest.raises(HomeAssistantError, match="changed since"):
        await entry.runtime_data.names.async_undo("home", result["request_id"])
    with pytest.raises(HomeAssistantError, match="this network"):
        await entry.runtime_data.names.async_verify("other", result["request_id"])
    assert writer.call_count == 1
    assert await real_hass.config_entries.async_unload(entry.entry_id)


async def test_unconfirmed_undo_does_not_inherit_a_previous_verified_observation(real_hass, monkeypatch):
    from custom_components.google_wifi_insights.api import ApiError

    entry, provider, identity, writer, _, _ = await setup_names(real_hass, monkeypatch)
    original = await rename(entry)
    assert original["observed_name"] == NAME
    identity.side_effect = [dict(provider), ApiError("Read-back unavailable")]
    undone = await entry.runtime_data.names.async_undo("home", original["request_id"])
    assert undone["state"] == "unconfirmed" and undone["new_name"] == OLD
    assert "observed_name" not in undone
    identity.side_effect = lambda *args: dict(provider)
    verified = await entry.runtime_data.names.async_verify("home", undone["request_id"])
    assert verified["state"] == "verified" and verified["observed_name"] == OLD
    assert writer.call_count == 2
    assert await real_hass.config_entries.async_unload(entry.entry_id)


async def test_automatic_sync_requires_persisted_network_opt_in_and_is_bounded(real_hass, monkeypatch):
    entry, provider, _, writer, _, _ = await setup_names(real_hass, monkeypatch)
    names = entry.runtime_data.names
    await names.async_automatic()
    writer.assert_not_awaited()
    # Keep scheduling deterministic while exercising the real batch worker.
    monkeypatch.setattr(entry.runtime_data, "_schedule_name_sync", lambda: None)
    await names.async_set_enabled("home", True)
    await names.async_automatic()
    assert writer.call_count == 1 and provider["name"] == NAME
    assert names.automatic_due() is False
    assert names.summary("other")["enabled"] is False
    await names.async_automatic()
    assert writer.call_count == 1
    path = Path(real_hass.config.path(".storage", f"google_wifi_insights.{entry.entry_id}.names"))
    assert path.is_file()
    assert await real_hass.config_entries.async_unload(entry.entry_id)
    assert path.is_file()  # Unload preserves intent and audit history.


async def test_services_require_interactive_admin_and_can_disable_during_outage(real_hass, monkeypatch):
    entry, _, _, writer, _, _ = await setup_names(real_hass, monkeypatch)
    real_hass.auth = SimpleNamespace(async_get_user=AsyncMock(return_value=SimpleNamespace(is_admin=True)))
    admin = Context(user_id="admin")
    point = carrier(real_hass, "client", "point").entity_id
    network = carrier(real_hass, "network", "diagnosis").entity_id
    request = {"entity_id": point, "expected_google_name": OLD, "expected_mac": MAC, "expected_ha_name": NAME}
    with pytest.raises(HomeAssistantError, match="interactive"):
        await call(real_hass, "rename_client", request)
    with pytest.raises(HomeAssistantError, match="interactive"):
        await call(real_hass, "set_name_sync", {"entity_id": network, "enabled": True})
    real_hass.auth.async_get_user.return_value = SimpleNamespace(is_admin=False)
    with pytest.raises(HomeAssistantError, match="administrator"):
        await call(real_hass, "rename_client", request, Context(user_id="guest"))
    real_hass.auth.async_get_user.return_value = SimpleNamespace(is_admin=True)
    data = await call(real_hass, "rename_client", request, admin)
    assert data["name_result"]["state"] == "verified"
    assert data["name_candidates"] == []
    request_id = data["name_result"]["request_id"]
    verified = await call(real_hass, "verify_name", {"entity_id": network, "request_id": request_id}, admin)
    assert verified["name_result"]["state"] == "verified"
    undone = await call(real_hass, "undo_name", {"entity_id": network, "request_id": request_id}, admin)
    assert undone["name_result"]["state"] == "verified"
    monkeypatch.setattr(entry.runtime_data, "_schedule_name_sync", lambda: None)
    await call(real_hass, "set_name_sync", {"entity_id": network, "enabled": True}, admin)
    entry.runtime_data.async_set_update_error(HomeAssistantError("Fixture outage"))
    data = await call(real_hass, "set_name_sync", {"entity_id": network, "enabled": False}, admin)
    assert data["rename"]["enabled"] is False and data["available"] is False
    assert writer.call_count == 2
    assert await real_hass.config_entries.async_unload(entry.entry_id)


async def test_concurrent_requests_do_not_send_duplicate_renames(real_hass, monkeypatch):
    entry, _, _, writer, _, _ = await setup_names(real_hass, monkeypatch)
    results = await asyncio.gather(rename(entry), rename(entry), return_exceptions=True)
    assert sum(isinstance(r, HomeAssistantError) for r in results) == 1
    assert writer.call_count == 1
    assert await real_hass.config_entries.async_unload(entry.entry_id)


async def test_enabling_schedules_a_real_bounded_background_batch(real_hass, monkeypatch):
    entry, _, identity, writer, device, snapshot = await setup_names(real_hass, monkeypatch)
    network = network_fixture(4)
    providers = {}
    registry = device_registry.async_get(real_hass)
    for i, client in enumerate(network["clients"].values()):
        mac, name = f"02:00:00:00:00:{i+1:02x}", f"Example phone {i}"
        client.update(name=OLD, google_name=OLD, mac_address=mac)
        if i == 0:
            registry.async_update_device(device.id, name_by_user=name)
        else:
            registry.async_get_or_create(config_entry_id=device.config_entry_id, identifiers={("mqtt", f"fixture-{i}")},
                connections={(device_registry.CONNECTION_NETWORK_MAC, mac)}, name=name)
        providers[f"client{i}"] = {"name": OLD, "raw_name": OLD, "automatic_name": OLD, "mac": mac}
    snapshot["networks"]["home"] = network
    await entry.runtime_data.async_refresh()
    identity.side_effect = lambda nid, sid: dict(providers[sid])

    async def write(nid, sid, name):
        providers[sid].update(name=name, raw_name=name)
        snapshot["networks"][nid]["clients"][sid]["google_name"] = name
        return {}

    writer.side_effect = write
    real_hass.auth = SimpleNamespace(async_get_user=AsyncMock(return_value=SimpleNamespace(is_admin=True)))
    network_entity = carrier(real_hass, "network", "diagnosis").entity_id
    await call(real_hass, "set_name_sync", {"entity_id": network_entity, "enabled": True}, Context(user_id="admin"))
    await asyncio.wait_for(entry.runtime_data._name_task, 5)
    assert writer.call_count == 3
    assert entry.runtime_data.names.summary("home")["verified_count"] == 3
    assert all(call.args[0] == "home" for call in writer.call_args_list)
    entry.runtime_data._schedule_name_sync()
    assert writer.call_count == 3  # The five-minute cooldown prevents a second batch.
    assert await real_hass.config_entries.async_unload(entry.entry_id)


async def test_unload_cancels_automatic_writer_and_restored_intent_pauses_after_uncertainty(real_hass, monkeypatch):
    from custom_components.google_wifi_insights.naming import NameSync

    entry, _, _, writer, _, _ = await setup_names(real_hass, monkeypatch)
    started = asyncio.Event()

    async def stalled_write(*args):
        started.set()
        await asyncio.Event().wait()

    writer.side_effect = stalled_write
    await entry.runtime_data.names.async_set_enabled("home", True)
    await asyncio.wait_for(started.wait(), 5)
    coordinator = entry.runtime_data
    task = coordinator._name_task
    assert await real_hass.config_entries.async_unload(entry.entry_id)
    assert task.cancelled()
    restored = NameSync(coordinator)
    await restored.async_load()
    assert restored.summary("home")["paused_reason"] == "previous_write_unconfirmed"
    assert restored.summary("home")["unconfirmed_count"] == 1
    assert restored.automatic_due() is False
    assert writer.call_count == 1


async def test_storage_failure_and_changed_ha_name_during_save_prevent_provider_writes(real_hass, monkeypatch):
    entry, _, _, writer, device, _ = await setup_names(real_hass, monkeypatch)
    names = entry.runtime_data.names
    save = names._store.async_save
    monkeypatch.setattr(names._store, "async_save", AsyncMock(side_effect=OSError("Fixture storage failure")))
    with pytest.raises(OSError):
        await rename(entry)
    writer.assert_not_awaited()

    async def change_during_save(data):
        await save(data)
        device_registry.async_get(real_hass).async_update_device(device.id, name_by_user="New HA choice")

    monkeypatch.setattr(names._store, "async_save", change_during_save)
    with pytest.raises(HomeAssistantError, match="changed"):
        await rename(entry)
    writer.assert_not_awaited()
    assert names.response("home")["history"][-1]["state"] == "cancelled"
    assert await real_hass.config_entries.async_unload(entry.entry_id)


async def test_manual_writer_does_not_recreate_storage_after_integration_removal(real_hass, monkeypatch):
    entry, _, _, writer, _, _ = await setup_names(real_hass, monkeypatch)
    started, release = asyncio.Event(), asyncio.Event()

    async def stalled(*args):
        started.set()
        await release.wait()
        return {}

    writer.side_effect = stalled
    task = asyncio.create_task(rename(entry))
    await asyncio.wait_for(started.wait(), 5)
    path = Path(real_hass.config.path(".storage", f"google_wifi_insights.{entry.entry_id}.names"))
    assert await real_hass.config_entries.async_remove(entry.entry_id)
    release.set()
    assert (await asyncio.wait_for(task, 5))["state"] == "unconfirmed"
    assert not path.exists()
