"""Transport and failure tests use dummy credentials and simulated endpoints."""

import asyncio
import time
from unittest.mock import AsyncMock, Mock

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer
from gwi_test import api


@pytest.mark.asyncio
async def test_http_errors_are_sanitized_and_redirects_not_followed():
    hits = []

    async def handler(request):
        hits.append(request.path)
        if request.path == "/redirect":
            raise web.HTTPFound("/credential-leak")
        return web.Response(status=401, text="secret-should-never-appear")

    app = web.Application()
    app.router.add_get("/{path:.*}", handler)
    async with TestServer(app) as server, aiohttp.ClientSession() as session:
        with pytest.raises(api.AuthError) as error:
            await api.json_get(session, str(server.make_url("/unauthorized")))
        assert "secret" not in str(error.value)
        with pytest.raises(api.ApiError):
            await api.json_get(
                session, str(server.make_url("/redirect")), {"Authorization": "dummy"}
            )
        assert "/credential-leak" not in hits


@pytest.mark.asyncio
async def test_oversized_chunked_response_rejected(monkeypatch):
    monkeypatch.setattr(api, "MAX_RESPONSE", 100)

    async def handler(request):
        response = web.StreamResponse()
        await response.prepare(request)
        await response.write(b"x" * 101)
        await response.write_eof()
        return response

    app = web.Application()
    app.router.add_get("/", handler)
    async with TestServer(app) as server, aiohttp.ClientSession() as session:
        with pytest.raises(api.ApiError, match="too large"):
            await api.json_get(session, str(server.make_url("/")))


@pytest.mark.asyncio
async def test_cloud_poll_only_reads_data_and_refreshes_expired_token_once(monkeypatch):
    calls, auth_calls = [], []

    async def executor(function, *args):
        auth_calls.append(args)
        return {"Auth": "old" if len(auth_calls) == 1 else "new"}

    async def handler(request):
        calls.append(
            (request.method, request.path, request.headers.get("Authorization"))
        )
        if request.headers.get("Authorization") == "Bearer old":
            return web.Response(status=401)
        if request.path == "/groups":
            return web.json_response({"groups": [{"id": "home", "accessPoints": []}]})
        if request.path.endswith("stations"):
            return web.json_response({"stations": [{"id": "one", "connected": True}]})
        if request.path.endswith("status"):
            return web.json_response({"apStatuses": []})
        return web.Response(status=404)

    app = web.Application()
    app.router.add_route("*", "/{path:.*}", handler)
    async with TestServer(app) as server, aiohttp.ClientSession() as session:
        monkeypatch.setattr(api, "CLOUD_URL", str(server.make_url("/")))
        client = api.CloudClient(
            session, executor, "test@example.invalid", "dummy", "0" * 16
        )
        result = await client.snapshot()
        assert result["networks"]["home"]["connected_clients"] == 1
        assert result["networks"]["home"]["download_mbps"] is None
        assert len(auth_calls) == 2
        assert all(call[0] == "GET" or (call[0] == "POST" and call[1].endswith("stations/operations/sensitiveInfo")) for call in calls)
        assert not any("reboot" in call[1] or "wanSpeedTest" in call[1] for call in calls)
        assert all(call[0] == "GET" for call in calls if "speedTestResults" in call[1])


@pytest.mark.asyncio
async def test_missing_client_payload_fails_instead_of_zero():
    client = api.CloudClient(None, None, "test@example.invalid", "dummy", "0" * 16)
    client._get = AsyncMock(side_effect=[{"groups": [{"id": "home"}]}, {}, {}])
    with pytest.raises(api.ApiError, match="client list"):
        await client.snapshot()


@pytest.mark.asyncio
async def test_rate_limit_prevents_repeated_network_calls():
    client = api.CloudClient(None, None, "test@example.invalid", "dummy", "0" * 16)
    client._get = AsyncMock(side_effect=api.RateLimitError(300))
    with pytest.raises(api.RateLimitError):
        await client.snapshot()
    assert client._retry_until > time.monotonic() + 290


@pytest.mark.asyncio
async def test_partial_local_failure_preserves_available_point(monkeypatch):
    async def fake_get(session, url):
        if "192.168.50.133" in url:
            raise api.ApiError("unreachable")
        return {"system": {"groupRole": "root"}, "wan": {"online": True}}

    monkeypatch.setattr(api, "json_get", fake_get)
    client = api.LocalClient(
        None,
        [
            {"name": "Sala", "host": "192.168.50.1"},
            {"name": "Quarto", "host": "192.168.50.133"},
        ],
    )
    result = await client.snapshot()
    assert result["networks"]["local"]["points"]["192.168.50.1"]["online"] is True
    assert result["networks"]["local"]["points"]["192.168.50.133"]["online"] is None
    assert result["networks"]["local"]["connected_clients"] is None


def test_auth_request_timeout_and_secret_safe_failure(monkeypatch):
    session = Mock()
    session.__enter__ = Mock(return_value=session)
    session.__exit__ = Mock(return_value=False)
    session.post.return_value.status_code = 403
    session.post.return_value.text = "Error=BadAuthentication\nInfo=very-secret"
    monkeypatch.setattr(api.requests, "Session", Mock(return_value=session))
    with pytest.raises(api.AuthError) as error:
        api.google_auth("test@example.invalid", "dummy-token", "0" * 16)
    assert "very-secret" not in str(error.value)
    assert session.post.call_args.kwargs["timeout"] == (10, 30)
    assert session.post.call_args.kwargs["allow_redirects"] is False


@pytest.mark.asyncio
async def test_parallel_auth_requests_mint_once():
    executor = AsyncMock(return_value={"Auth": "dummy"})
    client = api.CloudClient(None, executor, "test@example.invalid", "dummy", "0" * 16)
    await asyncio.gather(client._authenticate(), client._authenticate())
    assert executor.call_count == 1


@pytest.mark.asyncio
async def test_mac_read_is_cached_bound_to_requested_stations_and_retries_denials():
    client = api.CloudClient(None, None, "test@example.invalid", "dummy", "0" * 16)
    client._request = AsyncMock(return_value={"operation": {"operationId": "read"}})
    client._get = AsyncMock(side_effect=[
        {"operationState": "DONE"},
        {"stationSensitiveInfos": [
            {"stationId": "one", "macAddress": "aabbccddeeff"},
            {"stationId": "other", "macAddress": "11:22:33:44:55:66"},
        ]},
    ])
    stations = [{"id": "one", "connected": True}, {"id": "offline", "connected": False}]
    result = await client._station_macs("home", stations)
    assert result == {"one": "aa:bb:cc:dd:ee:ff"}
    assert client._request.call_args.args[0] == "POST"
    assert client._request.call_args.args[2] == {"stationIds": ["one"]}
    assert await client._station_macs("home", stations) == result
    assert client._request.call_count == 1
    client._request.side_effect = api.ApiError("Read endpoint returned HTTP 403")
    assert await client._station_macs("other", stations) == {}
    assert await client._station_macs("other", stations) == {}
    assert client._request.call_count == 2


@pytest.mark.asyncio
async def test_mac_lookup_pending_is_bounded_and_rate_limit_propagates(monkeypatch):
    client = api.CloudClient(None, None, "test@example.invalid", "dummy", "0" * 16)
    client._request = AsyncMock(return_value={"operation": {"operationId": "read"}})
    client._get = AsyncMock(return_value={"operationState": "RUNNING"})
    monkeypatch.setattr(api.asyncio, "sleep", AsyncMock())
    assert await client._station_macs("home", [{"id": "one", "connected": True}]) == {}
    assert client._get.call_count == 8
    client._request.side_effect = api.RateLimitError(300)
    with pytest.raises(api.RateLimitError):
        await client._station_macs("other", [{"id": "one", "connected": True}])
