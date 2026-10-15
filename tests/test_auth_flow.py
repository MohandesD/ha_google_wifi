"""Exercise the guided setup and renewal in a real isolated HA framework."""

import json
import re
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from homeassistant import config_entries
from test_ha import DOMAIN
from test_ha import real_hass as real_hass

EMAIL = "account@example.invalid"
COOKIE = "oauth2_4/fictional-browser-value"
MASTER = "aas_et/fictional-master-value"
ANDROID = "1" * 16


async def start_credentials(hass, step="cloud_cookie"):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "cloud"})
    assert result["type"] == "menu"
    assert result["menu_options"] == ["cloud_cookie", "cloud_master"]
    return await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": step})


@pytest.fixture
def fake_google(monkeypatch):
    from custom_components.google_wifi_insights import config_flow
    from custom_components.google_wifi_insights.api import CloudClient

    exchange = lambda *args: {"Token": MASTER}
    monkeypatch.setattr(config_flow, "google_auth", exchange)
    validate = AsyncMock(return_value=1)
    monkeypatch.setattr(CloudClient, "async_validate_account", validate)
    monkeypatch.setattr(CloudClient, "snapshot", AsyncMock(return_value={"networks": {}}))
    return validate


@pytest.mark.asyncio
async def test_cookie_setup_hides_android_id_and_stores_only_the_exchanged_token(real_hass, fake_google, monkeypatch):
    from custom_components.google_wifi_insights import config_flow

    exchanges = []
    def exchange(email, token, android_id, exchange):
        exchanges.append((email, token, android_id, exchange))
        return {"Token": MASTER}
    monkeypatch.setattr(config_flow, "google_auth", exchange)
    form = await start_credentials(real_hass)
    assert {str(key) for key in form["data_schema"].schema} == {"email", "oauth_token"}
    result = await real_hass.config_entries.flow.async_configure(
        form["flow_id"], {"email": " Account@Example.invalid ", "oauth_token": f'"{COOKIE}"'}
    )
    assert result["type"] == "create_entry"
    entry = result["result"]
    assert entry.data["email"] == EMAIL and entry.data["master_token"] == MASTER
    assert re.fullmatch(r"[a-f0-9]{16}", entry.data["android_id"])
    assert exchanges == [(EMAIL, COOKIE, entry.data["android_id"], True)]
    assert COOKIE not in json.dumps(dict(entry.data))
    await real_hass.async_block_till_done()
    assert await real_hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.asyncio
async def test_retry_reuses_the_exchange_and_never_returns_credentials_in_the_form(real_hass, fake_google, monkeypatch):
    from custom_components.google_wifi_insights import config_flow
    from custom_components.google_wifi_insights.api import ApiError

    calls = []
    def exchange(*args):
        calls.append(args)
        return {"Token": MASTER}
    monkeypatch.setattr(config_flow, "google_auth", exchange)
    fake_google.side_effect = [ApiError("Temporary network failure"), 1]
    form = await start_credentials(real_hass)
    retry = await real_hass.config_entries.flow.async_configure(form["flow_id"], {"email": EMAIL, "oauth_token": COOKIE})
    assert retry["step_id"] == "cloud_retry" and retry["errors"] == {"base": "cannot_connect"}
    assert set(str(key) for key in retry["data_schema"].schema) == {"new_token"}
    assert COOKIE not in repr(retry) and MASTER not in repr(retry)
    result = await real_hass.config_entries.flow.async_configure(retry["flow_id"], {})
    assert result["type"] == "create_entry" and len(calls) == 1
    await real_hass.async_block_till_done()
    assert await real_hass.config_entries.async_unload(result["result"].entry_id)


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_error,expected", [
    ("challenge", "google_challenge"), ("rejected", "invalid_auth"),
    ("outage", "auth_unavailable"), ("limit", "rate_limited"),
])
async def test_exchange_failure_has_specific_errors_and_no_password_default(real_hass, fake_google, monkeypatch, provider_error, expected):
    from custom_components.google_wifi_insights import config_flow
    from custom_components.google_wifi_insights.api import (
        AuthError,
        AuthServiceError,
        RateLimitError,
    )

    errors = {"challenge": AuthError(reason="google_challenge"), "rejected": AuthError(), "outage": AuthServiceError("Outage"), "limit": RateLimitError()}
    def exchange(*args):
        raise errors[provider_error]
    monkeypatch.setattr(config_flow, "google_auth", exchange)
    form = await start_credentials(real_hass)
    result = await real_hass.config_entries.flow.async_configure(form["flow_id"], {"email": EMAIL, "oauth_token": COOKIE})
    assert result["step_id"] == "cloud_cookie" and result["errors"] == {"base": expected}
    assert COOKIE not in repr(result) and MASTER not in repr(result)
    fake_google.assert_not_awaited()


@pytest.mark.asyncio
async def test_wrong_service_and_method_are_caught_before_contacting_google(real_hass, fake_google):
    form = await start_credentials(real_hass)
    result = await real_hass.config_entries.flow.async_configure(form["flow_id"], {"email": EMAIL, "oauth_token": "eyJfake.payload.signature"})
    assert result["errors"] == {"oauth_token": "wrong_service_token"}
    result = await real_hass.config_entries.flow.async_configure(form["flow_id"], {"email": EMAIL, "oauth_token": MASTER})
    assert result["step_id"] == "cloud_master" and "android_id" in result["data_schema"].schema
    assert result["errors"] == {"oauth_token": "wrong_token_type"}
    fake_google.assert_not_awaited()


@pytest.mark.asyncio
async def test_network_access_errors_keep_the_reusable_token_until_reset(real_hass, fake_google):
    from custom_components.google_wifi_insights.api import ApiError, NoNetworksError

    fake_google.side_effect = NoNetworksError("No networks")
    form = await start_credentials(real_hass, "cloud_master")
    result = await real_hass.config_entries.flow.async_configure(form["flow_id"], {"email": EMAIL, "oauth_token": MASTER, "android_id": ANDROID})
    assert result["errors"] == {"base": "no_networks"}
    fake_google.side_effect = ApiError("Denied", status=403)
    result = await real_hass.config_entries.flow.async_configure(form["flow_id"], {})
    assert result["errors"] == {"base": "account_access"}
    result = await real_hass.config_entries.flow.async_configure(form["flow_id"], {"new_token": True})
    assert result["step_id"] == "cloud" and result["type"] == "menu"
    result = await real_hass.config_entries.flow.async_configure(form["flow_id"], {"next_step_id": "cloud_cookie"})
    assert MASTER not in repr(result)


@pytest.mark.asyncio
async def test_bad_field_pastes_and_rejected_pending_auth_are_not_reflected(real_hass, fake_google):
    from custom_components.google_wifi_insights.api import AuthError

    form = await start_credentials(real_hass, "cloud_master")
    result = await real_hass.config_entries.flow.async_configure(form["flow_id"], {"email": COOKIE, "oauth_token": MASTER, "android_id": ANDROID})
    assert result["errors"] == {"email": "invalid_email"} and COOKIE not in repr(result)
    result = await real_hass.config_entries.flow.async_configure(form["flow_id"], {"email": EMAIL, "oauth_token": MASTER, "android_id": COOKIE})
    assert result["errors"] == {"android_id": "invalid_android_id"} and COOKIE not in repr(result)
    fake_google.side_effect = AuthError()
    result = await real_hass.config_entries.flow.async_configure(form["flow_id"], {"email": EMAIL, "oauth_token": MASTER, "android_id": ANDROID})
    assert result["step_id"] == "cloud_master" and result["errors"] == {"base": "invalid_auth"}
    assert MASTER not in repr(result)


@pytest.mark.asyncio
async def test_duplicate_account_is_detected_before_consuming_another_cookie(real_hass, fake_google, monkeypatch):
    from custom_components.google_wifi_insights import config_flow

    calls = []
    def exchange(*args):
        calls.append(args)
        return {"Token": MASTER}
    monkeypatch.setattr(config_flow, "google_auth", exchange)
    form = await start_credentials(real_hass)
    result = await real_hass.config_entries.flow.async_configure(form["flow_id"], {"email": EMAIL, "oauth_token": COOKIE})
    await real_hass.async_block_till_done()
    other = await start_credentials(real_hass)
    duplicate = await real_hass.config_entries.flow.async_configure(other["flow_id"], {"email": EMAIL, "oauth_token": COOKIE})
    assert duplicate["type"] == "abort" and duplicate["reason"] == "already_configured"
    assert len(calls) == 1
    assert await real_hass.config_entries.async_unload(result["result"].entry_id)


@pytest.mark.asyncio
async def test_options_open_native_reauth_preserving_entry_devices_and_options(real_hass, fake_google):
    from unittest.mock import patch

    from homeassistant.helpers import device_registry

    from custom_components.google_wifi_insights.api import CloudClient
    from custom_components.google_wifi_insights.model import cloud_network

    snapshot = {"networks": {"network": cloud_network(
        {"accessPoints": [{"id": "point"}]},
        {"apStatuses": [{"apId": "point", "apState": "AP_ONLINE"}]},
        [{"id": "client", "friendlyName": "Test client", "connected": True, "apId": "point"}],
        {},
    )}}
    with patch.object(CloudClient, "snapshot", AsyncMock(return_value=snapshot)):
        await _check_renewal_preserves_registry(real_hass, fake_google, device_registry)


async def _check_renewal_preserves_registry(real_hass, fake_google, device_registry):
    form = await start_credentials(real_hass, "cloud_master")
    result = await real_hass.config_entries.flow.async_configure(form["flow_id"], {"email": EMAIL, "oauth_token": MASTER, "android_id": ANDROID})
    entry = result["result"]
    await real_hass.async_block_till_done()
    real_hass.config_entries.async_update_entry(entry, options={"scan_interval": 300})
    await real_hass.async_block_till_done()
    original_entry_id, original_unique_id = entry.entry_id, entry.unique_id
    original_states = {state.entity_id for state in real_hass.states.async_all()}
    assert len(original_states) > 10
    registry = device_registry.async_get(real_hass)
    original_devices = {device.id for device in device_registry.async_entries_for_config_entry(registry, entry.entry_id)}
    assert len(original_devices) == 3
    options = await real_hass.config_entries.options.async_init(entry.entry_id)
    assert options["menu_options"] == ["polling", "controls", "renew_auth"]
    result = await real_hass.config_entries.options.async_configure(options["flow_id"], {"next_step_id": "renew_auth"})
    assert result["data"] is None and result["next_flow"][0] == config_entries.FlowType.CONFIG_FLOW
    assert entry.options == {"scan_interval": 300}
    reauth_id = result["next_flow"][1]
    another = await real_hass.config_entries.options.async_init(entry.entry_id)
    duplicate = await real_hass.config_entries.options.async_configure(another["flow_id"], {"next_step_id": "renew_auth"})
    assert duplicate["next_flow"][1] == reauth_id
    form = await real_hass.config_entries.flow.async_configure(reauth_id, {"next_step_id": "cloud_cookie"})
    mismatch = await real_hass.config_entries.flow.async_configure(reauth_id, {"email": "other@example.invalid", "oauth_token": COOKIE})
    assert mismatch["errors"] == {"base": "account_mismatch"}
    from custom_components.google_wifi_insights.api import AuthError
    fake_google.side_effect = AuthError()
    rejected = await real_hass.config_entries.flow.async_configure(reauth_id, {"email": EMAIL, "oauth_token": COOKIE})
    assert rejected["errors"] == {"base": "invalid_auth"}
    assert entry.data["master_token"] == MASTER and entry.options == {"scan_interval": 300}
    fake_google.side_effect = None
    result = await real_hass.config_entries.flow.async_configure(reauth_id, {"email": EMAIL, "oauth_token": COOKIE})
    assert result["type"] == "abort" and result["reason"] == "reauth_successful"
    await real_hass.async_block_till_done()
    assert entry.entry_id == original_entry_id and entry.unique_id == original_unique_id
    assert entry.data["android_id"] == ANDROID and entry.options == {"scan_interval": 300}
    assert len(real_hass.config_entries.async_entries(DOMAIN)) == 1
    assert {state.entity_id for state in real_hass.states.async_all()} == original_states
    assert {device.id for device in device_registry.async_entries_for_config_entry(registry, entry.entry_id)} == original_devices
    assert await real_hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.asyncio
async def test_local_polling_options_continue_to_work_without_google_auth(real_hass, monkeypatch):
    from custom_components.google_wifi_insights.api import LocalClient

    monkeypatch.setattr(LocalClient, "snapshot", AsyncMock(return_value={"networks": {}}))
    result = await real_hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    form = await real_hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "local"})
    result = await real_hass.config_entries.flow.async_configure(form["flow_id"], {"points": "Point=192.168.50.1"})
    entry = result["result"]
    await real_hass.async_block_till_done()
    options = await real_hass.config_entries.options.async_init(entry.entry_id)
    assert options["menu_options"] == ["polling"]
    form = await real_hass.config_entries.options.async_configure(options["flow_id"], {"next_step_id": "polling"})
    result = await real_hass.config_entries.options.async_configure(form["flow_id"], {"scan_interval": 300, "points": "Point=192.168.50.1"})
    assert entry.options == {"scan_interval": 300} and result["type"] == "create_entry"
    await real_hass.async_block_till_done()
    assert await real_hass.config_entries.async_unload(entry.entry_id)


def test_authentication_ui_has_equivalent_english_and_portuguese_keys():
    root = Path(__file__).resolve().parents[1] / "custom_components/google_wifi_insights"
    source = json.loads((root / "strings.json").read_text(encoding="utf-8"))
    english = json.loads((root / "translations/en.json").read_text(encoding="utf-8"))
    portuguese = json.loads((root / "translations/pt.json").read_text(encoding="utf-8"))
    assert source == english
    for section in ("step", "error", "abort"):
        assert source["config"][section].keys() == portuguese["config"][section].keys()
    assert "android_id" not in source["config"]["step"]["cloud_cookie"]["data"]


@pytest.mark.asyncio
@pytest.mark.parametrize("error_name,expected", [
    ("AuthError", "invalid_auth"), ("RateLimitError", "rate_limited"),
    ("AuthServiceError", "auth_unavailable"), ("ApiError", "cannot_connect"),
])
async def test_browser_exchange_failures_do_not_store_or_echo_credentials(real_hass, fake_google, monkeypatch, error_name, expected):
    from unittest.mock import Mock

    from custom_components.google_wifi_insights import api, config_flow

    monkeypatch.setattr(config_flow, "google_auth", Mock(side_effect=getattr(api, error_name)("fixture error")
                        if error_name != "RateLimitError" else api.RateLimitError(120)))
    form = await start_credentials(real_hass)
    result = await real_hass.config_entries.flow.async_configure(form["flow_id"], {"email": EMAIL, "oauth_token": COOKIE})
    assert result["errors"] == {"base": expected}
    assert not real_hass.config_entries.async_entries(DOMAIN)
    assert COOKIE not in str(result)


@pytest.mark.asyncio
@pytest.mark.parametrize("error_name,expected", [("AuthServiceError", "auth_unavailable"), ("NoNetworksError", "no_networks")])
async def test_temporary_discovery_failure_reuses_pending_exchange(real_hass, fake_google, error_name, expected):
    from custom_components.google_wifi_insights import api

    fake_google.side_effect = getattr(api, error_name)("fixture")
    form = await start_credentials(real_hass)
    result = await real_hass.config_entries.flow.async_configure(form["flow_id"], {"email": EMAIL, "oauth_token": COOKIE})
    assert result["step_id"] == "cloud_retry" and result["errors"] == {"base": expected}
    fake_google.side_effect = None
    result = await real_hass.config_entries.flow.async_configure(form["flow_id"], {})
    assert result["type"] == "create_entry"
    await real_hass.async_block_till_done()
    assert await real_hass.config_entries.async_unload(result["result"].entry_id)


@pytest.mark.asyncio
@pytest.mark.parametrize("points", ["Point=8.8.8.8", "Point=169.254.1.2", "Point=192.168.50.1\nOther=192.168.50.1"])
async def test_invalid_local_addresses_never_reach_the_transport(real_hass, monkeypatch, points):
    from custom_components.google_wifi_insights.api import LocalClient

    poll = AsyncMock()
    monkeypatch.setattr(LocalClient, "snapshot", poll)
    flow = await real_hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    form = await real_hass.config_entries.flow.async_configure(flow["flow_id"], {"next_step_id": "local"})
    result = await real_hass.config_entries.flow.async_configure(form["flow_id"], {"points": points})
    assert result["errors"] == {"base": "invalid_points"}
    poll.assert_not_awaited()
