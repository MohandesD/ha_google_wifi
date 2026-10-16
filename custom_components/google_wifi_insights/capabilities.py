"""Finite, inspectable inventory. Path discovery is not proof a write works."""
import math
import re
from datetime import date, datetime

READS = {
    "speedTestResults": 3600, "wifiblasterSpeedTestResults": 300,
    "meshSpeedTestResults": 300, "backhaulOfChildNodes": 300,
    "insightCards": 900, "meshConfiguration": 3600,
}
ACTION_KINDS = {
    "restart_network": "network", "restart_point": "point",
    "test_internet": "network", "test_mesh": "point",
    "test_local": "point", "test_clients": "point",
    "pause_client": "client", "resume_client": "client",
    "prioritize_client": "client", "clear_priority": "network",
    "set_point_light": "point", "pause_group": "network", "resume_group": "network",
    "create_device_group": "network", "update_device_group": "network",
    "delete_device_group": "network", "dismiss_insight": "network",
    "run_insight_action": "network", "remove_point": "point", "remove_network": "network",
}
ADVANCED = {"create_device_group", "update_device_group", "delete_device_group",
            "dismiss_insight", "run_insight_action", "remove_point", "remove_network"}
DESTRUCTIVE = {"remove_point", "remove_network"}
UNVERIFIED = {
    "guest_wifi_configuration": "request_schema_unverified",
    "ssid_password_configuration": "request_schema_unverified",
    "dns_configuration": "request_schema_unverified",
    "dhcp_static_ip_configuration": "request_schema_unverified",
    "upnp_ipv6_port_forwarding": "request_schema_unverified",
    "blocking_schedules_content_filtering": "request_schema_unverified",
    "rename_client": "android_schema_verified_use_name_services",
    "pin_bssid": "not_exposed_by_google",
    "radio_airtime_noise_retries": "not_supplied",
    "physical_mesh_routes": "not_supplied",
    "wifi_credentials": "credential_not_telemetry",
}


def safe_metadata(value, depth=0):
    """Keep new telemetry fields while excluding credentials and opaque blobs."""
    if depth > 14:
        return "[depth limit]"
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        result = {}
        for key, child in list(value.items())[:2000]:
            if re.search(r"token|auth|password|passphrase|secret|credential|certificate|private.?key|psk|kek|email|meshConfiguration", key, re.I):
                continue
            result[key] = safe_metadata(child, depth+1)
        return result
    if isinstance(value, list):
        return [safe_metadata(child, depth+1) for child in value[:2000]]
    if isinstance(value, str):
        if re.search(r"aas_et/|oauth2(?:rt)?_|eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.", value):
            return "[credential omitted]"
        return value[:4096]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value if isinstance(value, (int, float, bool)) or value is None else None


def apply_extras(network, group, extras, read_status, action_status):
    from datetime import UTC, datetime

    from .telemetry import mbps, timestamp
    now = datetime.now(UTC)
    telemetry = network["google_telemetry"]
    telemetry["groupProperties"] = safe_metadata(group.get("groupProperties", {}))
    telemetry["groupSettings"] = safe_metadata(group.get("groupSettings", {}))
    for endpoint in ("backhaulOfChildNodes", "insightCards"):
        telemetry[endpoint] = safe_metadata(extras.get(endpoint, {}))
    telemetry["meshConfiguration"] = {"available": "meshConfiguration" in extras,
                                      "content": "opaque configuration omitted"}
    network["capabilities"] = {"reads": read_status,
                               "actions": {action: {"state": action_status.get(action, "not_tested"),
                                                    "target": kind, "advanced": action in ADVANCED,
                                                    "destructive": action in DESTRUCTIVE}
                                           for action, kind in ACTION_KINDS.items()},
                               "other": UNVERIFIED}
    network["capability_count"] = sum(s.get("state") == "available" for s in read_status.values())
    settings = group.get("groupSettings") or {}
    family, lan = settings.get("familyHubSettings") or {}, settings.get("lanSettings") or {}
    policies = {r.get("stationId"): r for r in family.get("stationPolicies", []) if isinstance(r, dict)}
    priority = lan.get("prioritizedStation") or {}
    priority_end = timestamp(priority.get("prioritizationEndTime"))
    for sid, client in network["clients"].items():
        policy = policies.get(sid, {}).get("blockingPolicy")
        expiry = (policy or {}).get("expiryTimestamp")
        parsed = timestamp(expiry)
        client["internet_paused"] = bool(policy and (expiry == "1970-01-01T00:00:00Z" or parsed and parsed > now)) if "stationPolicies" in family else None
        client["pause_until"] = parsed if client["internet_paused"] else None
        client["priority_active"] = bool(priority.get("stationId") == sid and priority_end and priority_end > now) if "prioritizedStation" in lan else None
        client["priority_until"] = priority_end if client["priority_active"] else None
        client["google_telemetry"]["fullStationMetadata"] = safe_metadata(client.get("_station_metadata", {}))
        client.pop("_station_metadata", None)
    station_tests = extras.get("wifiblasterSpeedTestResults", {}).get("stationResults", [])
    for row in sorted((r for r in station_tests if isinstance(r, dict) and timestamp(r.get("timestamp"))), key=lambda r: timestamp(r["timestamp"])):
        client = network["clients"].get(row.get("stationId"))
        if client is not None:
            client.update({"wifi_test_mbps": mbps(row.get("throughputBps")), "wifi_test_at": timestamp(row["timestamp"]),
                           "wifi_test_ap_id": row.get("apId"),
                           "wifi_test_point": network["points"].get(row.get("apId"), {}).get("name")})
    mesh_tests = extras.get("meshSpeedTestResults", {}).get("speedTestResults", [])
    for row in sorted((r for r in mesh_tests if isinstance(r, dict) and timestamp(r.get("timestamp"))), key=lambda r: timestamp(r["timestamp"])):
        point = network["points"].get(row.get("clientApId"))
        if point is not None:
            point.update({"mesh_test_mbps": mbps(row.get("receiveSpeedBps")), "mesh_test_at": timestamp(row["timestamp"])})
    for row in extras.get("backhaulOfChildNodes", {}).get("apBackhaul", []):
        if isinstance(row, dict) and row.get("apId") in network["points"]:
            network["points"][row["apId"]]["backhaul_type"] = row.get("backhaul")
    for ap in group.get("accessPoints", []):
        if isinstance(ap, dict) and ap.get("id") in network["points"]:
            network["points"][ap["id"]]["google_telemetry"]["fullPointMetadata"] = safe_metadata(ap)
    for item in [network, *network["points"].values(), *network["clients"].values()]:
        for key in ("wifi_test_mbps", "wifi_test_at", "wifi_test_point", "wifi_test_ap_id", "mesh_test_mbps", "mesh_test_at", "backhaul_type", "internet_paused", "pause_until", "priority_active", "priority_until", "usage_windows", "usage_hourly"):
            if key in item:
                item["google_telemetry"][key] = item[key]
