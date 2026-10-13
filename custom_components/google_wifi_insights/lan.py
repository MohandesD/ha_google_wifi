"""Cached, bounded read-only diagnostics for explicitly selected LAN networks."""
import asyncio
from collections import Counter
from copy import deepcopy
import ipaddress
import time

from .api import ApiError, json_get
from .information import clean
from .operations import now_iso

ENDPOINTS = {"status": "status", "wan_configuration": "wan-configuration",
             "developer_configuration": "developer-configuration", "welcome_mat": "welcome-mat"}


def private_host(value):
    if not isinstance(value, str):
        return None
    try:
        ip = ipaddress.ip_address(value)
    except ValueError, TypeError:
        return None
    return str(ip) if ip.version == 4 and ip.is_private and not any((ip.is_loopback, ip.is_multicast, ip.is_unspecified, ip.is_reserved, ip.is_link_local)) else None


class LanDiagnostics:
    def __init__(self, session):
        self.session, self.cache, self.next_read, self.locks = session, {}, {}, {}
        self.slots = asyncio.Semaphore(4)

    def observe_status(self, host, payload):
        if private_host(host) and isinstance(payload.get("system"), dict) and isinstance(payload.get("wan"), dict):
            self.cache[(host, "status")] = {"payload": clean(payload), "read": {"state": "available", "stale": False, "retrieved_at": now_iso()}}
            self.next_read[(host, "status")] = time.monotonic()+60

    async def _read(self, host, name):
        identity = (host, name)
        lock = self.locks.setdefault(identity, asyncio.Lock())
        async with lock:
            if self.next_read.get(identity, 0) > time.monotonic():
                return self.cache.get(identity, {"payload": {}, "read": {"state": "unavailable", "stale": True}})
            ttl = 60 if name == "status" else 3600
            try:
                async with self.slots, asyncio.timeout(4):
                    payload = await json_get(self.session, f"http://{host}/api/v1/{ENDPOINTS[name]}", {"X-XSRF-Protection": "1"})
                if name == "status" and (not isinstance(payload.get("system"), dict) or not isinstance(payload.get("wan"), dict)):
                    raise ApiError("Not a Google Wifi status response")
                result = {"payload": clean(payload), "read": {"state": "available", "stale": False, "retrieved_at": now_iso()}}
            except (ApiError, TimeoutError) as error:
                # Never relabel cached data as a fresh successful reading.
                previous = self.cache.get(identity, {})
                code = getattr(error, "status", None)
                result = {"payload": previous.get("payload", {}), "read": {**previous.get("read", {}),
                          "state": "not_supported" if code in (404, 405) else "denied" if code == 403 else "unavailable",
                          "http_status": code, "attempted_at": now_iso(), "stale": True}}
                ttl = max(21600 if code in (403, 404, 405) else 300, ttl)
            self.cache[identity], self.next_read[identity] = result, time.monotonic()+ttl
            return result

    async def point(self, host, expected_role=None):
        if not private_host(host):
            return {"stale": True, "endpoints": {"status": {"state": "not_configured"}}}
        status = await self._read(host, "status")
        payload, observed = status["payload"], status["read"]
        role = payload.get("system", {}).get("groupRole")
        local_ip = payload.get("wan", {}).get("localIpAddress")
        # A primary's WAN address belongs to its upstream subnet, not its LAN host.
        # Leaf WAN interfaces use the mesh subnet and must match their cloud address.
        if observed.get("stale") or expected_role and role != expected_role or role == "leaf" and local_ip and private_host(local_ip) != host:
            return {"host": host, "status": {}, "stale": True, "retrieved_at": observed.get("retrieved_at"),
                    "endpoints": {"status": {**observed, "stale": True}}}
        names = [name for name in ENDPOINTS if name != "status"]
        extra = await asyncio.gather(*(self._read(host, name) for name in names))
        return {"host": host, "status": deepcopy(payload), "source": "google_lan", "stale": False,
                "retrieved_at": observed.get("retrieved_at"),
                **{name: deepcopy(result["payload"]) for name, result in zip(names, extra, strict=True)},
                "endpoints": {"status": observed, **{name: result["read"] for name, result in zip(names, extra, strict=True)}}}

    async def enrich_cloud(self, snapshot, configured_hosts, explicit_gateway=None):
        """Use a unique online primary anchored to existing LAN configuration."""
        anchors = {private_host(host) for host in configured_hosts}
        if explicit_gateway:
            anchors.add(private_host(explicit_gateway))
        anchors.discard(None)
        candidates = []
        for network in snapshot["networks"].values():
            roots = [p for p in network["points"].values() if p.get("is_root") is True and p.get("online") is True]
            if len(roots) == 1 and roots[0].get("host") in anchors:
                candidates.append((network, roots[0]))
        counts = Counter(root["host"] for _, root in candidates)
        jobs = []
        for network, root in candidates:
            if counts[root["host"]] != 1:
                continue
            settings = network.get("google_telemetry", {}).get("groupSettings", {}).get("lanSettings", {})
            try:
                subnet = ipaddress.ip_network(root["host"]+"/"+str(settings.get("netmask", "255.255.255.0")), strict=False)
            except ValueError:
                continue
            for point in list(network["points"].values())[:10]:
                host = private_host(point.get("host"))
                if host and point.get("online") is True and (host in configured_hosts or explicit_gateway == root["host"] and ipaddress.ip_address(host) in subnet):
                    jobs.append((point, host))

        async def poll(point, host):
            point["lan_information"] = await self.point(host, "root" if point.get("is_root") else "leaf")

        try:
            async with asyncio.timeout(12):
                await asyncio.gather(*(poll(point, host) for point, host in jobs))
        except TimeoutError:
            for point, host in jobs:
                point.setdefault("lan_information", {"host": host, "stale": True, "endpoints": {"status": {"state": "unavailable", "stale": True}}})
