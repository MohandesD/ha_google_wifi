"""Typed requests from independently documented Google Wifi clients."""
from datetime import UTC, datetime, timedelta
from urllib.parse import quote
import math
from homeassistant.exceptions import HomeAssistantError
from .capabilities import ACTION_KINDS, ADVANCED, DESTRUCTIVE


def integer(value, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value != int(value) or not minimum <= value <= maximum:
        raise HomeAssistantError(f"Value must be an integer between {minimum} and {maximum}")
    return int(value)


def build_action(network, network_id, action, kind, item_id, parameters):
    if ACTION_KINDS.get(action) != kind:
        raise HomeAssistantError("This Google action does not match the selected target")
    item = network if kind == "network" else network.get("points" if kind == "point" else "clients", {}).get(item_id)
    if not item or network.get("source") != "google_cloud":
        raise HomeAssistantError("Select a current Google cloud entity")
    if action in ADVANCED and parameters.get("confirmation") != network["name"]:
        raise HomeAssistantError("Confirm this advanced action by entering the exact network name")
    if action in DESTRUCTIVE and parameters.get("confirm_removal") != item["name"]:
        raise HomeAssistantError("Confirm removal by entering the exact target name; this can erase the network configuration")
    prefix = "groups/"+quote(network_id, safe="")+"/"
    ap = "accesspoints/"+quote(item_id, safe="")+"/"
    if action == "test_mesh":
        # Google requires a server AP query parameter, not an empty test body.
        roots = [pid for pid, point in network.get("points", {}).items()
                 if point.get("is_root") is True]
        if len(roots) != 1 or roots[0] == item_id:
            raise HomeAssistantError("A mesh test requires a separate, uniquely identified primary point in this network")
        return "POST", ap+"meshSpeedTest?serverApId="+quote(roots[0], safe=""), None
    endpoints = {"restart_network": prefix+"reboot", "restart_point": ap+"reboot",
                 "test_internet": prefix+"wanSpeedTest",
                 "test_local": ap+"localSpeedTest", "test_clients": ap+"wifiblasterSpeedTest"}
    if action in endpoints:
        return "POST", endpoints[action], {}
    if action == "set_point_light":
        if not isinstance(parameters.get("automatic", False), bool):
            raise HomeAssistantError("Automatic lighting must be true or false")
        return "PUT", ap+"lighting", {"automatic": parameters.get("automatic", False), "intensity": integer(parameters.get("brightness"), 0, 100)}
    if action in ("pause_client", "resume_client", "pause_group", "resume_group"):
        payload = {"blocked": action.startswith("pause"), "stationId": [item_id]}
        if kind == "network":
            group = parameters.get("group_id")
            valid = {r.get("id") for r in network["google_telemetry"].get("groupSettings", {}).get("stationSets", []) if isinstance(r, dict)}
            if group not in valid:
                raise HomeAssistantError("Select a Google device group in this network")
            payload = {"blocked": action.startswith("pause"), "stationSetId": [group]}
        duration = parameters.get("duration_minutes", 0)
        if duration:
            payload["expiryTimestamp"] = (datetime.now(UTC)+timedelta(minutes=integer(duration, 1, 1440))).isoformat()
        return "PUT", prefix+"stationBlocking", payload
    if action == "prioritize_client":
        minutes = integer(parameters.get("duration_minutes", 60), 1, 360)
        return "PUT", prefix+"prioritizedStation", {"stationId": item_id, "prioritizationEndTime": (datetime.now(UTC)+timedelta(minutes=minutes)).isoformat()}
    if action == "clear_priority":
        return "DELETE", prefix+"prioritizedStation", {}
    if action in ("create_device_group", "update_device_group", "delete_device_group"):
        group_id = parameters.get("group_id")
        valid = {r.get("id") for r in network["google_telemetry"].get("groupSettings", {}).get("stationSets", []) if isinstance(r, dict)}
        if action != "create_device_group" and group_id not in valid:
            raise HomeAssistantError("Device group does not belong to this network")
        path = prefix+"stationSets"+("/"+quote(group_id, safe="") if action != "create_device_group" else "")
        if action == "delete_device_group":
            return "DELETE", path, {}
        members, name = parameters.get("station_ids"), parameters.get("name")
        if not isinstance(members, list) or not members or any(s not in network["clients"] for s in members) or not isinstance(name, str) or not 1 <= len(name.strip()) <= 64:
            raise HomeAssistantError("Use a group name and client IDs belonging to this network")
        payload = {"name": name.strip(), "members": [{"stationId": s} for s in sorted(set(members))]}
        if action == "update_device_group":
            payload["updateMask"] = "name,members"
        else:
            payload["color"] = {"red": 0.25, "green": 0.5, "blue": 0.75}
        return "POST", path, payload
    if action in ("dismiss_insight", "run_insight_action"):
        card_id = parameters.get("card_id")
        cards = network["google_telemetry"].get("insightCards", {}).get("insightsCards", [])
        if card_id not in {c.get("id") for c in cards if isinstance(c, dict)}:
            raise HomeAssistantError("Insight card does not belong to this network")
        if action == "run_insight_action":
            card = next(c for c in cards if c.get("id") == card_id)
            if not any(a.get("actionType") not in ("DISPLAY_URL", "DISPLAY_HELP_ARTICLE", None) for a in card.get("actions", []) if isinstance(a, dict)):
                raise HomeAssistantError("This insight only contains Google Home links, not a server action")
        return ("DELETE", prefix+"insightCards/"+quote(card_id, safe=""), {}) if action == "dismiss_insight" else ("POST", prefix+"insightCards/"+quote(card_id, safe="")+"/action", {})
    if action == "remove_point":
        return "DELETE", ap.rstrip("/"), {}
    if action == "remove_network":
        return "DELETE", prefix.rstrip("/"), {}
    raise HomeAssistantError("Unknown Google action")
