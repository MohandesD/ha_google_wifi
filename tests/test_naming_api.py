"""Verify the exact rename schema, fresh MAC reads and single-attempt writes."""

import time
from unittest.mock import AsyncMock

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer
from gwi_test import api


async def client_for(server, session, monkeypatch):
    monkeypatch.setattr(api, "CLOUD_URL", str(server.make_url("/")))
    client = api.CloudClient(session, AsyncMock(), "fixture@example.invalid", "dummy", "0" * 16)
    client._token, client._expiry = "fictional", time.monotonic() + 3600
    return client


async def test_fresh_identity_lookup_and_exact_put_delete_schema(monkeypatch):
    state, requests = {"name": "Unnamed Device"}, []

    async def handler(request):
        body = await request.json() if request.can_read_body else None
        requests.append((request.method, request.raw_path, body))
        if request.path.endswith("/stations"):
            return web.json_response({"stations": [{"id": "client", "connected": True, "friendlyName": state["name"], "automaticFriendlyName": "Unnamed Device"}]})
        if request.method == "POST":
            assert body == {"stationIds": ["client"]}
            return web.json_response({"operation": {"operationId": "lookup"}})
        if request.path == "/operations/lookup":
            return web.json_response({"operationState": "DONE"})
        if request.path.endswith("/sensitiveInfo"):
            return web.json_response({"stationSensitiveInfos": [{"stationId": "client", "macAddress": "020000000001"}]})
        if request.method == "PUT":
            assert body == {"name": "Example phone"}
            state["name"] = body["name"]
        elif request.method == "DELETE":
            assert body is None
            state["name"] = "Unnamed Device"
        return web.Response(status=204)

    app = web.Application()
    app.router.add_route("*", "/{path:.*}", handler)
    async with TestServer(app) as server, aiohttp.ClientSession() as session:
        client = await client_for(server, session, monkeypatch)
        client._mac_cache["home"] = {"client": ("02:00:00:00:00:99", time.monotonic()+10000)}
        assert (await client.station_identity("home", "client"))["mac"] == "02:00:00:00:00:01"
        assert await client.set_station_name("home", "client", "Example phone") == {}
        assert (await client.station_identity("home", "client"))["name"] == "Example phone"
        await client.set_station_name("home", "client", None)
        assert (await client.station_identity("home", "client"))["name"] == "Unnamed Device"
    writes = [row for row in requests if row[0] in ("PUT", "DELETE")]
    assert writes == [("PUT", "/groups/home/stations/client/stationName?prettyPrint=false", {"name": "Example phone"}),
                      ("DELETE", "/groups/home/stations/client/stationName?prettyPrint=false", None)]


async def test_rename_401_does_not_reauthenticate_and_replay_the_write(monkeypatch):
    writes = []

    async def handler(request):
        writes.append(request.method)
        return web.Response(status=401)

    app = web.Application()
    app.router.add_route("*", "/{path:.*}", handler)
    async with TestServer(app) as server, aiohttp.ClientSession() as session:
        client = await client_for(server, session, monkeypatch)
        auth = AsyncMock()
        monkeypatch.setattr(client, "_authenticate", auth)
        with pytest.raises(api.AuthError):
            await client.set_station_name("home", "client", "Example phone")
        assert writes == ["PUT"] and auth.call_count == 1


@pytest.mark.parametrize("name", ["Example phone", None], ids=["put", "delete"])
async def test_disconnection_after_write_never_replays_through_http_client(monkeypatch, name):
    writes, middleware_calls = [], []

    async def existing_middleware(request, handler):
        middleware_calls.append(request.method)
        return await handler(request)

    async def handler(request):
        if request.path == "/ping":
            return web.json_response({"reachable": True})
        body = await request.json() if request.can_read_body else None
        writes.append((request.method, body))
        request.transport.close()  # Request received; the client gets no acknowledgement.
        return web.Response(status=204)

    app = web.Application()
    app.router.add_route("*", "/{path:.*}", handler)
    async with TestServer(app) as server, aiohttp.ClientSession(middlewares=(existing_middleware,)) as session:
        client = await client_for(server, session, monkeypatch)
        assert await client._get("ping") == {"reachable": True}
        with pytest.raises(api.ApiError, match="unconfirmed"):
            await client.set_station_name("home", "client", name)
        assert writes == [("DELETE", None) if name is None else ("PUT", {"name": name})]
        assert middleware_calls == ["GET", "DELETE" if name is None else "PUT"]
        assert await client._get("ping") == {"reachable": True}


@pytest.mark.parametrize("failure", ["stations", "duplicate", "offline", "operation", "malformed-operation", "failed", "pending", "mac", "duplicate-mac"], ids=str)
async def test_unverified_station_or_mac_blocks_identity(monkeypatch, failure):
    monkeypatch.setattr(api.asyncio, "sleep", AsyncMock())

    async def handler(request):
        if request.path.endswith("/stations"):
            if failure == "stations":
                return web.json_response({})
            row = {"id": "client", "connected": failure != "offline", "friendlyName": "Unnamed Device"}
            return web.json_response({"stations": [row, row] if failure == "duplicate" else [row]})
        if request.method == "POST":
            if failure == "malformed-operation":
                return web.json_response({"operation": "unexpected"})
            return web.json_response({} if failure == "operation" else {"operation": {"operationId": "lookup"}})
        if request.path.endswith("/sensitiveInfo"):
            row = {"stationId": "client", "macAddress": "02:00:00:00:00:01"}
            return web.json_response({"stationSensitiveInfos": [row, row] if failure == "duplicate-mac" else []})
        return web.json_response({"operationState": "FAILED" if failure == "failed" else "RUNNING" if failure == "pending" else "DONE"})

    app = web.Application()
    app.router.add_route("*", "/{path:.*}", handler)
    async with TestServer(app) as server, aiohttp.ClientSession() as session:
        client = await client_for(server, session, monkeypatch)
        with pytest.raises(api.ApiError):
            await client.station_identity("home", "client")


async def test_path_ids_are_encoded_and_names_never_enter_urls(monkeypatch):
    client = api.CloudClient(None, None, "fixture@example.invalid", "dummy", "0"*16)
    request = AsyncMock(return_value={})
    monkeypatch.setattr(client, "_request", request)
    await client.set_station_name("home/other", "client?other", "Example phone")
    assert request.call_args.args == ("PUT", "groups/home%2Fother/stations/client%3Fother/stationName?prettyPrint=false", {"name": "Example phone"})
    assert request.call_args.kwargs == {"retry_auth": False}
