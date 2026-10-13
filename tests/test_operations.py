"""Exercise real operation state transitions, uncertain delivery and target isolation."""
import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from gwi_test.api import ApiError, CloudClient, RateLimitError
from gwi_test.operations import latest, phase, summary


def client():
    return CloudClient(None, None, "test@example.invalid", "dummy", "0"*16)


@pytest.mark.asyncio
async def test_pending_write_is_visible_and_duplicate_never_sends_a_second_command():
    c = client()
    release = asyncio.Event()
    observed = []

    async def response(*args):
        await release.wait()
        return {"operation": {"operationId": "opaque/command", "operationState": "CREATED"}}

    c._request = AsyncMock(side_effect=response)
    request = asyncio.create_task(c.action("network", "restart_point", "accesspoints/point/reboot", "POST", {},
        target_kind="point", target_id="point", target_name="Test point",
        on_update=lambda: observed.append(summary(c._operations["network"][-1]))))
    await asyncio.sleep(0)
    assert observed[-1]["phase"] == "sending"
    with pytest.raises(ApiError, match="already pending"):
        await c.action("network", "restart_point", "accesspoints/point/reboot", "POST", {}, target_kind="point", target_id="point")
    release.set()
    result = await request
    assert c._request.call_count == 1
    assert [row["phase"] for row in observed] == ["queued", "sending", "accepted"]
    assert result["target_id"] == "point" and phase(result) == "accepted"
    assert "operation_id" not in summary(result)
    network = {"operations": c._operations["network"]}
    assert latest(network, "point", "other") is None
    assert latest(network, "point", "point", "test_mesh") is None
    assert latest(network, "point", "point", "restart_point")["request_id"] == result["request_id"]
    c._get = AsyncMock(side_effect=[{"operationState": "RUNNING"}, {"operation": {"operationState": "DONE"}}])
    await c._poll_operations("network")
    assert phase(c._operations["network"][-1]) == "running"
    await c._poll_operations("network")
    assert phase(c._operations["network"][-1]) == "completed"
    assert c._operations["network"][-1]["finished_at"]
    assert not c.has_pending_operations("network")


@pytest.mark.asyncio
@pytest.mark.parametrize("response,expected,error", [
    ({"operation": {"operationId": "op", "operationState": "ERROR"}}, "failed", True),
    ({"operation": {"operationId": "op", "operationState": "CANCELLED"}}, "cancelled", True),
    ({}, "unconfirmed", False),
    ([], "unconfirmed", True),
])
async def test_immediate_failure_and_ambiguous_acknowledgement_are_not_success(response, expected, error):
    c = client()
    c._request = AsyncMock(return_value=response)
    args = ("network", "test_internet", "groups/network/wanSpeedTest", "POST", {})
    if error:
        with pytest.raises(ApiError):
            await c.action(*args)
    else:
        await c.action(*args)
    assert phase(c._operations["network"][-1]) == expected
    assert not c.has_pending_operations("network")
    assert c._request.call_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("error,expected", [(ApiError("rejected", 403), "failed"), (ApiError("server error", 503), "unconfirmed"), (ApiError("transport failure"), "unconfirmed"), (RateLimitError(60), "failed")])
async def test_write_errors_record_their_uncertainty_and_are_not_retried(error, expected):
    c = client()
    c._request = AsyncMock(side_effect=error)
    with pytest.raises(ApiError):
        await c.action("network", "restart_network", "groups/network/reboot", "POST", {})
    assert phase(c._operations["network"][-1]) == expected
    assert c._request.call_count == 1


@pytest.mark.asyncio
async def test_expired_operation_stops_monitoring_without_claiming_failure_or_completion():
    c = client()
    c._operations = {"network": [{"action": "test_mesh", "state": "CREATED", "operation_id": "op",
                                "requested_at": (datetime.now(UTC)-timedelta(minutes=11)).isoformat()}]}
    c._get = AsyncMock()
    await c._poll_operations("network")
    assert summary(c._operations["network"][-1])["phase"] == "unconfirmed"
    assert c._operations["network"][-1]["status_error"] == "monitoring_timeout"
    assert not c.has_pending_operations("network")
    c._get.assert_not_called()


@pytest.mark.asyncio
async def test_older_status_response_cannot_regress_an_already_completed_operation():
    c = client()
    c._operations = {"network": [{"action": "test_mesh", "state": "CREATED", "operation_id": "op", "requested_at": datetime.now(UTC).isoformat()}]}
    release = asyncio.Event()
    count = 0

    async def response(*args):
        nonlocal count
        count += 1
        if count == 1:
            await release.wait()
            return {"operationState": "RUNNING"}
        return {"operationState": "DONE"}

    c._get = AsyncMock(side_effect=response)
    slow = asyncio.create_task(c._poll_operations("network"))
    await asyncio.sleep(0)
    await c._poll_operations("network")
    release.set()
    await slow
    assert phase(c._operations["network"][-1]) == "completed"


async def mesh_request(c):
    return await c.action("network", "test_mesh", "accesspoints/point/meshSpeedTest?serverApId=primary", "POST", None,
        target_kind="point", target_id="point", prepare_path="accesspoints/primary/localSpeedTest")


@pytest.mark.asyncio
async def test_mesh_prepares_primary_once_waits_for_readiness_and_tracks_client_until_done():
    c = client()
    c._request = AsyncMock(side_effect=[{"operation": {"operationId": "server", "operationState": "CREATED"}},
                                        {"operation": {"operationId": "client", "operationState": "CREATED"}}])
    c._get = AsyncMock(side_effect=[{"operationState": "IN_PROGRESS"}, {"operationState": "DONE"},
                                   {"operationState": "IN_PROGRESS"}, {"operationState": "DONE"}])
    c._optional_next[("network", "meshSpeedTestResults")] = float("inf")
    result = await mesh_request(c)
    assert result["stage"] == "preparing_server" and phase(result) == "accepted"
    await c._poll_operations("network")
    assert c._request.call_count == 1
    await c._poll_operations("network")
    operation = c._operations["network"][-1]
    assert operation["stage"] == "measuring" and operation["server_state"] == "DONE"
    assert phase(operation) == "accepted" and "finished_at" not in operation
    c._request.assert_awaited_with("POST", "accesspoints/point/meshSpeedTest?serverApId=primary&prettyPrint=false", None)
    await c._poll_operations("network")
    assert phase(operation) == "running"
    await c._poll_operations("network")
    assert phase(operation) == "completed" and c._request.call_count == 2
    assert not c._mesh_requests and ("network", "meshSpeedTestResults") not in c._optional_next


@pytest.mark.asyncio
async def test_failed_mesh_server_never_starts_the_client_or_claims_completion():
    c = client()
    c._request = AsyncMock(return_value={"operation": {"operationId": "server", "operationState": "CREATED"}})
    c._get = AsyncMock(return_value={"operationState": "ERROR"})
    await mesh_request(c)
    await c._poll_operations("network")
    assert phase(c._operations["network"][-1]) == "failed"
    assert not c._mesh_requests and c._request.call_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["CREATED", "DONE", None])
async def test_mesh_server_without_a_correlated_operation_id_is_unconfirmed(state):
    c = client()
    c._request = AsyncMock(return_value={"operation": {"operationState": state}})
    result = await mesh_request(c)
    await c._poll_operations("network")
    assert phase(result) == "unconfirmed" and c._request.call_count == 1
    assert not c._mesh_requests and "finished_at" not in result


@pytest.mark.asyncio
async def test_mesh_immediate_server_success_does_not_finish_the_combined_test():
    c = client()
    c._request = AsyncMock(side_effect=[{"operation": {"operationId": "server", "operationState": "DONE"}},
                                        {"operation": {"operationId": "client", "operationState": "CREATED"}}])
    c._get = AsyncMock()
    result = await mesh_request(c)
    assert phase(result) == "accepted" and "finished_at" not in result
    await c._poll_operations("network")
    assert c._request.call_count == 2 and c._operations["network"][-1]["operation_id"] == "client"
    c._get.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("response,expected", [(ApiError("transport failure"), "unconfirmed"), ({}, "unconfirmed"), ([], "unconfirmed"), (ApiError("rejected", 400), "failed")])
async def test_mesh_client_uncertainty_is_not_retried_after_server_preparation(response, expected):
    c = client()
    c._request = AsyncMock(side_effect=[{"operation": {"operationId": "server", "operationState": "DONE"}}, response])
    c._get = AsyncMock()
    await mesh_request(c)
    await c._poll_operations("network")
    await c._poll_operations("network")
    assert phase(c._operations["network"][-1]) == expected
    assert c._request.call_count == 2 and not c._mesh_requests


@pytest.mark.asyncio
async def test_concurrent_server_readbacks_cannot_send_the_mesh_client_twice():
    c = client()
    release = asyncio.Event()
    c._request = AsyncMock(side_effect=[{"operation": {"operationId": "server", "operationState": "CREATED"}},
                                        {"operation": {"operationId": "client", "operationState": "CREATED"}}])
    calls = 0

    async def status(*args):
        nonlocal calls
        calls += 1
        if calls == 1:
            await release.wait()
        return {"operationState": "DONE"}

    c._get = AsyncMock(side_effect=status)
    await mesh_request(c)
    slow = asyncio.create_task(c._poll_operations("network"))
    await asyncio.sleep(0)
    await c._poll_operations("network")
    release.set()
    await slow
    assert c._request.call_count == 2 and phase(c._operations["network"][-1]) == "accepted"
