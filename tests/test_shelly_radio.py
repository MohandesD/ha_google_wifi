"""Radio controls must preserve network settings and verify physical identity."""
import copy
from unittest.mock import AsyncMock
import pytest
from homeassistant.exceptions import HomeAssistantError
from gwi_test.shelly_radio import ShellyRadio, target

ITEM = {"connected": True, "identity_match": "mac", "mac_address": "aa:bb:cc:dd:ee:ff",
        "ip_address": "192.168.50.2", "ha_manufacturer": "Shelly", "roaming_supported": True}


def transport():
    roam = {"rssi_thr": -80, "interval": 60}
    writes = []
    async def rpc(host, method, params=None):
        if method == "Shelly.GetDeviceInfo":
            return {"mac": "AABBCCDDEEFF", "gen": 4, "auth_en": False}
        if method == "WiFi.GetConfig":
            return {"sta": {"ssid": "private", "pass": "private-password"}, "roam": copy.copy(roam)}
        if method == "WiFi.GetStatus":
            return {"status": "got ip", "rssi": -73, "bssid": "11:22:33:44:55:66", "channel": 6}
        writes.append(params)
        roam.update(params["config"]["roam"])
        return {}
    client = ShellyRadio(None)
    client._rpc = AsyncMock(side_effect=rpc)
    return client, writes, roam


@pytest.mark.asyncio
async def test_controls_read_back_and_never_send_wifi_credentials():
    client, writes, roam = transport()
    measured = await client.set_roaming(ITEM, "rssi_thr", -70)
    assert writes == [{"config": {"roam": {"rssi_thr": -70}}}]
    assert measured["roam_rssi_threshold"] == -70 and measured["rssi"] == -73
    assert measured["rssi_source"] == "shelly_wifi_status" and measured["rssi_observed_at"]
    assert "sta" not in measured and "private-password" not in str(measured)
    await client.set_roaming(ITEM, "interval", 120)
    await client.set_roaming(ITEM, "enabled", False)
    assert roam["interval"] == 0
    await client.set_roaming(ITEM, "enabled", True)
    assert roam["interval"] == 120 and roam["rssi_thr"] == -70


@pytest.mark.asyncio
async def test_dhcp_reassignment_and_unconfirmed_writes_are_rejected():
    client, _, _ = transport()
    client._rpc = AsyncMock(return_value={"mac": "00:11:22:33:44:55", "gen": 4, "auth_en": False})
    with pytest.raises(HomeAssistantError, match="identity"):
        await client.set_roaming(ITEM, "rssi_thr", -70)
    assert [c.args[1] for c in client._rpc.call_args_list] == ["Shelly.GetDeviceInfo"]
    client, _, _ = transport()
    read = client._read
    async def unconfirmed(host, mac):
        result = await read(host, mac)
        return {**result, "roam_rssi_threshold": -80}
    client._read = unconfirmed
    with pytest.raises(HomeAssistantError, match="confirm"):
        await client.set_roaming(ITEM, "rssi_thr", -70)


@pytest.mark.asyncio
async def test_missing_samples_clear_rssi_and_do_not_fail_google_network():
    client, _, _ = transport()
    snapshot = {"networks": {"home": {"clients": {"shelly": copy.deepcopy(ITEM), "other": {"connected": True, "rssi": None}}}}}
    await client.enrich(snapshot)
    assert snapshot["networks"]["home"]["clients_with_signal"] == 1
    client._rpc = AsyncMock(side_effect=HomeAssistantError("Offline"))
    fresh = {"networks": {"home": {"clients": {"shelly": {**ITEM, "rssi": None}}}}}
    await client.enrich(fresh)
    item = fresh["networks"]["home"]["clients"]["shelly"]
    assert item["rssi"] is None and item["radio_available"] is False and item["roaming_supported"] is True
    assert fresh["networks"]["home"]["clients_with_signal"] == 0


@pytest.mark.parametrize("change", [{"ip_address": "8.8.8.8"}, {"ip_address": "127.0.0.1"}, {"ip_address": "169.254.169.254"}, {"identity_match": "ip"}, {"ha_manufacturer": "Other"}, {"connected": False}, {"mac_address": None}])
def test_only_registered_mac_matched_lan_shelly_targets(change):
    assert target({**ITEM, **change}) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("key,value", [("rssi_thr", -20), ("interval", -1), ("interval", 1.5), ("interval", True), ("sta", -70)])
async def test_invalid_control_values_never_send_network_requests(key, value):
    client, _, _ = transport()
    with pytest.raises(HomeAssistantError):
        await client.set_roaming(ITEM, key, value)
    client._rpc.assert_not_awaited()


@pytest.mark.asyncio
async def test_rpc_rejects_a_network_configuration_patch_before_sending():
    client = ShellyRadio(None)
    with pytest.raises(HomeAssistantError, match="Only roaming"):
        await client._rpc("192.168.50.2", "WiFi.SetConfig", {"config": {"sta": {"ssid": "bad"}}})
