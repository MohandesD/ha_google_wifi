"""Explicit allowlists for observed Google telemetry; never export account secrets."""
from __future__ import annotations
from datetime import UTC, datetime
import math


def selected(source, keys):
    if not isinstance(source, dict):
        return {}
    return {key: source[key] for key in keys if key in source
            and isinstance(source[key], (str, int, float, bool, list))}


def timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return result.astimezone(UTC) if result.tzinfo and result.year > 1970 else None
    except ValueError:
        return None


def mbps(value):
    if isinstance(value, bool):
        return None
    try:
        numeric = float(value)
    except ValueError, TypeError, OverflowError:
        return None
    return round(numeric / 1_000_000, 6) if math.isfinite(numeric) and numeric >= 0 else None


SPEED = ("speedRating", "numericSpeedRating", "speedText", "expandedSpeedText")
TRAFFIC = ("receiveSpeedBps", "transmitSpeedBps")
STATION = (
    "id", "friendlyName", "automaticFriendlyName", "dhcpHostname", "curatedOuiName",
    "unfilteredCuratedOuiName", "friendlyType", "unfilteredFriendlyType", "stationType",
    "connected", "apId", "ipAddress", "ipAddresses", "connectionType", "wirelessBand",
    "wirelessCap", "numberOfRxSpatialStream", "lastSeen",
)
AP_PROPERTIES = (
    "firmwareVersion", "hardwareType", "hybridDeviceState", "ipAddress", "isBridged",
    "isGroupRoot", "lastFirmwareVersionChangeTimestamp", "lastSeenTime", "oemName",
    "operatingMode", "serialNumber", "setupCompleted",
)


def extend_network(network, group, status, stations, metrics, speed_tests):
    from .capabilities import safe_metadata
    now = datetime.now(UTC)
    station_metrics = {r.get("station", {}).get("id"): r for r in metrics.get("stationMetrics", []) if isinstance(r, dict)}
    for station in stations:
        client = network["clients"].get(station.get("id"))
        if client is None:
            continue
        telemetry = selected(station, STATION)
        telemetry["status"] = selected(station.get("status"), ("type", "text"))
        live = station_metrics.get(station["id"], {})
        if client.get("connected") is True and live.get("station", {}).get("connected") is True and live["station"].get("apId") == client.get("ap_id"):
            telemetry["connectionRating"] = selected(live.get("speed"), SPEED)
            if isinstance(live.get("traffic"), dict):
                telemetry["traffic"] = selected(live["traffic"], TRAFFIC)
                telemetry["trafficOmittedNumericDefaults"] = 0
        client.update({"google_telemetry": telemetry, "google_telemetry_at": now,
                       "last_seen": timestamp(station.get("lastSeen")),
                       "wireless_standard": station.get("wirelessCap"),
                       "rx_spatial_streams": station.get("numberOfRxSpatialStream")})
        telemetry["fullStationMetadata"] = safe_metadata(station)
        telemetry["fullRealtimeMeasurement"] = safe_metadata(live)
    ap_statuses = {r.get("apId"): r for r in status.get("apStatuses", []) if isinstance(r, dict)}
    meshes = {r.get("apId"): r for r in metrics.get("meshMetrics", []) if isinstance(r, dict)}
    for ap in group.get("accessPoints", []):
        point = network["points"].get(ap.get("id"))
        if point is None:
            continue
        props = ap.get("accessPointProperties") or {}
        settings = ap.get("accessPointSettings") or {}
        telemetry = selected(props, AP_PROPERTIES)
        telemetry["joinMeshResult"] = selected(props.get("joinMeshResult"), ("result",))
        telemetry["status"] = selected(ap_statuses.get(ap["id"]), ("apState",))
        telemetry["lightingSettings"] = selected(settings.get("lightingSettings"), ("intensity",))
        telemetry["pointSettings"] = selected(settings.get("accessPointOtherSettings"), ("apName", "ispType"))
        if point.get("mesh_quality"):
            telemetry["meshRatingToPrimary"] = selected(meshes.get(ap["id"], {}).get("speed"), SPEED)
        point.update({"google_telemetry": telemetry, "google_telemetry_at": now,
                      "last_seen": timestamp(props.get("lastSeenTime")),
                      "hardware_type": props.get("hardwareType"),
                      "led_brightness": (settings["lightingSettings"].get("intensity", 0)
                                         if isinstance(settings.get("lightingSettings"), dict) else None)})
    properties = group.get("groupProperties") or {}
    other = properties.get("otherProperties") or {}
    settings = group.get("groupSettings") or {}
    tests = speed_tests.get("speedTestResults", []) if isinstance(speed_tests, dict) else []
    tests = [selected(r, ("timestamp", "receiveWanSpeedBps", "transmitWanSpeedBps")) for r in tests if isinstance(r, dict) and timestamp(r.get("timestamp"))]
    tests.sort(key=lambda r: timestamp(r["timestamp"]), reverse=True)
    latest = tests[0] if tests else {}
    telemetry = {
        "wanConnectionStatus": status.get("wanConnectionStatus"),
        "wanProperties": selected(properties.get("wanProperties"), ("wanMode", "ipAddress", "ipNetmask", "gateway", "dnsServers", "wanDnsServers")),
        "lanProperties": selected(properties.get("lanProperties"), ("ipNetmask",)),
        "firmware": selected(other, ("firmwareVersion", "encouragedUpdate", "synchronousUpdateEstimatedTimeRemaining")),
        "capabilities": {key: selected(value, ("supportStatus",)) for key, value in (other.get("capabilities") or {}).items() if isinstance(value, dict)},
        "groupTraffic": selected(metrics.get("groupTraffic"), TRAFFIC),
        "wanSpeedTestResults": tests[:50],
        "ipv6Enabled": (settings.get("wanSettings") or {}).get("ipv6Enabled"),
    }
    network.update({"google_telemetry": telemetry, "google_telemetry_at": now,
                    "wan_status": status.get("wanConnectionStatus"),
                    "wan_test_download_mbps": mbps(latest.get("receiveWanSpeedBps")),
                    "wan_test_upload_mbps": mbps(latest.get("transmitWanSpeedBps")),
                    "wan_test_at": timestamp(latest.get("timestamp"))})
    return network
