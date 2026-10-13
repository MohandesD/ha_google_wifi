"""Exercise real collection boundaries, failure freshness and safe information."""
from unittest.mock import AsyncMock
import copy

import pytest
from gwi_test.api import ApiError, CloudClient
from gwi_test.information import apply_point_information, apply_network_information, clean, firmware_notes
from gwi_test.lan import LanDiagnostics, private_host


def status(host="10.7.0.1", role="root"):
    return {"system": {"groupRole": role, "lan0Link": False, "uptime": 100},
            "software": {"softwareVersion": "14000.1.2", "updateRequired": False, "updateStatus": "idle", "updateProgress": 0.25},
            "wan": {"localIpAddress": host, "online": True, "ethernetLink": False, "leaseDurationSeconds": 86400}}


def test_notes_are_versioned_text_and_historical_versions_do_not_claim_an_update():
    notes = firmware_notes({"releaseNotes": [{"apVersion": "13000.1.0", "card": {"title": "Old notes", "descriptionHtml": "<p>Fixes<br>WiFi</p><script>do-not-display</script>"}}]},
                           "14000.1.2", {"state": "available", "stale": False})
    assert notes["matching_installed"] is False
    assert notes["notes"][0]["version"] == "13000.1.0"
    assert notes["notes"][0]["description"] == "Fixes\nWiFi"
    assert "<script" not in str(notes) and "do-not-display" not in str(notes)
    assert clean({"newReading": 0, "password": "private", "setupCode": "private", "qrCode": "private", "nested": {"username": "private"}}) == {"newReading": 0, "nested": {}}


def test_missing_and_stale_lan_values_never_become_false_update_flags_or_fresh_progress():
    point = {"firmware": "14000.1.2", "lan_information": {"status": status(), "stale": False, "retrieved_at": "2026-10-13T12:00:00Z"}}
    apply_point_information(point)
    assert point["update_required"] is False and point["update_progress_raw"] == 0.25
    assert point["ethernet_link"] is False and point["wan_lease_seconds"] == 86400
    point["lan_information"]["stale"] = True
    apply_point_information(point)
    assert point["update_required"] is None and point["update_progress_raw"] is None
    assert point["ethernet_link"] is None and point["lan_status"] == "stale"
    empty = {}
    apply_point_information(empty)
    assert empty["update_required"] is None and empty["lan_status"] == "not_configured"


def test_complete_network_information_keeps_new_noncredential_fields_and_false_flags():
    network = {"source": "google_cloud", "points": {}, "google_telemetry": {
        "groupSettings": {"lanSettings": {"ipAddress": "10.7.0.1", "dhcpPoolBegin": "10.7.0.5", "upnpEnabled": False},
                          "wanSettings": {"ipv6Enabled": False}, "guestWirelessSettings": {"enabled": True, "psk": "private"},
                          "futureNetworkSetting": {"measured": 12, "password": "private"}},
        "groupProperties": {"wanProperties": {"ipAddress": "198.51.100.1", "wanMode": "STATIC"}}}}
    apply_network_information(network)
    assert network["ipv6_enabled"] is False and network["upnp_enabled"] is False
    assert network["network_information"]["cloud"]["remaining_settings"]["futureNetworkSetting"] == {"measured": 12}
    assert "private" not in str(network["network_information"])


@pytest.mark.parametrize("host", ["127.0.0.1", "169.254.169.254", "8.8.8.8", "0.0.0.0", "http://10.7.0.1", "localhost", True, 1])
def test_lan_targets_reject_nonprivate_or_nonliteral_addresses(host):
    assert private_host(host) is None


@pytest.mark.asyncio
async def test_lan_reads_are_cached_gets_and_keep_unsupported_endpoint_status(monkeypatch):
    calls = []

    async def read(session, url, headers=None):
        calls.append(url)
        if url.endswith("/status"):
            return status()
        if url.endswith("/developer-configuration"):
            return {"apiEnvironment": "production", "apiToken": "private"}
        raise ApiError("unsupported", 404)

    monkeypatch.setattr("gwi_test.lan.json_get", read)
    collector = LanDiagnostics(None)
    point = await collector.point("10.7.0.1", "root")
    assert point["developer_configuration"] == {"apiEnvironment": "production"}
    assert point["endpoints"]["welcome_mat"]["state"] == "not_supported"
    assert point["endpoints"]["welcome_mat"]["http_status"] == 404
    assert await collector.point("10.7.0.1", "root") == point
    assert len(calls) == 4
    collector.next_read[("10.7.0.1", "status")] = 0
    monkeypatch.setattr("gwi_test.lan.json_get", AsyncMock(side_effect=ApiError("offline")))
    failed = await collector.point("10.7.0.1", "root")
    assert failed["stale"] and failed["status"] == {}
    assert collector.cache[("10.7.0.1", "status")]["payload"]["software"]["updateRequired"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize("expected_role", ["root", "leaf"])
async def test_lan_role_and_ip_mismatches_do_not_get_extra_endpoint_reads(monkeypatch, expected_role):
    read = AsyncMock(return_value=status("10.7.0.2", "leaf"))
    monkeypatch.setattr("gwi_test.lan.json_get", read)
    point = await LanDiagnostics(None).point("10.7.0.1", expected_role)
    assert point["stale"] and point["status"] == {} and read.call_count == 1


@pytest.mark.asyncio
async def test_primary_wan_in_an_upstream_subnet_keeps_its_lan_diagnostics(monkeypatch):
    async def read(session, url, headers=None):
        return status("172.20.0.2", "root") if url.endswith("/status") else {"enabled": False}

    requests = AsyncMock(side_effect=read)
    monkeypatch.setattr("gwi_test.lan.json_get", requests)
    point = await LanDiagnostics(None).point("10.7.0.1", "root")
    assert point["stale"] is False and requests.call_count == 4
    assert point["status"]["wan"]["localIpAddress"] == "172.20.0.2"
    assert point["status"]["software"]["updateRequired"] is False


def network(host="10.7.0.1"):
    return {"points": {"root": {"host": host, "is_root": True, "online": True},
                       "leaf": {"host": "10.7.0.2", "is_root": False, "online": True}},
            "google_telemetry": {"groupSettings": {"lanSettings": {"netmask": "255.255.255.0"}}}}


@pytest.mark.asyncio
async def test_cloud_lan_collection_requires_an_explicit_anchor_and_rejects_ambiguous_networks():
    collector = LanDiagnostics(None)
    collector.point = AsyncMock(return_value={"stale": False})
    snapshot = {"networks": {"first": network()}}
    await collector.enrich_cloud(snapshot, set())
    collector.point.assert_not_awaited()
    await collector.enrich_cloud(snapshot, set(), "10.7.0.1")
    assert collector.point.call_count == 2
    collector.point.reset_mock()
    await collector.enrich_cloud({"networks": {"first": network(), "second": network()}}, {"10.7.0.1", "10.7.0.2"})
    collector.point.assert_not_awaited()


@pytest.mark.asyncio
async def test_extra_cloud_reads_share_account_and_version_caches_and_never_start_tests():
    client = CloudClient(None, None, "dummy@example.invalid", "dummy", "0"*16)
    groups = [{"id": "first", "accessPoints": [{"id": "p", "accessPointProperties": {"firmwareVersion": "14000.1.2"}}]},
              {"id": "second", "accessPoints": [{"id": "q", "accessPointProperties": {"firmwareVersion": "14000.1.2"}}]}]
    calls = []

    async def read(path):
        calls.append(path)
        if path == "groups?prettyPrint=false":
            return {"groups": copy.deepcopy(groups)}
        if "/stations?" in path:
            return {"stations": []}
        if "/releaseNotes?" in path:
            return {"releaseNotes": [{"apVersion": "13000.1.0", "card": {"description": "Older release"}}]}
        if path.startswith("userPreferences?"):
            return {"optInFlow": "COMPLETE"}
        return {}

    client._get = AsyncMock(side_effect=read)
    client._station_macs = AsyncMock(return_value={})
    result = await client.snapshot()
    assert sum(p.startswith("userPreferences?") for p in calls) == 1
    assert len([p for p in calls if "/hardwareBundleSetupInfo?" in p]) == 2
    assert result["networks"]["first"]["points"]["p"]["firmware_notes"]["matching_installed"] is False
    assert result["networks"]["second"]["google_telemetry"]["accountPreferences"] == {"optInFlow": "COMPLETE"}
    assert len([p for p in calls if "/releaseNotes?" in p]) == 1
    before = len([p for p in calls if "/releaseNotes?" in p])
    await client.snapshot()
    assert len([p for p in calls if "/releaseNotes?" in p]) == before
    assert not any("SpeedTest?" in p or "/reboot?" in p for p in calls)
