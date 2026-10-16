"""Conservative normalization; absent radio data remains unknown."""

from __future__ import annotations

import ipaddress
import math
from datetime import UTC, datetime
from typing import Any

from .identity import ip_values, normalize_ip, normalize_mac
from .telemetry import extend_network, selected


def at(data: dict, path: str) -> Any:
    for part in path.split("."):
        if not isinstance(data, dict):
            return None
        data = data.get(part)
    return data


def first(data: dict, *paths: str) -> Any:
    return next(
        (value for path in paths if (value := at(data, path)) is not None), None
    )


def number(value: Any, minimum: float, maximum: float = math.inf) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except TypeError, ValueError, OverflowError:
        return None
    return result if math.isfinite(result) and minimum <= result <= maximum else None


def rate(traffic: dict, key: str, default=None) -> float | None:
    """Google's explicit Bps fields are bit/s, as used by the upstream sensor."""
    value = number(traffic.get(key, default), 0)
    return None if value is None else round(value / 1_000_000, 6)


def google_quality(speed: Any) -> tuple[str | None, str | None, float | None]:
    """Observed Google ratings are categories, not RSSI, percent or throughput."""
    if not isinstance(speed, dict):
        return None, None, None
    rating = speed.get("speedRating")
    if not isinstance(rating, str):
        return None, None, None
    quality = {"GREAT": "excellent", "OK": "good", "WEAK": "weak"}.get(rating)
    if quality is None:
        return None, None, None
    return quality, rating, number(speed.get("numericSpeedRating"), 0, 100)


def parse_points(text: str) -> list[dict[str, str]]:
    points, seen = [], set()
    for line in text.splitlines():
        if not line.strip():
            continue
        label, separator, host = line.strip().partition("=")
        if not separator:
            host, label = label, label
        ip = ipaddress.ip_address(host.strip())
        if (
            ip.version != 4
            or not ip.is_private
            or ip.is_loopback
            or ip.is_multicast
            or ip.is_unspecified
            or ip.is_reserved
            or ip.is_link_local
        ):
            raise ValueError("Use private LAN IPv4 addresses")
        if str(ip) in seen:
            raise ValueError("Duplicate point address")
        seen.add(str(ip))
        points.append({"host": str(ip), "name": label.strip()[:100] or str(ip)})
    if not 1 <= len(points) <= 10:
        raise ValueError("Configure between one and ten points")
    return points


def local_point(point: dict, status: dict | None) -> dict:
    """Unreachable is unavailable, not evidence of an offline radio."""
    wan, system, software = (
        (status or {}).get("wan", {}),
        (status or {}).get("system", {}),
        (status or {}).get("software", {}),
    )
    online = wan.get("online")
    from .information import clean
    result = {
        "name": point["name"],
        "host": point["host"],
        "online": online if isinstance(online, bool) else None,
        "role": system.get("groupRole"),
        "is_root": system.get("groupRole") == "root" if system.get("groupRole") in ("root", "leaf") else None,
        "firmware": software.get("softwareVersion"),
        "uptime_seconds": number(system.get("uptime"), 0),
        "clients": None,
        "weak_clients": None,
        "client_list": [],
        "source": "local_status",
        "reachable": status is not None,
        "local_status_at": datetime.now(UTC).isoformat() if status else None,
        "local_status": {
            "setupState": (status or {}).get("setupState"),
            "software": selected(software, ("blockingUpdate", "softwareVersion", "updateChannel", "updateNewVersion", "updateProgress", "updateStatus", "updateRequired")),
            "system": selected(system, ("countryCode", "groupRole", "hardwareId", "lan0Link", "ledAnimation", "ledIntensity", "modelId", "oobeDetailedStatus", "uptime")),
            "wan": selected(wan, ("ethernetLink", "gatewayIpAddress", "ipAddress", "ipMethod", "ipPrefixLength", "leaseDurationSeconds", "localIpAddress", "nameServers", "online", "vlanScanAttemptCount", "vlanScanComplete")),
            "dns": selected((status or {}).get("dns"), ("mode", "servers")),
            "migration": selected((status or {}).get("vorlonInfo"), ("migrationMode",)),
        } if status else {},
    }
    if status:
        result["local_status"] = {**clean(status), "migration": selected(status.get("vorlonInfo"), ("migrationMode",))}
    return result


def cloud_network(
    group: dict, status: dict, stations: list[dict], metrics: dict, station_macs=None, speed_tests=None
) -> dict:
    """Only explicit client/AP fields are used; no IP/BSSID inference."""
    points = {}
    ap_status = {
        item["apId"]: item
        for item in status.get("apStatuses", [])
        if isinstance(item, dict) and item.get("apId")
    }
    roots = [
        ap["id"] for ap in group.get("accessPoints", [])
        if isinstance(ap, dict) and ap.get("id")
        and at(ap, "accessPointProperties.isGroupRoot") is True
    ]
    root_id = roots[0] if len(roots) == 1 else None
    mesh_metrics = {
        item["apId"]: item for item in metrics.get("meshMetrics", [])
        if isinstance(item, dict) and item.get("apId")
    }
    for ap in group.get("accessPoints", []):
        if not isinstance(ap, dict) or not ap.get("id"):
            continue
        ap_id = ap["id"]
        settings = at(ap, "accessPointSettings.accessPointOtherSettings") or {}
        state = ap_status.get(ap_id, {}).get("apState")
        online = (
            True if state == "AP_ONLINE" else False if state == "AP_OFFLINE" else None
        )
        mesh_quality, mesh_rating, mesh_index = (
            google_quality(mesh_metrics.get(ap_id, {}).get("speed"))
            if online is True and ap_id != root_id
            and ap_status.get(root_id, {}).get("apState") != "AP_OFFLINE"
            else (None, None, None)
        )
        points[ap_id] = {
            "name": first(settings, "roomData.name", "apName") or ap_id,
            "online": online,
            "clients": 0,
            "weak_clients": 0,
            "client_list": [],
            "firmware": at(ap, "accessPointProperties.firmwareVersion"),
            "uptime_seconds": None,
            "host": at(ap, "accessPointProperties.ipAddress"),
            "is_root": ap_id == root_id if root_id else None,
            "root_ap_id": root_id,
            "mesh_quality": mesh_quality,
            "mesh_rating": mesh_rating,
            "mesh_rating_index": mesh_index,
            "mesh_quality_source": "google_mesh_rating" if mesh_quality else None,
            "source": "google_cloud",
            "reachable": True,
        }
    station_metrics = {
        at(item, "station.id"): item
        for item in metrics.get("stationMetrics", [])
        if isinstance(item, dict) and at(item, "station.id")
    }
    clients, missing_connection, unassigned = {}, 0, 0
    for station in stations:
        if not isinstance(station, dict) or not station.get("id"):
            continue
        station_id = station["id"]
        live = station_metrics.get(station_id, {})
        connected = station.get("connected")
        connected = connected if isinstance(connected, bool) else None
        if connected is None:
            missing_connection += 1
        ap_id = station.get("apId") if connected is True else None
        # RSSI remains optional. Account payloads validate Google's speed ratings.
        # Only explicit negative dBm values are accepted; percentages/enums are not RSSI.
        rssi = (
            number(first(station, "rssi", "connectionInfo.rssi"), -110, -1)
            if connected
            else None
        )
        if rssi is None and connected:
            rssi = number(first(live, "rssi", "station.rssi"), -110, -1)
        rssi_quality = (
            (
                "excellent"
                if rssi >= -55
                else "good"
                if rssi >= -67
                else "fair"
                if rssi >= -75
                else "weak"
            )
            if rssi is not None
            else None
        )
        live_station = live.get("station") or {}
        # A realtime result may belong to the point before a client roamed.
        # Only use a rating with a confirmed current association.
        current_rating = (
            connected is True and live_station.get("connected") is True
            and ap_id is not None and live_station.get("apId") == ap_id
        )
        rated_quality, google_rating, rating_index = (
            google_quality(live.get("speed")) if current_rating else (None, None, None)
        )
        quality = rated_quality or rssi_quality
        # Google's present traffic message omits zero-valued numeric fields (ProtoJSON).
        # No metric/message or a stale AP association remains unknown.
        traffic = live.get("traffic")
        traffic_current = current_rating and isinstance(traffic, dict)
        addresses = sorted(ip_values(station.get("ipAddresses", [])) | ip_values(station.get("ipAddress"))) if connected else []
        client = {
            "name": station.get("friendlyName") or station_id,
            "google_name": station.get("friendlyName") or station_id,
            "mac_address": normalize_mac((station_macs or {}).get(station_id)) or normalize_mac(station.get("macAddress")),
            "connected": connected,
            "ap_id": ap_id,
            "point": points.get(ap_id, {}).get("name"),
            "ip_address": normalize_ip(station.get("ipAddress")) if connected and normalize_ip(station.get("ipAddress")) else next((ip for ip in addresses if ":" not in ip), next(iter(addresses), None)),
            "ip_addresses": addresses,
            "connection_type": station.get("connectionType") if connected else None,
            "rssi": rssi,
            "signal_quality": quality,
            "quality_source": "google_connection_rating" if rated_quality
            else "rssi" if rssi_quality else None,
            "google_rating": google_rating,
            "google_rating_index": rating_index,
            "wireless_band": station.get("wirelessBand") if connected else None,
            "download_mbps": rate(traffic, "receiveSpeedBps", 0) if traffic_current else None,
            "upload_mbps": rate(traffic, "transmitSpeedBps", 0) if traffic_current else None,
            "traffic_source": "google_realtime_metrics" if traffic_current else None,
            "source": "google_cloud",
        }
        clients[station_id] = client
        if connected is True and ap_id in points:
            points[ap_id]["clients"] += 1
            points[ap_id]["client_list"].append(client["name"])
            if quality == "weak":
                points[ap_id]["weak_clients"] += 1
        elif connected is True:
            unassigned += 1
    active = [client for client in clients.values() if client["connected"] is True]
    signals = [client for client in active if client["rssi"] is not None]
    rated = [client for client in active if client["signal_quality"] is not None]
    weak = [client for client in rated if client["signal_quality"] == "weak"]
    weak_mesh = [point for point in points.values() if point["mesh_quality"] == "weak"]
    for ap_id, point in points.items():
        point_clients = [client for client in active if client["ap_id"] == ap_id]
        for direction in ("download", "upload"):
            values = [c.get(direction + "_mbps") for c in point_clients]
            point["client_" + direction + "_mbps"] = round(sum(values), 6) if values and all(v is not None for v in values) else None
        point["weak_clients"] = (
            point["weak_clients"]
            if point_clients
            and all(client["signal_quality"] is not None for client in point_clients)
            else None
        )
    group_traffic = metrics.get("groupTraffic") or {}
    return extend_network({
        "name": group.get("name") or "Google WiFi",
        "points": points,
        "clients": clients,
        "connected_clients": len(active) if not missing_connection else None,
        "unassigned_clients": unassigned,
        "unknown_connection_clients": missing_connection,
        "weak_clients": len(weak) if active and len(rated) == len(active) else None,
        "clients_with_signal": len(signals),
        "clients_with_quality": len(rated),
        "weak_mesh_points": len(weak_mesh) if any(p["mesh_quality"] for p in points.values()) else None,
        "download_mbps": rate(group_traffic, "receiveSpeedBps"),
        "upload_mbps": rate(group_traffic, "transmitSpeedBps"),
        "diagnosis": "point_offline"
        if any(point["online"] is False for point in points.values())
        else "weak_mesh_detected"
        if weak_mesh
        else "weak_signal_detected"
        if weak
        else "quality_data_available"
        if rated or any(p["mesh_quality"] for p in points.values())
        else "insufficient_radio_data",
        "saturation": None,
        "source": "google_cloud",
    }, group, status, stations, metrics, speed_tests or {})


def apply_roaming(current: dict, previous: dict | None) -> dict:
    """Count observed AP changes only across two connected samples."""
    for network_id, network in current["networks"].items():
        old_clients = (
            (previous or {}).get("networks", {}).get(network_id, {}).get("clients", {})
        )
        for client_id, client in network["clients"].items():
            old = old_clients.get(client_id, {})
            changed = bool(
                client.get("connected") is True
                and old.get("connected") is True
                and client.get("ap_id")
                and old.get("ap_id")
                and client["ap_id"] != old["ap_id"]
            )
            client["roams_since_start"] = old.get("roams_since_start", 0) + int(changed)
            client["last_roam"] = (
                datetime.now(UTC).isoformat() if changed else old.get("last_roam")
            )
    return current
