"""Export capability/count evidence, never credentials or client identities."""

from collections import Counter

from .capabilities import ACTION_KINDS, ADVANCED, DESTRUCTIVE, READS, UNVERIFIED
from .telemetry import timestamp

READ_STATES = {"available", "denied", "error", "unavailable", "not_supported", "not_supplied", "not_configured"}
READ_NAMES = {*READS, "groups", "status", "stations", "realtimeMetrics", "groupDetails", "userPreferences",
              "usage_minute", "usage_hour", "usage_day", "usage_month"}


def diagnostic_capabilities(capabilities):
    """Use fixed endpoint/action names; hardware cache keys contain real AP IDs."""
    reads = {}
    for key, value in capabilities.get("reads", {}).items():
        if not isinstance(key, str) or not isinstance(value, dict):
            continue
        name = "hardware" if key.startswith("hardware:") else "firmware_notes" if key.startswith("notes:") else key
        if name not in READ_NAMES | {"hardware", "firmware_notes"}:
            continue
        record = {"state": value.get("state") if value.get("state") in READ_STATES else "unknown",
                  "stale": value.get("stale") is True}
        observed = timestamp(value.get("retrieved_at"))
        if observed:
            record["retrieved_at"] = observed.isoformat()
        status = value.get("http_status")
        if isinstance(status, int) and not isinstance(status, bool) and 100 <= status <= 599:
            record["http_status"] = status
        if name in {"hardware", "firmware_notes"}:
            reads.setdefault(name, []).append(record)
        else:
            reads[name] = record
    actions = {}
    for name, value in capabilities.get("actions", {}).items():
        if name not in ACTION_KINDS or not isinstance(value, dict):
            continue
        state = value.get("state")
        actions[name] = {"state": state if state in {"not_tested", "accepted", "denied", "unconfirmed"} else "unknown",
                         "target": ACTION_KINDS[name], "advanced": name in ADVANCED, "destructive": name in DESTRUCTIVE}
    return {"reads": reads, "actions": actions, "other": UNVERIFIED.copy()}


async def async_get_config_entry_diagnostics(hass, entry):
    coordinator = entry.runtime_data
    return {
        "mode": entry.data["mode"],
        "last_update_success": coordinator.last_update_success,
        "network_errors": dict(Counter(error.get("state", "unavailable") for error in getattr(coordinator.client, "network_errors", {}).values()
                                       if error.get("state") in {"denied", "unavailable", "invalid_response"})),
        "radio_evidence": getattr(coordinator.client, "radio_evidence", {}),
        "networks": [
            {
                "points": len(network["points"]),
                "available": coordinator.last_update_success and network.get("reachable", True),
                "known_clients": len(network["clients"]),
                "connected_clients": network.get("connected_clients"),
                "clients_with_signal": network.get("clients_with_signal"),
                "unassigned_clients": network.get("unassigned_clients"),
                "assessment": network.get("diagnosis"),
                "saturation_available": False,
                "capabilities": diagnostic_capabilities(network.get("capabilities", {})),
            }
            for network in (coordinator.data or {}).get("networks", {}).values()
        ],
    }
