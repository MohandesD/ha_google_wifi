"""Partial cloud failures, recovery, cancellation and safe diagnostic exports."""

import asyncio
import copy
import json
import time

import pytest
from gwi_test import api
from gwi_test.diagnostics import diagnostic_capabilities
from gwi_test.radio_schema import radio_schema


def cloud_client(groups=("first", "second"), failures=None):
    """Return a transport fixture that cannot send a real HTTP request."""
    client = api.CloudClient(None, None, "tester@example.invalid", "fictional", "0" * 16)
    failures = failures if failures is not None else {}

    async def get(path):
        if path == "groups?prettyPrint=false":
            return {"groups": [{"id": group, "accessPoints": []} for group in groups]}
        if path.endswith("/status?prettyPrint=false"):
            group = path.split("/")[1]
            if group in failures:
                raise failures[group]
            return {"apStatuses": []}
        if path.endswith("/stations?prettyPrint=false"):
            return {"stations": []}
        raise api.ApiError("Optional fixture endpoint unavailable", status=404)

    client._get = get
    return client


@pytest.mark.parametrize("failed_group", ["first", "second"])
@pytest.mark.parametrize("status", [403, 404, 500, None])
async def test_one_failed_network_does_not_discard_an_accessible_network(failed_group, status):
    client = cloud_client(failures={failed_group: api.ApiError("Fixture failure", status)})
    result = await client.snapshot()
    assert set(result["networks"]) == ({"first", "second"} - {failed_group})
    assert result["network_errors"] == {failed_group: {
        "state": "denied" if status in (403, 404) else "unavailable", "http_status": status,
    }}


async def test_recovery_clears_partial_errors_and_never_relabels_old_data():
    failures = {"first": api.ApiError("Denied", 403)}
    client = cloud_client(failures=failures)
    assert set((await client.snapshot())["networks"]) == {"second"}
    failures.clear()
    recovered = await client.snapshot()
    assert set(recovered["networks"]) == {"first", "second"}
    assert recovered["network_errors"] == client.network_errors == {}


async def test_all_networks_failing_is_a_failed_poll_not_an_empty_healthy_network():
    client = cloud_client(failures={key: api.ApiError("Fixture unavailable", 500) for key in ("first", "second")})
    with pytest.raises(api.ApiError):
        await client.snapshot()
    assert set(client.network_errors) == {"first", "second"}


@pytest.mark.parametrize("failure", [api.AuthError(), api.RateLimitError(120), asyncio.CancelledError()])
async def test_account_authentication_throttling_and_cancellation_are_not_swallowed(failure):
    client = cloud_client(failures={"second": failure})
    with pytest.raises(type(failure)):
        await client.snapshot()
    if isinstance(failure, api.RateLimitError):
        assert client._retry_until > time.monotonic() + 100


async def test_changed_schema_is_isolated_without_echoing_provider_data(monkeypatch):
    client = cloud_client()
    original = client._snapshot_network

    async def malformed(group, group_id):
        if group_id == "first":
            raise TypeError("private provider payload must never appear")
        return await original(group, group_id)

    monkeypatch.setattr(client, "_snapshot_network", malformed)
    result = await client.snapshot()
    assert set(result["networks"]) == {"second"}
    assert result["network_errors"] == {"first": {"state": "invalid_response", "http_status": None}}
    assert "private provider" not in json.dumps(result, default=str)


def test_diagnostic_capabilities_remove_identifiers_from_keys_and_values():
    private = "aabbccddeeff00112233445566778899"
    capabilities = {
        "reads": {
            "hardware:" + private: {"state": "available", "stale": False, "ap_id": private,
                                    "retrieved_at": "2026-10-15T12:00:00Z"},
            "notes:123.4.5": {"state": "denied", "http_status": 403, "stale": True},
            "stations": {"state": "available", "token": "aas_et/fictional-secret", "email": "private@example.invalid"},
            private: {"state": "available"},
        },
        "actions": {"restart_point": {"state": "accepted", "target": private}, private: {"state": "accepted"}},
        "other": {"account": "private@example.invalid"},
    }
    original = copy.deepcopy(capabilities)
    result = diagnostic_capabilities(capabilities)
    encoded = json.dumps(result)
    for value in (private, "aas_et/", "private@example.invalid", "123.4.5"):
        assert value not in encoded
    assert result["reads"]["hardware"][0]["state"] == "available"
    assert result["reads"]["firmware_notes"][0]["http_status"] == 403
    assert result["actions"]["restart_point"]["target"] == "point"
    assert capabilities == original


async def test_invalid_provider_name_is_isolated_before_entering_the_ha_registry():
    client = cloud_client()
    original = client._get

    async def malformed(path):
        result = await original(path)
        if path == "groups?prettyPrint=false":
            result["groups"][0]["name"] = {"not": "a device name"}
        return result

    client._get = malformed
    result = await client.snapshot()
    assert set(result["networks"]) == {"second"}
    assert result["network_errors"]["first"]["state"] == "unavailable"


def test_radio_field_evidence_does_not_expose_hexadecimal_identity_keys():
    identity = "aabbccddeeff00112233445566778899"
    encoded = json.dumps(radio_schema({identity: {"rssi": -60}, "devices": {"aa:bb:cc:dd:ee:ff": {"channel": 6}}}))
    assert identity not in encoded
    assert "aa:bb:cc:dd:ee:ff" not in encoded
    assert "-60" in encoded
