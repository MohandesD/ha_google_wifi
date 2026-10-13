"""HA services bound to real registry entities and their current cloud network."""
import voluptuous as vol
from homeassistant.core import SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry
from .const import DOMAIN
from .capabilities import ACTION_KINDS, safe_metadata


def register_services(hass):
    if hass.services.has_service(DOMAIN, "google_action"):
        return

    def resolve(entity_id):
        entity = entity_registry.async_get(hass).async_get(entity_id)
        state = hass.states.get(entity_id)
        if not entity or entity.platform != DOMAIN or not state:
            raise HomeAssistantError("Select an entity from Google WiFi Insights")
        entry = hass.config_entries.async_get_entry(entity.config_entry_id)
        coordinator = getattr(entry, "runtime_data", None)
        if not entry or entry.domain != DOMAIN or not coordinator or not coordinator.last_update_success:
            raise HomeAssistantError("Google WiFi entry is unavailable")
        attrs = state.attributes
        nid, kind, sid = (attrs.get(k) for k in ("gwi_network_id", "gwi_kind", "gwi_item_id"))
        if kind not in ("network", "point", "client") or not all(isinstance(i, str) for i in (nid, sid)) or not entity.unique_id.startswith(f"{entry.entry_id}:{nid}:{kind}:{sid}:"):
            raise HomeAssistantError("Entity target could not be verified")
        network = (coordinator.data or {}).get("networks", {}).get(nid, {})
        item = network if kind == "network" and sid == nid else network.get("points" if kind == "point" else "clients", {}).get(sid)
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

    base = {vol.Required("entity_id"): str}
    hass.services.async_register(DOMAIN, "google_action", action, schema=vol.Schema({**base, vol.Required("action"): vol.In(ACTION_KINDS), vol.Optional("parameters", default={}): dict}), supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, "get_usage_history", history, schema=vol.Schema({**base, vol.Required("resolution", default="hour"): vol.In(("minute", "hour", "day", "month"))}), supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, "get_capabilities", capabilities, schema=vol.Schema(base), supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, "get_google_metrics", telemetry, schema=vol.Schema(base), supports_response=SupportsResponse.ONLY)
