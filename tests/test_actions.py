from unittest.mock import AsyncMock

import pytest
from gwi_test import api
from gwi_test.actions import build_action
from homeassistant.exceptions import HomeAssistantError


def network():
    return {"name": "Test WiFi", "source": "google_cloud", "points": {"point": {"name": "Point"}}, "clients": {"client": {"name": "Client"}},
            "google_telemetry": {"groupSettings": {"stationSets": [{"id": "set"}]}, "insightCards": {"insightsCards": [{"id": "card", "actions": [{"actionType": "DISPLAY_URL"}]}]}}}


def test_google_requests_bound_to_target_encode_ids_and_do_not_modify_wifi_credentials():
    n = network()
    assert build_action(n, "group/slash", "restart_point", "point", "point", {}) == ("POST", "accesspoints/point/reboot", {})
    method, path, body = build_action(n, "group/slash", "pause_client", "client", "client", {})
    assert (method, path, body) == ("PUT", "groups/group%2Fslash/stationBlocking", {"blocked": True, "stationId": ["client"]})
    assert build_action(n, "group", "set_point_light", "point", "point", {"brightness": 42})[-1] == {"automatic": False, "intensity": 42}
    with pytest.raises(HomeAssistantError):
        build_action(n, "group", "restart_network", "client", "client", {})
    with pytest.raises(HomeAssistantError):
        build_action(n, "group", "prioritize_client", "client", "foreign", {})
    for invalid in (True, -1, 101, float("nan")):
        with pytest.raises(HomeAssistantError):
            build_action(n, "group", "set_point_light", "point", "point", {"brightness": invalid})


def test_advanced_removal_group_members_and_insight_actions_require_concrete_confirmation():
    n = network()
    with pytest.raises(HomeAssistantError, match="exact network"):
        build_action(n, "group", "remove_network", "network", "group", {})
    with pytest.raises(HomeAssistantError, match="target name"):
        build_action(n, "group", "remove_point", "point", "point", {"confirmation": "Test WiFi", "confirm_removal": "Other"})
    assert build_action(n, "group", "remove_point", "point", "point", {"confirmation": "Test WiFi", "confirm_removal": "Point"}) == ("DELETE", "accesspoints/point", {})
    with pytest.raises(HomeAssistantError, match="client IDs"):
        build_action(n, "group", "create_device_group", "network", "group", {"confirmation": "Test WiFi", "name": "Test", "station_ids": ["foreign"]})
    with pytest.raises(HomeAssistantError, match="links"):
        build_action(n, "group", "run_insight_action", "network", "group", {"confirmation": "Test WiFi", "card_id": "card"})


def test_mesh_request_uses_only_the_discovered_primary_in_the_selected_network():
    n = network()
    n["points"]["primary/point"] = {"name": "Primary", "is_root": True}
    assert build_action(n, "group", "test_mesh", "point", "point", {"serverApId": "foreign"}) == (
        "POST", "accesspoints/point/meshSpeedTest?serverApId=primary%2Fpoint", None)
    with pytest.raises(HomeAssistantError, match="separate"):
        build_action(n, "group", "test_mesh", "point", "primary/point", {})


@pytest.mark.parametrize("roots", [[], ["first", "second"]])
def test_mesh_request_rejects_missing_or_ambiguous_primary_instead_of_guessing(roots):
    n = network()
    n["points"].update({pid: {"name": pid, "is_root": True} for pid in roots})
    with pytest.raises(HomeAssistantError, match="uniquely identified"):
        build_action(n, "group", "test_mesh", "point", "point", {})


@pytest.mark.asyncio
async def test_mesh_server_query_survives_the_transport_and_is_sent_once_without_json_body():
    client = api.CloudClient(None, None, "test@example.invalid", "dummy", "0"*16)
    client._request = AsyncMock(return_value={"operation": {"operationId": "mesh", "operationState": "CREATED"}})
    n = network()
    n["points"]["primary/point"] = {"name": "Primary", "is_root": True}
    method, path, body = build_action(n, "group", "test_mesh", "point", "point", {})
    await client.action("group", "test_mesh", path, method, body, target_kind="point", target_id="point")
    client._request.assert_awaited_once_with("POST", "accesspoints/point/meshSpeedTest?serverApId=primary%2Fpoint&prettyPrint=false", None)


@pytest.mark.asyncio
async def test_write_transport_failure_is_never_retried_and_acceptance_is_not_completion():
    client = api.CloudClient(None, None, "test@example.invalid", "dummy", "0"*16)
    client._request = AsyncMock(side_effect=api.ApiError("delivery unconfirmed"))
    with pytest.raises(api.ApiError):
        await client.action("group", "restart_network", "groups/group/reboot", "POST", {})
    assert client._request.call_count == 1
    client._request = AsyncMock(return_value={"operation": {"operationId": "one", "operationState": "CREATED"}})
    result = await client.action("group", "test_internet", "groups/group/wanSpeedTest", "POST", {})
    assert result["state"] == "CREATED"
    client._get = AsyncMock(return_value={"operationState": "DONE"})
    await client._poll_operations("group")
    assert client._operations["group"][-1]["state"] == "DONE"


@pytest.mark.asyncio
async def test_denied_optional_endpoint_preserves_cached_history_and_backs_off():
    client = api.CloudClient(None, None, "test@example.invalid", "dummy", "0"*16)
    client._get = AsyncMock(side_effect=api.ApiError("HTTP 403", 403))
    await client._optional("group", "insightCards", "path", 300)
    await client._optional("group", "insightCards", "path", 300)
    assert client._get.call_count == 1
    assert client._read_status["group"]["insightCards"]["state"] == "denied"


@pytest.mark.parametrize("action", ["pause_group", "resume_group"])
def test_group_pause_uses_only_a_known_group_and_bounded_duration(action):
    n = network()
    method, path, payload = build_action(n, "group", action, "network", "group", {"group_id": "set", "duration_minutes": 30})
    assert (method, path) == ("PUT", "groups/group/stationBlocking")
    assert payload["stationSetId"] == ["set"]
    assert payload["blocked"] is action.startswith("pause")
    assert payload["expiryTimestamp"]
    with pytest.raises(HomeAssistantError, match="device group"):
        build_action(n, "group", action, "network", "group", {"group_id": "foreign"})


@pytest.mark.parametrize("action", ["create_device_group", "update_device_group", "delete_device_group"])
def test_group_edits_are_scoped_typed_requests(action):
    n = network()
    params = {"confirmation": n["name"], "group_id": "set", "name": "Example group", "station_ids": ["client", "client"]}
    method, path, payload = build_action(n, "group", action, "network", "group", params)
    assert method == ("DELETE" if action == "delete_device_group" else "POST")
    assert path == "groups/group/stationSets" + ("" if action == "create_device_group" else "/set")
    if action != "delete_device_group":
        assert payload["members"] == [{"stationId": "client"}]
        if action == "update_device_group":
            assert payload["updateMask"] == "name,members"
    if action != "create_device_group":
        with pytest.raises(HomeAssistantError, match="belong"):
            build_action(n, "group", action, "network", "group", {**params, "group_id": "foreign"})


def test_insight_actions_require_a_real_server_action_and_known_card():
    n = network()
    params = {"confirmation": n["name"], "card_id": "card"}
    assert build_action(n, "group", "dismiss_insight", "network", "group", params) == ("DELETE", "groups/group/insightCards/card", {})
    n["google_telemetry"]["insightCards"]["insightsCards"][0]["actions"] = [{"actionType": "RUN_ACTION"}]
    assert build_action(n, "group", "run_insight_action", "network", "group", params) == ("POST", "groups/group/insightCards/card/action", {})
    with pytest.raises(HomeAssistantError, match="belong"):
        build_action(n, "group", "dismiss_insight", "network", "group", {**params, "card_id": "foreign"})


def test_network_removal_request_keeps_both_name_confirmations_and_encodes_target():
    n = network()
    assert build_action(n, "group/slash", "remove_network", "network", "group/slash",
                        {"confirmation": n["name"], "confirm_removal": n["name"]}) == ("DELETE", "groups/group%2Fslash", {})
    with pytest.raises(HomeAssistantError, match="Automatic lighting"):
        build_action(n, "group", "set_point_light", "point", "point", {"automatic": "yes", "brightness": 10})
    with pytest.raises(HomeAssistantError, match="current Google"):
        build_action({**n, "source": "local_status"}, "group", "restart_network", "network", "group", {})
