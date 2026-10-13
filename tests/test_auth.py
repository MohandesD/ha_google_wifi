"""Check credential normalization, useful errors and bounded account discovery."""

from unittest.mock import AsyncMock, Mock

import pytest

from gwi_test import api
from gwi_test.auth import CredentialInputError, normalize_email, normalize_google_token


@pytest.mark.parametrize("value", [
    " oauth2_4/fictional-value ",
    '"oauth2_4/fictional-value"',
    "oauth_token=oauth2_4/fictional-value",
    "oauth_token='oauth2_4/fictional-value'",
    "oauth2_4%2Ffictional-value",
])
def test_copy_paste_variants_produce_the_same_cookie_value(value):
    assert normalize_google_token(value, "cookie") == "oauth2_4/fictional-value"


@pytest.mark.parametrize("value,method,reason", [
    ("oauth2_4/", "cookie", "invalid_token"),
    ("aas_et/", "master", "invalid_token"),
    ("oauth2_4/has\nnewline", "cookie", "invalid_token"),
    ("oauth2_4/has%0Anewline", "cookie", "invalid_token"),
    ("oauth_token=oauth2_4/value; another=secret", "cookie", "invalid_token"),
    ("oauth2_4/value", "master", "wrong_token_type"),
    ("aas_et/value", "cookie", "wrong_token_type"),
    ("eyJfake.payload.signature", "cookie", "wrong_service_token"),
])
def test_invalid_credentials_report_only_a_fixed_error_key(value, method, reason):
    with pytest.raises(CredentialInputError) as error:
        normalize_google_token(value, method)
    assert str(error.value) == reason


def test_email_normalization_and_master_token_support():
    assert normalize_email(" Account@Example.invalid ") == "account@example.invalid"
    assert normalize_google_token("oauth2rt_1/fictional-value", "master") == "oauth2rt_1/fictional-value"
    with pytest.raises(CredentialInputError, match="invalid_email"):
        normalize_email("two @example.invalid")


@pytest.mark.parametrize("status,body,expected,reason", [
    (200, "Error=NeedsBrowser\nUrl=https://untrusted.invalid/secret\n", api.AuthError, "google_challenge"),
    (403, "Error=BadAuthentication\nInfo=secret\n", api.AuthError, "invalid_auth"),
    (200, "Error=UnrecognizedProviderReason\nInfo=secret\n", api.AuthError, "invalid_auth"),
    (200, "Error=ServiceUnavailable\n", api.AuthServiceError, None),
    (503, "temporary failure with secret", api.AuthServiceError, None),
    (429, "slow down with secret", api.RateLimitError, None),
    (200, "<html>unexpected response with secret</html>", api.ApiError, None),
])
def test_google_errors_are_classified_without_exposing_provider_details(monkeypatch, status, body, expected, reason):
    session = Mock()
    session.__enter__ = Mock(return_value=session)
    session.__exit__ = Mock(return_value=False)
    session.post.return_value.status_code = status
    session.post.return_value.text = body
    session.post.return_value.headers = {"Retry-After": "120"}
    monkeypatch.setattr(api.requests, "Session", Mock(return_value=session))
    with pytest.raises(expected) as error:
        api.google_auth("test@example.invalid", "fictional-value", "0" * 16)
    assert "secret" not in str(error.value) and "untrusted" not in str(error.value)
    if reason:
        assert error.value.reason == reason
    if status == 429:
        assert error.value.retry_after == 120


@pytest.mark.asyncio
async def test_setup_checks_network_discovery_without_optional_metrics():
    client = api.CloudClient(None, None, "test@example.invalid", "dummy", "0" * 16)
    client._get = AsyncMock(return_value={"groups": [{"id": "network"}, {}, None]})
    client.snapshot = AsyncMock()
    assert await client.async_validate_account() == 1
    client._get.assert_awaited_once_with("groups?prettyPrint=false")
    client.snapshot.assert_not_awaited()
    client._get.return_value = {"groups": []}
    with pytest.raises(api.NoNetworksError):
        await client.async_validate_account()
    client._get.return_value = {}
    with pytest.raises(api.ApiError):
        await client.async_validate_account()
