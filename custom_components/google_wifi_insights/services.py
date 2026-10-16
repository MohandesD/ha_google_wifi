"""HA services bound to real registry entities and their current cloud network."""
import voluptuous as vol
from homeassistant.core import SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry

from .capabilities import ACTION_KINDS, safe_metadata
from .const import DOMAIN


def register_services(hass):
    if hass.services.has_service(DOMAIN, "google_action"):
        return

    def resolve(entity_id, *, allow_unavailable=False):
        entity = entity_registry.async_get(hass).async_get(entity_id)
        state = hass.states.get(entity_id)
        if not entity or entity.platform != DOMAIN or not state:
            raise HomeAssistantError("Select an entity from Google WiFi Insights")
        entry = hass.config_entries.async_get_entry(entity.config_entry_id)
        coordinator = getattr(entry, "runtime_data", None)
        if not entry or entry.domain != DOMAIN or not coordinator or (not allow_unavailable and not coordinator.last_update_success):
            raise HomeAssistantError("Google WiFi entry is unavailable")
        attrs = state.attributes
        nid, kind, sid = (attrs.get(k) for k in ("gwi_network_id", "gwi_kind", "gwi_item_id"))
        if kind not in ("network", "point", "client") or not all(isinstance(i, str) for i in (nid, sid)) or not entity.unique_id.startswith(f"{entry.entry_id}:{nid}:{kind}:{sid}:"):
            raise HomeAssistantError("Entity target could not be verified")
        network = (coordinator.data or {}).get("networks", {}).get(nid, {})
        item = network if kind == "network" and sid == nid else network.get("points" if kind == "point" else "clients", {}).get(sid)
        if not allow_unavailable and network.get("reachable") is False:
            raise HomeAssistantError("Google WiFi network is unavailable; wait for a successful update")
        if not item or network.get("source") != "google_cloud":
            raise HomeAssistantError("Select a current Google account entity")
        return coordinator, nid, kind, sid

    async def authorized(call):
        if call.context.user_id:
            user = await hass.auth.async_get_user(call.context.user_id)
            if not user or not user.is_admin:
                raise HomeAssistantError("This service requires a Home Assistant administrator")

    async def action(call):
        await authorized(call)
        coordinator, nid, kind, sid = resolve(call.data["entity_id"])
        return await coordinator.async_google_action(nid, kind, sid, call.data["action"], call.data.get("parameters", {}), call.context)

    async def history(call):
        await authorized(call)
        coordinator, nid, kind, sid = resolve(call.data["entity_id"])
        if kind == "point":
            raise HomeAssistantError("Historical usage is per client or Internet connection, not per point")
        mode = call.data["resolution"]
        data = getattr(coordinator.client, "_histories", {}).get(nid, {}).get(mode)
        if not data:
            raise HomeAssistantError("Google has not supplied this usage history")
        rows = data["wan"] if kind == "network" else data["stations"].get(sid, [])
        return {"period": data["period"], "retrieved_at": data["retrieved_at"],
                "series": rows, "peaks": data["peaks"] if kind == "network" else [],
                "timestamp_semantics": "bucket_end", "unit": "bytes"}

    async def capabilities(call):
        await authorized(call)
        coordinator, nid, _, _ = resolve(call.data["entity_id"])
        network = coordinator.data["networks"][nid]
        return safe_metadata({"capabilities": network.get("capabilities", {}), "operations": network.get("operations", [])})

    async def telemetry(call):
        await authorized(call)
        coordinator, nid, kind, sid = resolve(call.data["entity_id"])
        network = coordinator.data["networks"][nid]
        item = network if kind == "network" else network["points" if kind == "point" else "clients"][sid]
        result = {"metrics": item.get("google_telemetry", {}), "capabilities": network.get("capabilities", {})}
        if kind == "network":
            result["saved_results"] = getattr(coordinator.client, "_optional_cache", {}).get(nid, {})
        return safe_metadata(result)

    async def management(call):
        await authorized(call)
        coordinator, nid, _, _ = resolve(call.data["entity_id"], allow_unavailable=True)
        return coordinator.management.response(nid, coordinator.data["networks"][nid])

    async def naming(call):
        await authorized(call)
        service = call.service
        interactive = service in ("rename_client", "undo_name") or service == "set_name_sync" and call.data["enabled"]
        if interactive and not call.context.user_id:
            raise HomeAssistantError("Name changes require an interactive Home Assistant administrator")
        coordinator, nid, kind, sid = resolve(call.data["entity_id"], allow_unavailable=service == "set_name_sync" and not call.data["enabled"])
        result = None
        if service == "set_name_sync":
            await coordinator.names.async_set_enabled(nid, call.data["enabled"])
            coordinator._schedule_name_sync()
        elif service == "rename_client":
            if kind != "client":
                raise HomeAssistantError("Select a Google WiFi client entity")
            result = await coordinator.names.async_rename(nid, sid, call.data["expected_google_name"], call.data["expected_mac"], call.data["expected_ha_name"])
        elif service == "undo_name":
            result = await coordinator.names.async_undo(nid, call.data["request_id"])
        else:
            result = await coordinator.names.async_verify(nid, call.data["request_id"])
        if coordinator._stopping:
            raise HomeAssistantError("The integration unloaded; review the saved name-change history after reload")
        return {**coordinator.management.response(nid, coordinator.data["networks"][nid]), "name_result": result}

    async def point_area(call):
        await authorized(call)
        coordinator, nid, kind, sid = resolve(call.data["entity_id"])
        if kind != "point":
            raise HomeAssistantError("Select a Google WiFi point entity")
        await coordinator.async_set_point_area(nid, sid, call.data["area_id"])
        return coordinator.management.response(nid, coordinator.data["networks"][nid])

    base = {vol.Required("entity_id"): str}
    hass.services.async_register(DOMAIN, "google_action", action, schema=vol.Schema({**base, vol.Required("action"): vol.In(ACTION_KINDS), vol.Optional("parameters", default={}): dict}), supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, "get_usage_history", history, schema=vol.Schema({**base, vol.Required("resolution", default="hour"): vol.In(("minute", "hour", "day", "month"))}), supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, "get_capabilities", capabilities, schema=vol.Schema(base), supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, "get_google_metrics", telemetry, schema=vol.Schema(base), supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, "get_management", management, schema=vol.Schema(base), supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, "set_point_area", point_area, schema=vol.Schema({**base, vol.Required("area_id"): vol.Any(None, str)}), supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, "set_name_sync", naming, schema=vol.Schema({**base, vol.Required("enabled"): bool}), supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, "rename_client", naming, schema=vol.Schema({**base, vol.Required("expected_google_name"): str, vol.Required("expected_ha_name"): str, vol.Required("expected_mac"): str}), supports_response=SupportsResponse.ONLY)
    for service in ("undo_name", "verify_name"):
        hass.services.async_register(DOMAIN, service, naming, schema=vol.Schema({**base, vol.Required("request_id"): str}), supports_response=SupportsResponse.ONLY)
