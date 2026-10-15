"""Telemetry exposes known readings without exporting group credentials."""
from gwi_test.model import cloud_network


def test_metrics_include_historical_wan_results_and_omit_secrets():
    station = {"id": "s", "connected": True, "apId": "ap", "wirelessCap": "VHT", "numberOfRxSpatialStream": 2, "lastSeen": "2026-10-11T12:00:00Z", "status": {"type": "NORMAL"}}
    group = {"accessPoints": [{"id": "ap", "accessPointProperties": {"hardwareType": "AC-1304", "localAuthorizationToken": "private-ap-token", "lastSeenTime": "2026-10-11T12:00:00Z"}}], "groupSettings": {"meshSettings": {"kek": "private-kek"}, "wlanSettings": {"privateSsid": "private-ssid"}}, "managers": [{"emailAddress": "private-email"}]}
    network = cloud_network(group, {"wanConnectionStatus": "ONLINE"}, [station], {"stationMetrics": [{"station": station, "traffic": {}, "speed": {"speedRating": "OK", "numericSpeedRating": "50"}}]}, speed_tests={"speedTestResults": [{"timestamp": "2026-10-10T12:00:00Z", "receiveWanSpeedBps": "10"}, {"timestamp": "2026-10-11T12:00:00Z", "receiveWanSpeedBps": "885929256", "transmitWanSpeedBps": "386599232"}]})
    assert network["wan_test_download_mbps"] == 885.929256
    assert network["wan_test_upload_mbps"] == 386.599232
    assert network["clients"]["s"]["rx_spatial_streams"] == 2
    assert network["clients"]["s"]["google_telemetry"]["connectionRating"]["numericSpeedRating"] == "50"
    assert network["points"]["ap"]["hardware_type"] == "AC-1304"
    assert "private-" not in str(network)


def test_stale_association_does_not_export_current_quality_or_traffic():
    network = cloud_network({"accessPoints": [{"id": "ap"}]}, {}, [{"id": "s", "connected": True, "apId": "ap"}], {"stationMetrics": [{"station": {"id": "s", "apId": "old", "connected": True}, "traffic": {"receiveSpeedBps": "10000"}, "speed": {"speedRating": "GREAT"}}]})
    telemetry = network["clients"]["s"]["google_telemetry"]
    assert "connectionRating" not in telemetry and "traffic" not in telemetry
    assert network["wan_test_download_mbps"] is None


def test_local_status_does_not_leak_to_old_network_or_ambiguous_points():
    from types import SimpleNamespace

    from gwi_test.coordinator import WifiCoordinator
    from gwi_test.model import local_point
    local = object.__new__(WifiCoordinator)
    local.last_update_success = True
    local.data = {"networks": {"local": {"points": {"root": local_point({"host": "192.168.50.1", "name": "Root"}, {"system": {"groupRole": "root", "uptime": 100}, "wan": {"online": True}})}}}}
    local_entry = SimpleNamespace(data={"mode": "local"}, options={}, runtime_data=local)
    cloud = object.__new__(WifiCoordinator)
    cloud.config_entry = SimpleNamespace(data={"mode": "cloud"})
    cloud.hass = SimpleNamespace(config_entries=SimpleNamespace(async_entries=lambda domain: [local_entry]))
    def point(online):
        return {"is_root": True, "online": online, "host": "192.168.50.1", "uptime_seconds": None, "google_telemetry": {}}
    snapshot = {"networks": {"current": {"points": {"p": point(True)}}, "old": {"points": {"p": point(False)}}}}
    cloud._merge_local_points(snapshot)
    assert snapshot["networks"]["current"]["points"]["p"]["uptime_seconds"] == 100
    assert snapshot["networks"]["old"]["points"]["p"]["uptime_seconds"] is None
    snapshot = {"networks": {"current": {"points": {"p": point(True)}}, "ambiguous": {"points": {"p": point(True)}}}}
    cloud._merge_local_points(snapshot)
    assert all(n["points"]["p"]["uptime_seconds"] is None for n in snapshot["networks"].values())
