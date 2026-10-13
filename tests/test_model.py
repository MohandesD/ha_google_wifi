"""No false saturation, phantom clients, fabricated signal or stale bindings."""

import copy

import pytest
from gwi_test.model import apply_roaming, cloud_network, local_point, parse_points


def network(stations, metrics=None):
    group = {
        "id": "home",
        "accessPoints": [
            {
                "id": "ap1",
                "accessPointSettings": {
                    "accessPointOtherSettings": {"roomData": {"name": "Sala"}}
                },
            },
            {
                "id": "ap2",
                "accessPointSettings": {
                    "accessPointOtherSettings": {"apName": "Escritorio"}
                },
            },
        ],
    }
    status = {
        "apStatuses": [
            {"apId": "ap1", "apState": "AP_ONLINE"},
            {"apId": "ap2", "apState": "AP_ONLINE"},
        ]
    }
    return cloud_network(group, status, stations, metrics or {})


def test_synthetic_lan_status_fixture():
    value = local_point(
        {"host": "192.168.50.1", "name": "Sala"},
        {"wan": {"online": True}, "software": {"softwareVersion": "1.2.3"}},
    )
    assert value["online"] is True
    assert value["firmware"] == "1.2.3"
    assert value["clients"] is None


@pytest.mark.parametrize(
    "text",
    [
        "Sala=127.0.0.1",
        "https://example.com",
        "192.168.50.1:80",
        "8.8.8.8",
        "0.0.0.0",
        "192.168.50.1\n192.168.50.1",
        "",
    ],
)
def test_only_unique_private_points(text):
    with pytest.raises(ValueError):
        parse_points(text)


def test_parse_named_points():
    assert parse_points("Sala=192.168.50.1\nQuarto=192.168.50.133")[1] == {
        "name": "Quarto",
        "host": "192.168.50.133",
    }


def test_unreachable_is_unknown():
    value = local_point({"host": "192.168.50.133", "name": "Quarto"}, None)
    assert value["online"] is None and value["reachable"] is False


def test_client_count_never_claims_saturation():
    value = network(
        [{"id": str(i), "connected": True, "apId": "ap1"} for i in range(200)]
    )
    assert value["connected_clients"] == 200
    assert value["points"]["ap1"]["clients"] == 200
    assert value["saturation"] is None
    assert value["diagnosis"] == "insufficient_radio_data"
    assert value["weak_clients"] is None


def test_no_stale_ap_or_rssi_when_disconnected():
    value = network([{"id": "phone", "connected": False, "apId": "ap1", "rssi": -82}])
    assert value["clients"]["phone"]["point"] is None
    assert value["clients"]["phone"]["rssi"] is None
    assert value["points"]["ap1"]["clients"] == 0


@pytest.mark.parametrize("rssi", [45, True, -999, "POOR", "NaN", "inf", None])
def test_reject_percentages_and_invalid_signal(rssi):
    value = network([{"id": "phone", "connected": True, "apId": "ap1", "rssi": rssi}])
    assert value["clients"]["phone"]["rssi"] is None


def test_explicit_signal_optional_fixture():
    value = network([{"id": "phone", "connected": True, "apId": "ap1", "rssi": -82}])
    assert value["clients"]["phone"]["signal_quality"] == "weak"
    assert value["weak_clients"] == 1
    assert value["diagnosis"] == "weak_signal_detected"
    assert value["saturation"] is None


def test_missing_connection_does_not_become_offline_or_zero():
    value = network([{"id": "phone", "apId": "ap1"}])
    assert value["connected_clients"] is None
    assert value["clients"]["phone"]["connected"] is None
    assert value["unknown_connection_clients"] == 1


def test_unknown_binding_does_not_guess_from_ip():
    value = network(
        [
            {
                "id": "phone",
                "connected": True,
                "apId": "unknown",
                "ipAddress": "192.168.50.40",
            }
        ]
    )
    assert value["clients"]["phone"]["point"] is None
    assert value["unassigned_clients"] == 1


def test_unknown_radio_does_not_turn_zero_weak_into_good():
    value = network(
        [
            {"id": "one", "connected": True, "apId": "ap1", "rssi": -50},
            {"id": "two", "connected": True, "apId": "ap1"},
        ]
    )
    assert value["clients_with_signal"] == 1
    assert value["weak_clients"] is None
    assert value["points"]["ap1"]["weak_clients"] is None
    assert value["diagnosis"] == "quality_data_available"
    assert value["clients"]["two"]["signal_quality"] is None
    assert value["saturation"] is None


def test_traffic_is_not_link_speed():
    value = network(
        [{"id": "phone", "connected": True, "apId": "ap1"}],
        {
            "groupTraffic": {"receiveSpeedBps": "25000000", "transmitSpeedBps": 0},
            "stationMetrics": [
                {"station": {"id": "phone", "connected": True, "apId": "ap1"}, "traffic": {"receiveSpeedBps": "5000000"}}
            ],
        },
    )
    assert value["download_mbps"] == 25
    assert value["upload_mbps"] == 0
    assert value["clients"]["phone"]["download_mbps"] == 5
    assert value["clients"]["phone"]["upload_mbps"] == 0


def test_current_empty_traffic_is_zero_but_missing_or_stale_message_unknown():
    station = {"id": "one", "connected": True, "apId": "ap1", "ipAddress": "192.168.50.4", "ipAddresses": ["192.168.50.4", "fe80::1234"]}
    metric = {"station": station, "traffic": {}}
    value = network([station], {"stationMetrics": [metric]})["clients"]["one"]
    assert value["download_mbps"] == 0 and value["upload_mbps"] == 0
    assert value["ip_addresses"] == ["192.168.50.4", "fe80::1234"]
    assert value["mac_address"] is None
    assert network([station])["clients"]["one"]["download_mbps"] is None
    metric["station"] = {**station, "apId": "ap2"}
    assert network([station], {"stationMetrics": [metric]})["clients"]["one"]["download_mbps"] is None


def test_roaming_only_between_connected_samples():
    old = {
        "networks": {
            "home": network([{"id": "phone", "connected": True, "apId": "ap1"}])
        }
    }
    new = {
        "networks": {
            "home": network([{"id": "phone", "connected": True, "apId": "ap2"}])
        }
    }
    result = apply_roaming(new, old)
    assert result["networks"]["home"]["clients"]["phone"]["roams_since_start"] == 1
    assert result["networks"]["home"]["clients"]["phone"]["last_roam"]
    disconnected = copy.deepcopy(old)
    disconnected["networks"]["home"]["clients"]["phone"]["connected"] = False
    result = apply_roaming(new, disconnected)
    assert result["networks"]["home"]["clients"]["phone"]["roams_since_start"] == 0


def test_observed_google_connection_rating_is_not_rssi_or_throughput():
    value = network(
        [{"id": "phone", "connected": True, "apId": "ap1", "wirelessBand": "BAND_2400_MHZ"}],
        {"stationMetrics": [{
            "station": {"id": "phone", "connected": True, "apId": "ap1"},
            "speed": {"speedRating": "WEAK", "numericSpeedRating": "19"},
            "traffic": {"receiveSpeedBps": "2000000"},
        }]},
    )
    client = value["clients"]["phone"]
    assert client["signal_quality"] == "weak"
    assert client["quality_source"] == "google_connection_rating"
    assert client["google_rating_index"] == 19
    assert client["rssi"] is None
    assert client["download_mbps"] == 2
    assert client["wireless_band"] == "BAND_2400_MHZ"
    assert value["weak_clients"] == 1 and value["clients_with_quality"] == 1
    assert value["saturation"] is None


@pytest.mark.parametrize("live", [
    {"id": "phone", "connected": True, "apId": "ap2"},
    {"id": "phone", "connected": False, "apId": "ap1"},
    {"id": "phone", "apId": "ap1"},
])
def test_roamed_or_disconnected_metrics_do_not_supply_stale_quality(live):
    value = network(
        [{"id": "phone", "connected": True, "apId": "ap1"}],
        {"stationMetrics": [{"station": live, "speed": {"speedRating": "GREAT"}}]},
    )
    assert value["clients"]["phone"]["signal_quality"] is None


def test_mesh_rating_uses_explicit_ap_and_root_even_without_rssi():
    group = {"accessPoints": [
        {"id": "root", "accessPointProperties": {"isGroupRoot": True, "firmwareVersion": "test"}},
        {"id": "leaf"}, {"id": "offline"},
    ]}
    status = {"apStatuses": [
        {"apId": "root", "apState": "AP_ONLINE"},
        {"apId": "leaf", "apState": "AP_ONLINE"},
        {"apId": "offline", "apState": "AP_OFFLINE"},
    ]}
    metrics = {"meshMetrics": [
        {"apId": "leaf", "speed": {"speedRating": "OK", "numericSpeedRating": "50"}},
        {"apId": "offline", "speed": {"speedRating": "GREAT"}},
        {"apId": "unknown", "speed": {"speedRating": "WEAK"}},
    ]}
    points = cloud_network(group, status, [], metrics)["points"]
    assert points["root"]["is_root"] is True and points["root"]["mesh_quality"] is None
    assert points["leaf"]["is_root"] is False and points["leaf"]["root_ap_id"] == "root"
    assert points["leaf"]["mesh_quality"] == "fair"
    assert points["leaf"]["mesh_quality_source"] == "google_mesh_rating"
    assert points["offline"]["mesh_quality"] is None
    assert "unknown" not in points


@pytest.mark.parametrize("speed", [{}, {"speedRating":"UNKNOWN"}, {"speedRating":[]}, None])
def test_unrecognized_google_quality_is_unknown(speed):
    value = network(
        [{"id":"phone","connected":True,"apId":"ap1"}],
        {"stationMetrics":[{"station":{"id":"phone","connected":True,"apId":"ap1"},"speed":speed}]},
    )
    assert value["clients"]["phone"]["signal_quality"] is None


def test_good_rating_does_not_claim_good_radio_saturation():
    value = network(
        [{"id":"phone","connected":True,"apId":"ap1"}],
        {"stationMetrics":[{"station":{"id":"phone","connected":True,"apId":"ap1"},"speed":{"speedRating":"GREAT"}}]},
    )
    assert value["diagnosis"] == "quality_data_available"
    assert value["saturation"] is None and value["clients_with_signal"] == 0
