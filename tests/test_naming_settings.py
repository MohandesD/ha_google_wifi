"""Configurable limits preserve durable intent, group draining and admin scope."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from homeassistant.core import Context
from homeassistant.exceptions import HomeAssistantError
from test_ha import real_hass as real_hass
from test_management import call, carrier
from test_naming import setup_names
from test_naming_concurrency import setup_clients


@pytest.mark.parametrize("initial,next_limit", [(1, 5), (5, 1), (10, 3)])
async def test_changed_limits_drain_the_admitted_group_before_using_the_new_limit(real_hass, monkeypatch, initial, next_limit):
    from custom_components.google_wifi_insights.naming import NameSync

    entry, _, writer, delivered, rename = await setup_clients(real_hass, monkeypatch, 12)
    names = entry.runtime_data.names
    await names.async_set_concurrency("home", initial)
    reached, release, next_reached = (asyncio.Event() for _ in range(3))
    next_size = min(next_limit, 12 - initial)
    active = sent = later_peak = 0

    async def write(nid, sid, name):
        nonlocal active, sent, later_peak
        sent += 1
        position = sent
        active += 1
        if position <= initial:
            if position == initial:
                reached.set()
            await release.wait()
        else:
            later_peak = max(later_peak, active)
            if position <= initial + next_size:
                if position == initial + next_size:
                    next_reached.set()
                await next_reached.wait()
            else:
                await asyncio.sleep(0)
        active -= 1
        return delivered(nid, sid, name)

    writer.side_effect = write
    tasks = [asyncio.create_task(rename(i)) for i in range(12)]
    await asyncio.wait_for(reached.wait(), 5)
    assert active == sent == initial
    await names.async_set_concurrency("home", next_limit)
    assert active == sent == initial, "Changing policy never cancels or expands the active group"
    assert names.response("home")["max_concurrent"] == next_limit
    assert names.response("other")["max_concurrent"] == 3
    release.set()
    results = await asyncio.wait_for(asyncio.gather(*tasks), 10)
    assert all(r["state"] == "verified" for r in results)
    assert later_peak == min(next_limit, 12 - initial)
    assert not names.busy and not entry.runtime_data.client._action_lock.locked()
    restored = NameSync(entry.runtime_data)
    await restored.async_load()
    assert restored.concurrency("home") == next_limit
    assert restored.summary("home")["enabled"] is False
    assert await real_hass.config_entries.async_unload(entry.entry_id)


async def test_concurrency_service_is_local_scoped_admin_only_and_transactional(real_hass, monkeypatch):
    entry, _, _, writer, _, _ = await setup_names(real_hass, monkeypatch)
    entity = carrier(real_hass, "network", "diagnosis").entity_id
    real_hass.auth = SimpleNamespace(async_get_user=AsyncMock(return_value=SimpleNamespace(is_admin=False)))
    with pytest.raises(HomeAssistantError, match="administrator"):
        await call(real_hass, "set_name_concurrency", {"entity_id": entity, "max_concurrent": 5}, Context(user_id="not-admin"))
    with pytest.raises(HomeAssistantError, match="network entity"):
        await call(real_hass, "set_name_concurrency", {"entity_id": carrier(real_hass, "client", "point").entity_id, "max_concurrent": 5})
    response = await call(real_hass, "set_name_concurrency", {"entity_id": entity, "max_concurrent": 5})
    assert response["rename"]["max_concurrent"] == 5
    assert response["rename"]["concurrency_configurable"] is True
    assert entry.runtime_data.names.response("other")["max_concurrent"] == 3
    assert entry.runtime_data.names.summary("home")["enabled"] is False
    writer.assert_not_awaited()
    monkeypatch.setattr(entry.runtime_data.names._store, "async_save", AsyncMock(side_effect=OSError("Fixture storage unavailable")))
    with pytest.raises(OSError):
        await entry.runtime_data.names.async_set_concurrency("home", 8)
    assert entry.runtime_data.names.concurrency("home") == 5
    assert await real_hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize("invalid", [True, False, 0, 11, -1, 3.5, "5", None])
async def test_concurrency_service_rejects_invalid_values_without_writing(real_hass, monkeypatch, invalid):
    import voluptuous as vol

    entry, _, _, writer, _, _ = await setup_names(real_hass, monkeypatch)
    with pytest.raises(vol.Invalid):
        await call(real_hass, "set_name_concurrency", {"entity_id": carrier(real_hass, "network", "diagnosis").entity_id, "max_concurrent": invalid})
    assert entry.runtime_data.names.concurrency("home") == 3
    writer.assert_not_awaited()
    assert await real_hass.config_entries.async_unload(entry.entry_id)


async def test_invalid_persisted_limits_never_expand_the_cap(real_hass, monkeypatch):
    from custom_components.google_wifi_insights.naming import NameSync

    entry, _, _, writer, _, _ = await setup_names(real_hass, monkeypatch)
    restored = NameSync(entry.runtime_data)
    for invalid in [True, False, 0, 100, -1, 2.5, "10", None]:
        monkeypatch.setattr(restored._store, "async_load", AsyncMock(return_value={"home": {"max_concurrent": invalid}}))
        restored._loaded = False
        await restored.async_load()
        assert restored.concurrency("home") == 3
    writer.assert_not_awaited()
    assert await real_hass.config_entries.async_unload(entry.entry_id)
