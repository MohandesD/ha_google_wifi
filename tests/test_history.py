from datetime import UTC, datetime
from urllib.parse import parse_qs
from gwi_test.history import request_window, normalize_history, summarize, apply_history
from gwi_test.capabilities import apply_extras, safe_metadata
from gwi_test.model import cloud_network


def test_usage_query_explicit_utc_range_resolution_and_end_timestamp_semantics():
    period, query = request_window("hour", datetime(2026, 10, 13, 12, 0, 59, tzinfo=UTC))
    assert parse_qs(query)["granularity"] == ["3600"]
    assert period["end"] == "2026-10-13T12:00:00+00:00"
    assert period["start"] == "2026-10-12T12:00:00+00:00"
    payload = {"wanUsageRecords": [{"timestamp": "2026-10-12T13:00:00Z", "bytesReceived": "9007199254740993", "bytesTransmitted": "123"},
                                  {"timestamp": "2026-10-12T12:00:00Z", "bytesReceived": "888"},
                                  {"timestamp": "2026-10-13T13:00:00Z", "bytesReceived": "999"}]}
    data = normalize_history(payload, period)
    assert data["wan"] == [{"start": period["start"], "end": "2026-10-12T13:00:00+00:00", "download_bytes": 9007199254740993, "upload_bytes": 123}]
    assert summarize(data["wan"], period)["complete"] is False
    network = {"clients": {"not_returned": {}}}
    apply_history(network, {"hour": data})
    assert network["usage_24h_download"] is None
    assert network["usage_windows"]["hour"]["download_bytes"] == 9007199254740993
    assert network["clients"]["not_returned"]["usage_windows"]["hour"]["download_bytes"] is None


def test_usage_deduplicates_drops_conflicts_malformed_and_keeps_explicit_zero():
    period, _ = request_window("minute", datetime(2026, 10, 13, 12, tzinfo=UTC))
    rows = [{"timestamp": "2026-10-13T11:01:00Z"}, {"timestamp": "2026-10-13T11:01:00Z"},
            {"timestamp": "2026-10-13T11:02:00Z", "bytesReceived": "10"},
            {"timestamp": "2026-10-13T11:02:00Z", "bytesReceived": "20"},
            {"timestamp": "2026-10-13T11:03:00Z", "bytesReceived": True},
            {"timestamp": "2026-10-13T11:03:03Z", "bytesReceived": "1"},
            {"timestamp": "2026-10-13T11:04:00Z", "bytesReceived": "-1"}]
    data = normalize_history({"wanUsageRecords": rows, "stationUsageRecords": [{"station": {"id": "client"}, "usageRecords": rows}]}, period)
    assert len(data["wan"]) == 1 and data["wan"][0]["download_bytes"] == 0
    assert data["stations"]["client"] == data["wan"]


def test_stored_tests_are_station_bound_dated_and_not_current_traffic_or_rssi():
    station = {"id": "client", "connected": True, "apId": "now"}
    group = {"accessPoints": [{"id": "now"}, {"id": "then", "accessPointSettings": {"accessPointOtherSettings": {"apName": "Old point"}}}], "groupSettings": {"familyHubSettings": {"stationPolicies": []}, "lanSettings": {"prioritizedStation": {}}}}
    network = cloud_network(group, {}, [station], {})
    extras = {"wifiblasterSpeedTestResults": {"stationResults": [
        {"stationId": "client", "apId": "now", "throughputBps": "999000000", "timestamp": "2025-01-01T00:00:00Z"},
        {"stationId": "client", "apId": "then", "throughputBps": "11024049", "timestamp": "2025-07-26T09:00:00Z"},
        {"stationId": "foreign", "apId": "now", "throughputBps": "900000000", "timestamp": "2026-10-13T00:00:00Z"}]},
        "meshSpeedTestResults": {"speedTestResults": [{"clientApId": "then", "receiveSpeedBps": "100000000", "timestamp": "2026-01-01T00:00:00Z"}]},
        "backhaulOfChildNodes": {"apBackhaul": [{"apId": "then", "backhaul": "MESH_5000MHZ"}]}}
    apply_extras(network, group, extras, {}, {})
    client = network["clients"]["client"]
    assert client["wifi_test_mbps"] == 11.024049 and client["wifi_test_at"].year == 2025
    assert client["wifi_test_ap_id"] == "then" and client["wifi_test_point"] == "Old point"
    assert client["ap_id"] == "now" and client["rssi"] is None and client["download_mbps"] is None
    assert "foreign" not in network["clients"]
    assert network["points"]["then"]["mesh_test_mbps"] == 100
    assert network["points"]["then"]["backhaul_type"] == "MESH_5000MHZ"
    assert client["internet_paused"] is False and client["priority_active"] is False


def test_all_metadata_keeps_new_metrics_but_excludes_secrets_and_opaque_config():
    value = safe_metadata({"newMetric": 42, "mainPsk": "secret", "LocalAuthToken": "secret", "meshConfiguration": "encoded", "nested": {"credential": "x", "value": "aas_et/verysecret"}})
    assert value == {"newMetric": 42, "nested": {"value": "[credential omitted]"}}


def test_present_lighting_message_defaults_zero_but_absent_message_is_unknown():
    network = cloud_network({"accessPoints": [{"id": "p", "accessPointSettings": {"lightingSettings": {"lightOffWhenMuted": False}}}, {"id": "other"}]}, {}, [], {})
    assert network["points"]["p"]["led_brightness"] == 0
    assert network["points"]["other"]["led_brightness"] is None
