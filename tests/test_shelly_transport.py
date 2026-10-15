"""Exercise the real RPC transport against loopback servers only."""

import json

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer
from gwi_test.shelly_radio import MAX_RESPONSE, ShellyRadio
from homeassistant.exceptions import HomeAssistantError


async def test_rpc_read_and_narrow_write_use_bounded_requests():
    calls = []

    async def handler(request):
        calls.append((request.method, request.path, await request.json() if request.method == "POST" else None))
        return web.json_response({"result": {"ok": True}} if request.method == "POST" else {"rssi": -60})

    app = web.Application()
    app.router.add_route("*", "/{path:.*}", handler)
    async with TestServer(app) as server, aiohttp.ClientSession() as session:
        radio = ShellyRadio(session)
        host = str(server.make_url("/")).removeprefix("http://").rstrip("/")
        assert await radio._rpc(host, "WiFi.GetStatus") == {"rssi": -60}
        params = {"config": {"roam": {"rssi_thr": -70}}}
        assert await radio._rpc(host, "WiFi.SetConfig", params) == {"ok": True}
        assert calls == [("GET", "/rpc/WiFi.GetStatus", None),
                         ("POST", "/rpc", {"id": 1, "method": "WiFi.SetConfig", "params": params})]


@pytest.mark.parametrize("status,payload,write,message", [
    (401, {"private": "fixture-secret"}, False, "unavailable"),
    (500, {"private": "fixture-secret"}, False, "unavailable"),
    (200, {"error": {"message": "fixture-secret"}}, False, "rejected"),
    (200, [], False, "rejected"),
    (200, {"result": []}, True, "Unexpected"),
    (200, "not-json fixture-secret", False, "Cannot communicate"),
    (200, "x" * (MAX_RESPONSE + 1), False, "too large"),
], ids=["authentication", "server-error", "rpc-error", "non-object", "invalid-result", "invalid-json", "oversized"])
async def test_rpc_rejects_provider_errors_and_large_or_invalid_responses(status, payload, write, message):
    async def handler(request):
        return web.Response(status=status, text=payload if isinstance(payload, str) else json.dumps(payload))

    app = web.Application()
    app.router.add_route("*", "/{path:.*}", handler)
    async with TestServer(app) as server, aiohttp.ClientSession() as session:
        radio = ShellyRadio(session)
        host = str(server.make_url("/")).removeprefix("http://").rstrip("/")
        with pytest.raises(HomeAssistantError, match=message) as error:
            await radio._rpc(host, "WiFi.SetConfig" if write else "WiFi.GetStatus",
                             {"config": {"roam": {"interval": 60}}} if write else None)
        assert "fixture-secret" not in str(error.value)


@pytest.mark.parametrize("method,params", [
    ("Shelly.Reboot", None),
    ("WiFi.SetConfig", {"config": {"sta": {"ssid": "example"}}}),
    ("WiFi.SetConfig", {"config": {"roam": {"interval": 60}, "sta": {}}}),
    ("WiFi.SetConfig", {"config": {"roam": {"unknown": 1}}}),
])
async def test_rpc_rejects_other_commands_before_attempting_http(method, params):
    with pytest.raises(HomeAssistantError):
        await ShellyRadio(None)._rpc("unused.example.invalid", method, params)


async def test_identity_check_rejects_authenticated_device_before_reading_settings():
    from unittest.mock import AsyncMock

    radio = ShellyRadio(None)
    radio._rpc = AsyncMock(return_value={"mac": "aabbccddeeff", "gen": 3, "auth_en": True})
    with pytest.raises(HomeAssistantError, match="authentication"):
        await radio._read("unused.example.invalid", "aa:bb:cc:dd:ee:ff")
    radio._rpc.assert_awaited_once_with("unused.example.invalid", "Shelly.GetDeviceInfo")
