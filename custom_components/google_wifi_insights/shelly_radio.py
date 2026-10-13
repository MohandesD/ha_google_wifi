"""MAC-verified Shelly radio measurements and narrowly scoped roaming controls."""

from __future__ import annotations

import asyncio
import ipaddress
import json
from datetime import UTC, datetime

import aiohttp
from homeassistant.exceptions import HomeAssistantError

from .identity import normalize_mac
from .model import number

MAX_RESPONSE = 128 * 1024
READ_METHODS = {"Shelly.GetDeviceInfo", "WiFi.GetConfig", "WiFi.GetStatus"}


def target(item):
    """Only a registered Shelly with an exact MAC match can be contacted."""
    if item.get("connected") is not True or item.get("identity_match") != "mac":
        return None
    if str(item.get("ha_manufacturer", "")).lower() not in {"shelly", "allterco"}:
        return None
    mac = normalize_mac(item.get("mac_address"))
    try:
        address = ipaddress.ip_address(item.get("ip_address"))
    except ValueError, TypeError:
        return None
    if not mac or address.version != 4 or not address.is_private or any((
        address.is_loopback, address.is_multicast, address.is_unspecified, address.is_reserved, address.is_link_local,
    )):
        return None
    return str(address), mac


class ShellyRadio:
    def __init__(self, session):
        self.session = session
        self._locks = {}
        self._semaphore = asyncio.Semaphore(4)
        self._supported = set()
        self._intervals = {}

    async def _rpc(self, host, method, params=None):
        if method not in READ_METHODS and method != "WiFi.SetConfig":
            raise HomeAssistantError("Unsupported radio action")
        payload = None
        if method == "WiFi.SetConfig":
            roam = (params or {}).get("config", {}).get("roam", {})
            if set(params or {}) != {"config"} or set(params["config"]) != {"roam"} or not roam or set(roam) - {"rssi_thr", "interval"}:
                raise HomeAssistantError("Only roaming settings can be changed")
            payload = {"id": 1, "method": method, "params": params}
        url = f"http://{host}/rpc" + ("" if payload else f"/{method}")
        try:
            async with self.session.request(
                "POST" if payload else "GET", url, json=payload,
                allow_redirects=False, timeout=aiohttp.ClientTimeout(total=4),
            ) as response:
                if response.status != 200:
                    raise HomeAssistantError("Shelly radio is unavailable or requires authentication")
                body = bytearray()
                async for chunk in response.content.iter_chunked(8192):
                    body.extend(chunk)
                    if len(body) > MAX_RESPONSE:
                        raise HomeAssistantError("Shelly radio response is too large")
                result = json.loads(body)
                if not isinstance(result, dict) or "error" in result:
                    raise HomeAssistantError("Shelly rejected the radio request")
                result = result.get("result", {}) if payload else result
                if not isinstance(result, dict):
                    raise HomeAssistantError("Unexpected Shelly radio response")
                return result
        except aiohttp.ClientError, TimeoutError, ValueError:
            raise HomeAssistantError("Cannot communicate with the Shelly radio") from None

    async def _verify(self, host, expected_mac):
        info = await self._rpc(host, "Shelly.GetDeviceInfo")
        if normalize_mac(info.get("mac")) != expected_mac or info.get("gen") not in {2, 3, 4}:
            raise HomeAssistantError("Shelly identity does not match the registered device")
        if info.get("auth_en") is not False:
            raise HomeAssistantError("Shelly radio requires authentication")

    async def _read(self, host, mac):
        await self._verify(host, mac)
        config = await self._rpc(host, "WiFi.GetConfig")
        status = await self._rpc(host, "WiFi.GetStatus")
        roam = config.get("roam") or {}
        threshold = number(roam.get("rssi_thr"), -100, -40)
        interval = number(roam.get("interval"), 0, 3600)
        if threshold is None or interval is None:
            raise HomeAssistantError("Shelly roaming is not supported by this firmware")
        self._supported.add(mac)
        if interval > 0:
            self._intervals[mac] = int(interval)
        rssi = number(status.get("rssi"), -110, -1) if status.get("status") == "got ip" else None
        return {
            "roaming_supported": True, "radio_available": True,
            "roam_rssi_threshold": int(threshold), "roam_interval": int(interval),
            "rssi": rssi, "rssi_source": "shelly_wifi_status" if rssi is not None else None,
            "rssi_observed_at": datetime.now(UTC).isoformat() if rssi is not None else None,
            "wifi_bssid": normalize_mac(status.get("bssid")) if rssi is not None else None,
            "wifi_channel": number(status.get("channel"), 1, 196) if rssi is not None else None,
        }

    async def enrich(self, snapshot):
        async def poll(item):
            resolved = target(item)
            if not resolved:
                return
            host, mac = resolved
            async with self._semaphore, self._locks.setdefault(mac, asyncio.Lock()):
                try:
                    item.update(await self._read(host, mac))
                except HomeAssistantError:
                    # A failed measurement is never displayed as a fresh cached RSSI.
                    item.update({"roaming_supported": mac in self._supported, "radio_available": False})
        await asyncio.gather(*(poll(item) for network in snapshot["networks"].values() for item in network["clients"].values()))
        for network in snapshot["networks"].values():
            network["clients_with_signal"] = sum(c.get("connected") is True and c.get("rssi") is not None for c in network["clients"].values())
        return snapshot

    async def set_roaming(self, item, key, value):
        resolved = target(item)
        if not resolved or not item.get("roaming_supported"):
            raise HomeAssistantError("This client has no verified Shelly roaming controls")
        host, mac = resolved
        if key == "enabled":
            if not isinstance(value, bool):
                raise HomeAssistantError("Invalid roaming setting")
            key, value = "interval", self._intervals.get(mac, 60) if value else 0
        limits = {"rssi_thr": (-100, -40), "interval": (0, 3600)}
        if key not in limits or isinstance(value, bool) or number(value, *limits[key]) is None or float(value) != int(value):
            raise HomeAssistantError("Roaming value is outside the supported range")
        async with self._locks.setdefault(mac, asyncio.Lock()):
            # Fresh identity check before each write guards against IP reassignment.
            await self._verify(host, mac)
            config = await self._rpc(host, "WiFi.GetConfig")
            if not isinstance(config.get("roam"), dict):
                raise HomeAssistantError("Shelly roaming configuration is unavailable")
            await self._rpc(host, "WiFi.SetConfig", {"config": {"roam": {key: int(value)}}})
            measured = await self._read(host, mac)
            field = "roam_rssi_threshold" if key == "rssi_thr" else "roam_interval"
            if measured[field] != int(value):
                raise HomeAssistantError("Shelly did not confirm the requested roaming setting")
            return measured
