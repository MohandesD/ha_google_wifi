"""Measure synthetic entity scaling without a Google account or LAN devices."""

import json
import time
import tracemalloc

import pytest
from homeassistant.helpers import entity_registry
from test_ha import real_hass as real_hass
from test_stabilization_ha import network_fixture, setup_fixture


@pytest.mark.parametrize("clients", [100, 300])
async def test_many_clients_keep_optional_diagnostics_disabled_and_updates_local(real_hass, monkeypatch, tmp_path, clients):
    network = network_fixture(clients)
    snapshot = {"networks": {"home": network}}
    start, cpu = time.perf_counter(), time.process_time()
    tracemalloc.start()
    try:
        entry = await setup_fixture(real_hass, monkeypatch, snapshot)
        setup_seconds = time.perf_counter() - start
        registry = entity_registry.async_get(real_hass)
        registered = entity_registry.async_entries_for_config_entry(registry, entry.entry_id)
        optional = [row for row in registered if row.translation_key in {
            "google_telemetry_at", "wireless_standard", "rx_spatial_streams",
        } and ":client:" in row.unique_id]
        assert len(optional) == 3 * clients
        assert all(row.disabled_by == entity_registry.RegistryEntryDisabler.INTEGRATION for row in optional)
        states = real_hass.states.async_all()
        carriers = [row for row in states if row.attributes.get("gwi_kind") == "client" and row.attributes.get("gwi_metric") == "point"]
        assert len(carriers) == clients
        assert all(row.state != "unavailable" for row in carriers)
        state_bytes = len(json.dumps([row.as_dict() for row in states], default=str).encode())
        previous = {row.entity_id: row.last_updated for row in states}
        snapshot["networks"]["home"]["clients"]["client0"]["download_mbps"] = 1.25
        refresh_start = time.perf_counter()
        await entry.runtime_data.async_refresh()
        await real_hass.async_block_till_done()
        refresh_seconds = time.perf_counter() - refresh_start
        changed = [row for row in real_hass.states.async_all() if previous.get(row.entity_id) != row.last_updated]
        assert changed
        assert all(row.attributes.get("gwi_item_id") == "client0" for row in changed)
        _, peak = tracemalloc.get_traced_memory()
        metrics = {
            "clients": clients, "registered_entities": len(registered), "reported_ha_states": len(states),
            "optional_client_diagnostics_disabled": len(optional), "state_json_bytes": state_bytes,
            "setup_seconds": round(setup_seconds, 4), "refresh_seconds": round(refresh_seconds, 4),
            "process_cpu_seconds": round(time.process_time() - cpu, 4), "python_peak_bytes": peak,
            "entities_changed_for_one_client_traffic_update": len(changed),
            "synthetic": True, "live_network_requests": 0, "recorder_database_growth_measured": False,
        }
        (tmp_path / "scale-metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    finally:
        tracemalloc.stop()
    assert await real_hass.config_entries.async_unload(entry.entry_id)
