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
