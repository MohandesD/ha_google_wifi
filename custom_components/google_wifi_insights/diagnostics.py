"""Export capability/count evidence, never credentials or client identities."""


async def async_get_config_entry_diagnostics(hass, entry):
    coordinator = entry.runtime_data
    return {
        "mode": entry.data["mode"],
        "last_update_success": coordinator.last_update_success,
        "radio_evidence": getattr(coordinator.client, "radio_evidence", {}),
        "networks": [
            {
                "points": len(network["points"]),
                "known_clients": len(network["clients"]),
                "connected_clients": network.get("connected_clients"),
                "clients_with_signal": network.get("clients_with_signal"),
                "unassigned_clients": network.get("unassigned_clients"),
                "assessment": network.get("diagnosis"),
                "saturation_available": False,
                "capabilities": network.get("capabilities", {}),
            }
            for network in (coordinator.data or {}).get("networks", {}).values()
        ],
    }
