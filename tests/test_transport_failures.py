"""Bounded authentication and HTTP failures never echo or resend secrets."""

from unittest.mock import MagicMock

import aiohttp
import pytest
import requests
from aiohttp import web
from aiohttp.test_utils import TestServer
from gwi_test import api
from gwi_test.auth import CredentialInputError, normalize_google_token


@pytest.mark.parametrize("status,text,error", [
    (500, "fictional-secret", api.AuthServiceError),
    (400, "fictional-secret", api.ApiError),
    (200, "x" * 65537, api.ApiError),
    (200, "SID=fictional-secret", api.ApiError),
], ids=["provider-outage", "unexpected-status", "oversized-auth-response", "incomplete-auth-response"])
def test_auth_response_failures_are_fixed_safe_errors(monkeypatch, status, text, error):
    session = MagicMock()
    session.__enter__.return_value = session
    session.post.return_value = MagicMock(status_code=status, text=text, headers={})
    monkeypatch.setattr(api.requests, "Session", lambda: session)
    with pytest.raises(error) as result:
        api.google_auth("tester@example.invalid", "fictional-secret", "0" * 16)
    assert "fictional-secret" not in str(result.value)
    assert session.post.call_args.kwargs["verify"] is True
    assert session.post.call_args.kwargs["allow_redirects"] is False


@pytest.mark.parametrize("retry,expected", [("90", 90), ("1", 60), ("99999", 3600), ("tomorrow", 300)])
def test_auth_throttling_uses_a_bounded_retry_interval(monkeypatch, retry, expected):
    session = MagicMock()
    session.__enter__.return_value = session
    session.post.return_value = MagicMock(status_code=429, text="", headers={"Retry-After": retry})
    monkeypatch.setattr(api.requests, "Session", lambda: session)
    with pytest.raises(api.RateLimitError) as result:
        api.google_auth("tester@example.invalid", "fictional", "0" * 16)
    assert result.value.retry_after == expected


def test_auth_connection_failure_is_not_a_credential_rejection(monkeypatch):
    session = MagicMock()
    session.__enter__.return_value = session
    session.post.side_effect = requests.Timeout("fictional-secret")
    monkeypatch.setattr(api.requests, "Session", lambda: session)
    with pytest.raises(api.AuthServiceError) as result:
        api.google_auth("tester@example.invalid", "fictional-secret", "0" * 16)
    assert "fictional-secret" not in str(result.value)


@pytest.mark.parametrize("body", ["invalid-json fictional-secret", "[]", "null", "true"])
async def test_non_object_http_responses_do_not_become_measurements(body):
    async def handler(request):
        return web.Response(text=body)

    app = web.Application()
    app.router.add_get("/", handler)
    async with TestServer(app) as server, aiohttp.ClientSession() as session:
        with pytest.raises(api.ApiError) as result:
            await api.json_get(session, str(server.make_url("/")))
        assert "fictional-secret" not in str(result.value)


async def test_http_redirect_is_not_followed_with_an_authorization_header():
    paths = []

    async def handler(request):
        paths.append(request.path)
        if request.path == "/start":
            raise web.HTTPFound("/must-not-receive-auth")
        return web.json_response({})

    app = web.Application()
    app.router.add_get("/{path:.*}", handler)
    async with TestServer(app) as server, aiohttp.ClientSession() as session:
        with pytest.raises(api.ApiError, match="HTTP 302"):
            await api.json_get(session, str(server.make_url("/start")), {"Authorization": "Bearer fictional"})
    assert paths == ["/start"]


async def test_http_throttling_preserves_the_provider_retry_window():
    async def handler(request):
        return web.Response(status=429, headers={"Retry-After": "120"})

    app = web.Application()
    app.router.add_get("/", handler)
    async with TestServer(app) as server, aiohttp.ClientSession() as session:
        with pytest.raises(api.RateLimitError) as result:
            await api.json_get(session, str(server.make_url("/")))
        assert result.value.retry_after == 120


def test_overlong_google_token_is_rejected_locally():
    with pytest.raises(CredentialInputError) as result:
        normalize_google_token("oauth2_4/" + "a" * 16384, "cookie")
    assert result.value.reason == "invalid_token"
