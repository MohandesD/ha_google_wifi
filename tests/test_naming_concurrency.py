"""Bounded real-HA naming concurrency with fictional client identities only."""

import asyncio
import time
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry
from test_ha import real_hass as real_hass
from test_naming import OLD, setup_names
from test_stabilization_ha import network_fixture


async def setup_clients(hass, monkeypatch, count=7):
    entry, _, identity, writer, device, snapshot = await setup_names(hass, monkeypatch)
    network, providers = network_fixture(count), {}
    registry = device_registry.async_get(hass)
    for i, client in enumerate(network["clients"].values()):
        sid, mac, name = f"client{i}", f"02:00:00:00:00:{i+1:02x}", f"Example phone {i}"
        client.update(name=OLD, google_name=OLD, mac_address=mac)
        if i == 0:
            registry.async_update_device(device.id, name_by_user=name)
        else:
            registry.async_get_or_create(config_entry_id=device.config_entry_id, identifiers={("mqtt", sid)},
                connections={(device_registry.CONNECTION_NETWORK_MAC, mac)}, name=name)
        providers[sid] = {"name": OLD, "raw_name": OLD, "automatic_name": OLD, "mac": mac}
    snapshot["networks"]["home"] = network
    await entry.runtime_data.async_refresh()
    identity.side_effect = lambda nid, sid: dict(providers[sid])

    def delivered(nid, sid, name):
        providers[sid].update(name=name, raw_name=name)
        snapshot["networks"][nid]["clients"][sid]["google_name"] = name
        return {}

    writer.side_effect = delivered

    async def rename(i):
        return await entry.runtime_data.names.async_rename("home", f"client{i}", OLD, f"02:00:00:00:00:{i+1:02x}", f"Example phone {i}")

    return entry, identity, writer, delivered, rename


async def test_three_clients_overlap_with_durable_intents_and_network_action_fairness(real_hass, monkeypatch):
    entry, _, writer, delivered, rename = await setup_clients(real_hass, monkeypatch)
    names, client = entry.runtime_data.names, entry.runtime_data.client
    started, release, action_entered, action_release = (asyncio.Event() for _ in range(4))
    active = peak = 0
    sent = []

    async def write(nid, sid, name):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        sent.append(sid)
        record = next(r for r in names.network(nid)["history"] if r["station_id"] == sid)
        assert record["state"] == "unconfirmed"
        saved = Path(real_hass.config.path(".storage", f"google_wifi_insights.{entry.entry_id}.names")).read_text(encoding="utf-8")
        assert record["request_id"] in saved
        if len(sent) == 3:
            started.set()
        await release.wait()
        active -= 1
        return delivered(nid, sid, name)

    async def other_action():
        async with client._action_lock:
            assert names._active == 0
            action_entered.set()
            await action_release.wait()

    writer.side_effect = write
    tasks = [asyncio.create_task(rename(i)) for i in range(7)]
    await asyncio.wait_for(started.wait(), 5)
    assert len(sent) == peak == 3 and names.busy
    action = asyncio.create_task(other_action())
    await asyncio.sleep(0)
    release.set()
    await asyncio.wait_for(action_entered.wait(), 5)
    assert len(sent) == 3, "A queued network action runs before the next naming group"
    action_release.set()
    results = await asyncio.wait_for(asyncio.gather(*tasks, action), 5)
    assert all(r["state"] == "verified" for r in results[:-1])
    assert len(set(sent)) == len(sent) == 7 and peak == 3
    assert not names.busy and names._active == 0 and not client._action_lock.locked()
    assert names.summary("home")["verified_count"] == 7
    assert names.response("home")["max_concurrent"] == 3
    assert names.response("other")["history"] == []
    assert names.summary("home")["enabled"] is False
    assert await real_hass.config_entries.async_unload(entry.entry_id)


async def test_cancelled_parallel_requests_release_all_locks_and_preserve_uncertain_intents(real_hass, monkeypatch):
    from custom_components.google_wifi_insights.naming import NameSync

    entry, _, writer, delivered, rename = await setup_clients(real_hass, monkeypatch, 4)
    started, stalled = asyncio.Event(), asyncio.Event()
    count = 0

    async def write(*args):
        nonlocal count
        count += 1
        if count == 3:
            started.set()
        await stalled.wait()

    writer.side_effect = write
    tasks = [asyncio.create_task(rename(i)) for i in range(4)]
    await asyncio.wait_for(started.wait(), 5)
    for task in tasks:
        task.cancel()
    results = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), 5)
    assert all(isinstance(r, asyncio.CancelledError) for r in results)
    names = entry.runtime_data.names
    assert count == 3 and not names.busy and not entry.runtime_data.client._action_lock.locked()
    restored = NameSync(entry.runtime_data)
    await restored.async_load()
    assert restored.summary("home")["unconfirmed_count"] == 3
    assert restored.summary("home")["paused_reason"] == "previous_write_unconfirmed"
    writer.side_effect = delivered
    assert (await asyncio.wait_for(rename(3), 5))["state"] == "verified"
    assert writer.call_count == 4
    assert await real_hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize("failure", ["rejected", "rate_limit"])
async def test_peer_failure_prevents_writes_still_in_identity_checks(real_hass, monkeypatch, failure):
    from custom_components.google_wifi_insights.api import ApiError, RateLimitError

    entry, identity, writer, _, rename = await setup_clients(real_hass, monkeypatch, 3)
    all_started, failed = asyncio.Event(), asyncio.Event()
    original = identity.side_effect
    checked = 0

    async def fresh(nid, sid):
        nonlocal checked
        checked += 1
        if checked == 3:
            all_started.set()
        await all_started.wait()
        if sid != "client0":
            await failed.wait()
        return original(nid, sid)

    async def write(*args):
        failed.set()
        raise RateLimitError(300) if failure == "rate_limit" else ApiError("Fixture rejection", 400)

    identity.side_effect, writer.side_effect = fresh, write
    results = await asyncio.wait_for(asyncio.gather(*(rename(i) for i in range(3)), return_exceptions=True), 5)
    assert results[0]["state"] == ("unconfirmed" if failure == "rate_limit" else "rejected")
    assert all(isinstance(r, HomeAssistantError) for r in results[1:])
    assert writer.call_count == 1
    assert not entry.runtime_data.names.busy and not entry.runtime_data.client._action_lock.locked()
    if failure == "rate_limit":
        assert entry.runtime_data.client._retry_until > time.monotonic() + 290
    assert await real_hass.config_entries.async_unload(entry.entry_id)


async def test_cancelled_group_waiter_does_not_leak_the_shared_action_lock(real_hass, monkeypatch):
    entry, _, writer, _, rename = await setup_clients(real_hass, monkeypatch, 1)
    client = entry.runtime_data.client
    await client._action_lock.acquire()
    task = asyncio.create_task(rename(0))
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not entry.runtime_data.names.busy and client._action_lock.locked()
    writer.assert_not_awaited()
    client._action_lock.release()
    assert (await asyncio.wait_for(rename(0), 5))["state"] == "verified"
    assert await real_hass.config_entries.async_unload(entry.entry_id)


async def test_rate_limit_after_auth_wait_prevents_transport_call(monkeypatch):
    from gwi_test import api

    client = api.CloudClient(None, None, "test@example.invalid", "dummy", "0" * 16)

    async def authenticated():
        client._retry_until = time.monotonic() + 300

    client._authenticate = authenticated
    request = AsyncMock()
    monkeypatch.setattr(api, "json_request", request)
    with pytest.raises(api.RateLimitError):
        await client._request("PUT", "groups/home/stations/client/stationName", {"name": "Example"}, retry_auth=False)
    request.assert_not_awaited()


async def test_read_only_verification_also_applies_shared_rate_limit(real_hass, monkeypatch):
    from custom_components.google_wifi_insights.api import RateLimitError

    entry, identity, writer, _, rename = await setup_clients(real_hass, monkeypatch, 1)
    result = await rename(0)
    identity.side_effect = RateLimitError(300)
    with pytest.raises(HomeAssistantError, match="read-back is unavailable"):
        await entry.runtime_data.names.async_verify("home", result["request_id"])
    assert writer.call_count == 1
    assert entry.runtime_data.client._retry_until > time.monotonic() + 290
    assert not entry.runtime_data.names.busy and not entry.runtime_data.client._action_lock.locked()
    assert await real_hass.config_entries.async_unload(entry.entry_id)
