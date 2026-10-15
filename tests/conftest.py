"""Import transport/model without pretending to run Home Assistant."""

import sys
import types
from pathlib import Path
from urllib.parse import urlsplit

import aiohttp
import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]
package = types.ModuleType("gwi_test")
package.__path__ = [str(ROOT / "custom_components" / "google_wifi_insights")]
sys.modules["gwi_test"] = package


@pytest.fixture(autouse=True)
def forbid_external_http(monkeypatch):
    """Only in-process loopback test servers may receive real HTTP requests."""
    def check(url):
        if urlsplit(str(url)).hostname not in {"127.0.0.1", "::1", "localhost"}:
            raise AssertionError("External HTTP is forbidden in tests; use a fixture or loopback server")

    original_async = aiohttp.ClientSession._request
    original_sync = requests.sessions.Session.request

    async def local_async(session, method, url, *args, **kwargs):
        check(url)
        return await original_async(session, method, url, *args, **kwargs)

    def local_sync(session, method, url, *args, **kwargs):
        check(url)
        return original_sync(session, method, url, *args, **kwargs)

    monkeypatch.setattr(aiohttp.ClientSession, "_request", local_async)
    monkeypatch.setattr(requests.sessions.Session, "request", local_sync)
