"""Firmware notes and complete non-credential LAN/WAN information."""
import math
import re
from html import unescape
from html.parser import HTMLParser

from .capabilities import safe_metadata


class PlainText(HTMLParser):
    """Keep text and line breaks without executing or retaining provider HTML."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.hidden = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1
        elif tag in ("br", "p", "li", "div", "h1", "h2", "h3") and not self.hidden:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.hidden = max(0, self.hidden-1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def plain_text(value):
    if not isinstance(value, str):
        return ""
    parser = PlainText()
    parser.feed(value[:32768])
    return re.sub(r"\n[ \t\n]+", "\n", unescape("".join(parser.parts))).strip()[:8192]


def clean(value):
    """Exclude credentials, provisioning secrets and raw HTML in new reads."""
    value = safe_metadata(value)
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()
                if not re.search(r"username|setup.?code|qr.?code|pairing.?code|pin(?:code)?$|challenge|attestation|endorsement|ticket|descriptionHtml", k, re.I)}
    if isinstance(value, list):
        return [clean(v) for v in value]
    return value


def firmware_notes(payload, queried_version, read_status):
    rows = payload.get("releaseNotes", []) if isinstance(payload, dict) else []
    notes = []
    for row in rows[:30] if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        card = row.get("card") or {}
        if not isinstance(card, dict):
            continue
        version = row.get("apVersion")
        if not isinstance(version, str):
            continue
        notes.append({"version": version[:128], "title": plain_text(card.get("title")),
                      "description": plain_text(card.get("description") or card.get("descriptionHtml")),
                      "matches_installed": version == queried_version})
    return {"queried_version": queried_version, "notes": notes,
            "matching_installed": any(n["matches_installed"] for n in notes),
            "source": "google_cloud", **read_status}


def bool_value(value):
    return value if isinstance(value, bool) else None


def numeric(value):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except TypeError, ValueError, OverflowError:
        return None
    return number if math.isfinite(number) and number >= 0 else None


def apply_point_information(point):
    lan = point.get("lan_information") or {}
    local = lan.get("status") or point.get("local_status") or {}
    software, system, wan = (local.get(k) or {} for k in ("software", "system", "wan"))
    fresh = bool(local) and not lan.get("stale", False)
    notes = point.get("firmware_notes") or {}
    point["firmware_information"] = {
        "installed_version": point.get("firmware"),
        "local_version": software.get("softwareVersion") if fresh else None,
        "update_status": software.get("updateStatus") if fresh else None,
        "reported_new_version": software.get("updateNewVersion") if fresh else None,
        "update_required": bool_value(software.get("updateRequired")) if fresh else None,
        "update_channel": software.get("updateChannel") if fresh else None,
        # The API's raw progress scale is not established; do not invent a percent.
        "update_progress_raw": numeric(software.get("updateProgress")) if fresh else None,
        "blocking_update": software.get("blockingUpdate") if fresh else None,
        "lan_source": "google_lan", "lan_retrieved_at": lan.get("retrieved_at") or point.get("local_status_at"),
        "lan_stale": not fresh, "release_notes": notes,
    }
    point.update({"update_status": point["firmware_information"]["update_status"],
                  "update_channel": point["firmware_information"]["update_channel"],
                  "update_progress_raw": point["firmware_information"]["update_progress_raw"],
                  "update_required": point["firmware_information"]["update_required"],
                  "new_firmware_version": point["firmware_information"]["reported_new_version"],
                  "firmware_notes_count": len(notes.get("notes", [])) if notes.get("state") == "available" else None,
                  "lan_status": "stale" if lan.get("stale") and lan.get("retrieved_at") else "unavailable" if lan.get("stale") else "available" if fresh else "not_configured",
                  "wan_ip_method": wan.get("ipMethod") if fresh else None,
                  "wan_local_ip": wan.get("localIpAddress") if fresh else None,
                  "wan_gateway": wan.get("gatewayIpAddress") if fresh else None,
                  "wan_prefix_length": numeric(wan.get("ipPrefixLength")) if fresh else None,
                  "wan_lease_seconds": numeric(wan.get("leaseDurationSeconds")) if fresh else None,
                  "wan_online": bool_value(wan.get("online")) if fresh else None,
                  "ethernet_link": bool_value(wan.get("ethernetLink")) if fresh else None,
                  "lan0_link": bool_value(system.get("lan0Link")) if fresh else None,
                  "dns_mode": (local.get("dns") or {}).get("mode") if fresh else None,
                  "api_environment": (lan.get("developer_configuration") or {}).get("apiEnvironment"),
                  "firmware_information_at": lan.get("retrieved_at")})
    from .telemetry import timestamp
    point["firmware_information_at"] = timestamp(point["firmware_information_at"])
    if lan.get("endpoints", {}).get("developer_configuration", {}).get("stale"):
        point["api_environment"] = None
    if fresh and numeric(system.get("uptime")) is not None:
        point["uptime_seconds"] = numeric(system["uptime"])
    telemetry = point.setdefault("google_telemetry", {})
    telemetry.update(firmwareInformation=clean(point["firmware_information"]), lanInformation=clean(lan))


def apply_network_information(network):
    telemetry = network.get("google_telemetry", {})
    settings = telemetry.get("groupSettings") or {}
    properties = telemetry.get("groupProperties") or {}
    lan, wan = settings.get("lanSettings") or {}, properties.get("wanProperties") or {}
    roots = [p for p in network["points"].values() if p.get("is_root") is True]
    network["network_information"] = clean({
        "cloud": {"lan_properties": properties.get("lanProperties", {}), "wan_properties": wan,
                  "lan_settings": lan, "wan_settings": settings.get("wanSettings", {}),
                  "guest_wifi": settings.get("guestWirelessSettings", {}),
                  "wifi": settings.get("wlanSettings", {}), "mesh": settings.get("meshSettings", {}),
                  "family_wifi": settings.get("familyHubSettings", {}),
                  "other_settings": settings.get("otherSettings", {}),
                  "other_properties": properties.get("otherProperties", {}),
                  "remaining_settings": {k: v for k, v in settings.items() if k not in (
                      "lanSettings", "wanSettings", "guestWirelessSettings", "wlanSettings", "meshSettings", "familyHubSettings", "otherSettings")}},
        "primary_lan": roots[0].get("lan_information", {}) if len(roots) == 1 else {},
        "account_preferences": telemetry.get("accountPreferences", {}),
        "group_details": telemetry.get("groupDetails", {}),
        "retrieved_at": network.get("google_telemetry_at"),
    })
    network.update({"wan_ip_address": wan.get("ipAddress"), "wan_gateway": wan.get("gateway"),
                    "wan_mode": wan.get("wanMode"), "wan_netmask": wan.get("ipNetmask"),
                    "lan_ip_address": lan.get("ipAddress"), "lan_netmask": lan.get("netmask"),
                    "dhcp_pool_begin": lan.get("dhcpPoolBegin"), "dhcp_pool_end": lan.get("dhcpPoolEnd"),
                    "dns_mode": ((settings.get("wanSettings") or {}).get("dnsConfig") or {}).get("dnsMode"),
                    "ipv6_enabled": bool_value((settings.get("wanSettings") or {}).get("ipv6Enabled")),
                    "upnp_enabled": bool_value(lan.get("upnpEnabled")),
                    "guest_wifi_enabled": bool_value((settings.get("guestWirelessSettings") or {}).get("enabled")),
                    "network_information_status": "available" if network.get("source") == "google_cloud" else "local_only"})
    telemetry["networkInformation"] = network["network_information"]
