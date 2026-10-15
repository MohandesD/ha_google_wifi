"""Bounded LAN reads and explicit unofficial Google Home Wifi API operations."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from urllib.parse import quote
from uuid import uuid4

import aiohttp
import gpsoauth
import requests

from .capabilities import READS, apply_extras, safe_metadata
from .history import WINDOWS, apply_history, normalize_history, request_window
from .identity import normalize_mac
from .model import cloud_network, local_point
from .operations import MONITOR_SECONDS, TERMINAL_STATES, now_iso, pending
from .radio_schema import radio_schema

AUTH_URL = "https://android.clients.google.com/auth"
CLOUD_URL = "https://googlehomefoyer-pa.googleapis.com/v2/"
CLIENT_SIGNATURE = "24bb24c05e47e0aefa68a58a766179d9b613a600"
MAX_RESPONSE = 4 * 1024 * 1024


class ApiError(Exception):
    """A sanitized communication failure."""

    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


class AuthError(ApiError):
    """Google authentication was rejected."""

    def __init__(self, message="Google rejected authentication", reason="invalid_auth"):
        super().__init__(message)
        self.reason = reason if reason in {"invalid_auth", "google_challenge"} else "invalid_auth"


class AuthServiceError(ApiError):
    """A temporary Google authentication outage, not a rejected credential."""


class NoNetworksError(ApiError):
    """Authentication succeeded but the account returned no WiFi networks."""


class RateLimitError(ApiError):
    """Back off polling when Google throttles requests."""

    def __init__(self, retry_after=300):
        super().__init__("Google rate limit")
        self.retry_after = retry_after


def google_auth(
    email: str, token: str, android_id: str, exchange: bool = False
) -> dict:
    """Use gpsoauth's TLS adapter with bounded requests and no global patching."""
    fields = {
        "accountType": "HOSTED_OR_GOOGLE",
        "Email": email,
        "androidId": android_id,
        "has_permission": 1,
        "source": "android",
        "device_country": "us",
        "operatorCountry": "us",
        "lang": "en",
        "sdk_version": 17,
        "google_play_services_version": 240913000,
    }
    if exchange:
        signature = "38918a453d07199354f8b19af05ec6562ced5788"
        fields.update(
            {
                "Token": token,
                "ACCESS_TOKEN": 1,
                "add_account": 1,
                "service": "ac2dm",
                "client_sig": signature,
                "callerSig": signature,
                "droidguard_results": "dummy123",
            }
        )
    else:
        fields.update(
            {
                "EncryptedPasswd": token,
                "service": "oauth2:https://www.googleapis.com/auth/accesspoints",
                "app": "com.google.android.apps.chromecast.app",
                "client_sig": CLIENT_SIGNATURE,
            }
        )
    try:
        with requests.Session() as session:
            session.mount(AUTH_URL, gpsoauth.AuthHTTPAdapter())
            session.headers.update(
                {"User-Agent": "GoogleAuth/1.4", "Accept-Encoding": "identity"}
            )
            response = session.post(
                AUTH_URL,
                data=fields,
                timeout=(10, 30),
                allow_redirects=False,
                verify=True,
            )
            if response.status_code == 429:
                retry = response.headers.get("Retry-After", "300")
                raise RateLimitError(min(max(int(retry), 60), 3600) if retry.isdigit() else 300)
            if response.status_code >= 500:
                raise AuthServiceError("Google authentication service unavailable")
            if response.status_code not in (200, 401, 403):
                raise ApiError("Unexpected authentication response")
            try:
                if len(response.text) > 65536:
                    raise ValueError
                result = gpsoauth.google.parse_auth_response(response.text)
            except (TypeError, ValueError):
                raise ApiError("Unexpected authentication response") from None
            if result.get("Error") in {"NeedsBrowser", "WebLoginRequired", "CaptchaRequired", "InvalidSecondFactor"}:
                raise AuthError(reason="google_challenge")
            if result.get("Error") == "ServiceUnavailable":
                raise AuthServiceError("Google authentication service unavailable")
            if response.status_code in (401, 403) or result.get("Error"):
                raise AuthError()
    except requests.RequestException:
        raise AuthServiceError("Cannot contact Google authentication") from None
    if not result.get("Token" if exchange else "Auth"):
        raise ApiError("Incomplete Google authentication response")
    return result


async def json_get(session, url, headers=None) -> dict:
    return await json_request(session, "GET", url, headers)


async def json_request(session, method, url, headers=None, payload=None) -> dict:
    """Never follow redirects with credentials or log response bodies."""
    try:
        async with session.request(
            method, url,
            headers=headers,
            json=payload,
            allow_redirects=False,
            timeout=aiohttp.ClientTimeout(total=15),
        ) as response:
            if response.status == 429:
                retry = response.headers.get("Retry-After", "300")
                raise RateLimitError(
                    min(max(int(retry), 60), 3600) if retry.isdigit() else 300
                )
            if response.status == 401:
                raise AuthError("Google token expired or rejected")
            if not 200 <= response.status < 300:
                raise ApiError(f"Google endpoint returned HTTP {response.status}", response.status)
            if response.content_length and response.content_length > MAX_RESPONSE:
                raise ApiError("Response too large")
            body = bytearray()
            async for chunk in response.content.iter_chunked(65536):
                body.extend(chunk)
                if len(body) > MAX_RESPONSE:
                    raise ApiError("Response too large")
            import json

            result = json.loads(body) if body else {}
            if not isinstance(result, dict):
                raise ApiError("Unexpected response format")
            return result
    except aiohttp.ClientError, TimeoutError, ValueError:
        raise ApiError("Network request failed; delivery of a write is unconfirmed") from None


class LocalClient:
    def __init__(self, session, points, lan=None):
        self.session, self.points = session, points
        self.lan = lan

    async def snapshot(self):
        points = {}
        for point in self.points:
            try:
                status = await json_get(
                    self.session, f"http://{point['host']}/api/v1/status"
                )
                if not isinstance(status.get("system"), dict) or not isinstance(
                    status.get("wan"), dict
                ):
                    raise ApiError("Not a Google Wifi status response")
            except ApiError:
                status = None
            points[point["host"]] = local_point(point, status)
            if self.lan and status:
                self.lan.observe_status(point["host"], status)
                points[point["host"]]["lan_information"] = await self.lan.point(point["host"])
        if not any(point["reachable"] for point in points.values()):
            raise ApiError("No Google Wifi point responded")
        return {
            "networks": {
                "local": {
                    "name": "Google WiFi",
                    "points": points,
                    "clients": {},
                    "connected_clients": None,
                    "weak_clients": None,
                    "clients_with_signal": None,
                    "download_mbps": None,
                    "upload_mbps": None,
                    "unassigned_clients": None,
                    "unknown_connection_clients": None,
                    "saturation": None,
                    "diagnosis": "insufficient_radio_data",
                    "source": "local_status",
                }
            }
        }


class CloudClient:
    def __init__(self, session, executor: Callable, email, master_token, android_id):
        self.session, self.executor = session, executor
        self.email, self.master_token, self.android_id = email, master_token, android_id
        self._token, self._expiry, self._retry_until = None, 0, 0
        self._lock = asyncio.Lock()
        self.radio_evidence = {}
        self.network_errors = {}
        self._mac_cache = {}
        self._mac_retry = {}
        self._speed_cache = {}
        self._speed_next_read = {}
        self._optional_cache, self._optional_next, self._read_status = {}, {}, {}
        self._histories, self._action_status, self._operations = {}, {}, {}
        self._action_lock = asyncio.Lock()
        self._mesh_requests = {}
        self._optional_slots = asyncio.Semaphore(3)

    async def async_validate_account(self):
        """Check authentication and network discovery without polling every metric."""
        result = await self._get("groups?prettyPrint=false")
        groups = result.get("groups")
        if not isinstance(groups, list):
            raise ApiError("Unexpected network discovery response")
        count = sum(isinstance(group, dict) and isinstance(group.get("id"), str) and bool(group["id"]) for group in groups)
        if not count:
            raise NoNetworksError("No Google Wifi networks found on this account")
        return count

    async def _authenticate(self, force=False):
        async with self._lock:
            if not force and self._token and self._expiry > time.monotonic() + 60:
                return
            result = await self.executor(
                google_auth, self.email, self.master_token, self.android_id
            )
            self._token = result["Auth"]
            try:
                lifetime = int(result.get("ExpiresInDurationSec", 3600))
            except TypeError, ValueError:
                lifetime = 3600
            self._expiry = time.monotonic() + max(60, lifetime)

    async def _get(self, path):
        return await self._request("GET", path)

    async def _request(self, method, path, payload=None):
        if time.monotonic() < self._retry_until:
            raise RateLimitError(int(self._retry_until - time.monotonic()) + 1)
        await self._authenticate()
        try:
            return await json_request(
                self.session, method,
                CLOUD_URL + path,
                {"Authorization": f"Bearer {self._token}"},
                payload,
            )
        except AuthError:
            await self._authenticate(force=True)
            return await json_request(
                self.session, method,
                CLOUD_URL + path,
                {"Authorization": f"Bearer {self._token}"},
                payload,
            )

    async def _optional(self, group_id, key, path, ttl, period=None):
        """Denied/empty optional measurements never remove core network entities."""
        from datetime import UTC, datetime
        identity = (group_id, key)
        if self._optional_next.get(identity, 0) > time.monotonic():
            return
        self._optional_next[identity] = time.monotonic() + ttl
        status = self._read_status.setdefault(group_id, {})
        try:
            async with self._optional_slots:
                payload = await self._get(path)
            if period is not None:
                self._histories.setdefault(group_id, {})[key.removeprefix("usage_")] = normalize_history(payload, period)
            else:
                # This opaque encoded configuration is not telemetry and may contain keys.
                self._optional_cache.setdefault(group_id, {})[key] = {} if key == "meshConfiguration" else payload
            status[key] = {"state": "available", "retrieved_at": datetime.now(UTC).isoformat(), "stale": False}
        except AuthError, RateLimitError:
            raise
        except (ApiError, TypeError, ValueError, AttributeError) as error:
            code = getattr(error, "status", None)
            denied = code in (403, 404, 405)
            self._optional_next[identity] = time.monotonic() + max(ttl, 1800 if denied else 120)
            status[key] = {**status.get(key, {}), "state": "denied" if denied else "error",
                           "http_status": code, "stale": True}

    def invalidate(self, group_id):
        for identity in list(self._optional_next):
            if identity[0] == group_id:
                self._optional_next.pop(identity)

    async def action(self, group_id, action, path, method, payload, *, target_kind=None, target_id=None, target_name=None, on_update=None, prepare_path=None):
        """No automatic retry of a transport failure or ambiguous write response."""
        if prepare_path is not None and action != "test_mesh":
            raise ApiError("Server preparation is only valid for a mesh test")
        operations = self._operations.setdefault(group_id, [])
        if any(pending(op) and (op.get("action"), op.get("target_kind"), op.get("target_id")) == (action, target_kind, target_id) for op in operations):
            raise ApiError("This action is already pending for the selected target")
        if sum(pending(op) for op in operations) >= 20:
            raise ApiError("Too many Google operations are pending")
        while len(operations) >= 20:
            previous = next(op for op in operations if not pending(op))
            self._mesh_requests.pop(previous.get("request_id"), None)
            operations.remove(previous)
        record = {"request_id": uuid4().hex, "action": action, "target_kind": target_kind,
                  "target_id": target_id, "target_name": target_name, "state": "QUEUED",
                  "operation_id": None, "requested_at": now_iso(), "updated_at": now_iso()}
        operations.append(record)
        if prepare_path is not None:
            record["stage"] = "preparing_server"
            self._mesh_requests[record["request_id"]] = (method, path, payload)
        if on_update:
            on_update()
        async with self._action_lock:
            record.update(state="SENDING", updated_at=now_iso())
            if on_update:
                on_update()
            try:
                request_path = prepare_path or path
                separator = "&" if "?" in request_path else "?"
                response = await self._request(method, request_path + separator + "prettyPrint=false", None if prepare_path else payload)
                if not isinstance(response, dict):
                    raise ApiError("Google returned an unconfirmed operation")
                op = response.get("operation") or response
                if not isinstance(op, dict):
                    raise ApiError("Google returned an unconfirmed operation")
                operation_id = op.get("operationId")
                state = op.get("operationState")
                record.update(operation_id=operation_id if isinstance(operation_id, str) and operation_id else None,
                              state=state if isinstance(state, str) and state else "ACCEPTED_UNCONFIRMED", updated_at=now_iso())
                if prepare_path:
                    record["server_state"] = record["state"]
                    if not record["operation_id"] and record["state"] not in ("ERROR", "FAILED", "CANCELLED"):
                        record["state"] = "ACCEPTED_UNCONFIRMED"
                    elif state == "DONE":
                        record["state"] = "CREATED"
                if record["state"] in TERMINAL_STATES:
                    record["finished_at"] = now_iso()
                if record["state"] in ("ERROR", "FAILED", "CANCELLED"):
                    raise ApiError("Google operation failed")
            except ApiError as error:
                if isinstance(error, RateLimitError):
                    self._retry_until = time.monotonic() + error.retry_after
                if record["state"] not in TERMINAL_STATES:
                    rejected = error.status is not None and 400 <= error.status < 500 or isinstance(error, (AuthError, RateLimitError))
                    record.update(state="REJECTED" if rejected else "DELIVERY_UNCONFIRMED", updated_at=now_iso())
                if error.status:
                    record["http_status"] = error.status
                if isinstance(error, AuthError):
                    record["status_error"] = "authentication_required"
                if isinstance(error, RateLimitError):
                    record["status_error"] = "rate_limited"
                if record["state"] == "REJECTED":
                    record["finished_at"] = now_iso()
                self._action_status.setdefault(group_id, {})[action] = "denied" if error.status in (403, 404, 405) else "unconfirmed"
                raise
            except asyncio.CancelledError:
                record.update(state="DELIVERY_UNCONFIRMED", updated_at=now_iso())
                raise
            finally:
                if not pending(record):
                    self._mesh_requests.pop(record["request_id"], None)
                if on_update:
                    on_update()
            self._action_status.setdefault(group_id, {})[action] = "accepted"
            self.invalidate(group_id)
            return record.copy()

    async def _start_mesh_measurement(self, group_id, operation):
        """Continue one user request after server readiness; never resend a write."""
        async with self._action_lock:
            if operation.get("stage") != "preparing_server" or not pending(operation):
                return
            request = self._mesh_requests.pop(operation["request_id"], None)
            if request is None:
                return
            operation.update(stage="measuring", state="SENDING", server_state="DONE", operation_id=None, updated_at=now_iso())
            method, path, payload = request
            try:
                separator = "&" if "?" in path else "?"
                response = await self._request(method, path+separator+"prettyPrint=false", payload)
                if not isinstance(response, dict):
                    raise ApiError("Google returned an unconfirmed mesh operation")
                result = response.get("operation") or response
                if not isinstance(result, dict):
                    raise ApiError("Google returned an unconfirmed mesh operation")
                oid, state = result.get("operationId"), result.get("operationState")
                operation.update(operation_id=oid if isinstance(oid, str) and oid else None,
                                 state=state if isinstance(state, str) and state else "ACCEPTED_UNCONFIRMED", updated_at=now_iso())
                if operation["state"] == "DONE":
                    self.invalidate(group_id)
            except ApiError as error:
                if isinstance(error, RateLimitError):
                    self._retry_until = time.monotonic()+error.retry_after
                rejected = error.status is not None and 400 <= error.status < 500 or isinstance(error, (AuthError, RateLimitError))
                operation.update(state="REJECTED" if rejected else "DELIVERY_UNCONFIRMED", updated_at=now_iso())
                if error.status:
                    operation["http_status"] = error.status
                if isinstance(error, AuthError):
                    operation["status_error"] = "authentication_required"
            except asyncio.CancelledError:
                operation.update(state="DELIVERY_UNCONFIRMED", updated_at=now_iso())
                raise
            if operation["state"] in TERMINAL_STATES:
                operation["finished_at"] = now_iso()

    def has_pending_operations(self, group_id):
        return any(pending(op) for op in self._operations.get(group_id, []))

    async def _poll_operations(self, group_id):
        from datetime import UTC, datetime

        from .history import instant
        for operation in list(self._operations.get(group_id, [])):
            if not pending(operation):
                continue
            if (datetime.now(UTC)-instant(operation["requested_at"])).total_seconds() > MONITOR_SECONDS:
                operation.update(state="PENDING_UNCONFIRMED", status_error="monitoring_timeout", updated_at=now_iso())
                self._mesh_requests.pop(operation.get("request_id"), None)
                continue
            if operation["state"] in ("QUEUED", "SENDING"):
                continue
            if time.monotonic() < self._retry_until:
                continue
            try:
                stage = operation.get("stage")
                if stage == "preparing_server" and operation.get("server_state") == "DONE":
                    await self._start_mesh_measurement(group_id, operation)
                    continue
                progress = await self._get("operations/"+quote(operation["operation_id"], safe="")+"?prettyPrint=false")
                if not pending(operation) or operation.get("stage") != stage:
                    continue  # Another status reader already received a terminal result.
                if isinstance(progress, dict) and isinstance(progress.get("operation"), dict):
                    progress = progress["operation"]
                state = progress.get("operationState") if isinstance(progress, dict) else None
                if stage == "preparing_server":
                    operation["server_state"] = state
                    if state == "DONE":
                        await self._start_mesh_measurement(group_id, operation)
                        continue
                if operation["state"] in ("RUNNING", "IN_PROGRESS") and state in ("CREATED", "PENDING"):
                    continue
                if isinstance(state, str) and state and operation.get("status_error"):
                    operation.pop("status_error", None)
                    operation.pop("http_status", None)
                    operation["updated_at"] = now_iso()
                if isinstance(state, str) and state and state != operation["state"]:
                    operation.update(state=state, updated_at=now_iso())
                    operation.pop("status_error", None)
                    if state in TERMINAL_STATES:
                        operation["finished_at"] = now_iso()
                        self._mesh_requests.pop(operation.get("request_id"), None)
                    if state == "DONE":
                        self.invalidate(group_id)
            except AuthError:
                operation.update(state="PENDING_UNCONFIRMED", status_error="authentication_required", updated_at=now_iso())
                self._mesh_requests.pop(operation.get("request_id"), None)
                raise
            except RateLimitError as error:
                self._retry_until = time.monotonic() + error.retry_after
                raise
            except ApiError as error:
                operation["status_error"] = "status_unavailable"
                if error.status:
                    operation["http_status"] = error.status

    async def _station_macs(self, group_id, stations):
        """Read MACs in bounded batches. Never run tests or modify router settings."""
        now = time.monotonic()
        active = {s["id"] for s in stations if s.get("connected") is True}
        cache = self._mac_cache.setdefault(group_id, {})
        needed = sorted(sid for sid in active if cache.get(sid, (None, 0))[1] < now)
        if needed and self._mac_retry.get(group_id, 0) <= now:
            try:
                # Limit the total optional work per poll, including operation waiting.
                async with asyncio.timeout(30):
                    for start in range(0, min(len(needed), 200), 100):
                        batch = needed[start:start + 100]
                        created = await self._request(
                            "POST", f"groups/{quote(group_id, safe='')}/stations/operations/sensitiveInfo?prettyPrint=false",
                            {"stationIds": batch},
                        )
                        operation = (created.get("operation") or {}).get("operationId")
                        if not isinstance(operation, str) or not operation:
                            raise ApiError("MAC lookup operation unavailable")
                        path = f"operations/{quote(operation, safe='')}"
                        for attempt in range(8):
                            progress = await self._get(path + "?prettyPrint=false")
                            if progress.get("operationState") == "DONE":
                                break
                            if progress.get("operationState") in ("ERROR", "FAILED", "CANCELLED"):
                                raise ApiError("MAC lookup operation failed")
                            await asyncio.sleep(1)
                        else:
                            raise ApiError("MAC lookup operation pending")
                        result = await self._get(path + "/sensitiveInfo?prettyPrint=false")
                        rows = result.get("stationSensitiveInfos")
                        if not isinstance(rows, list):
                            raise ApiError("MAC lookup result unavailable")
                        # Google may return additional records: accept requested IDs only.
                        returned = {r.get("stationId"): normalize_mac(r.get("macAddress"))
                                    for r in rows if isinstance(r, dict) and r.get("stationId") in batch}
                        for sid in batch:
                            mac = returned.get(sid)
                            cache[sid] = (mac, now + (21600 if mac else 3600))
            except AuthError, RateLimitError:
                raise
            except ApiError as error:
                # Denied endpoints back off longer; transient startup failures retry
                # at the next normal poll while preserving the already resolved MACs.
                denied = any(f"HTTP {code}" in str(error) for code in (403, 404, 405))
                self._mac_retry[group_id] = now + (1800 if denied else 120)
            except TimeoutError:
                self._mac_retry[group_id] = now + 120
        return {sid: value[0] for sid, value in cache.items() if value[0]}

    async def snapshot(self):
        """Keep one inaccessible network from discarding other network readings."""
        try:
            groups_payload = await self._get("groups?prettyPrint=false")
            self.radio_evidence = {"groups": radio_schema(groups_payload), "networks": []}
            groups = groups_payload.get("groups")
            if not isinstance(groups, list):
                raise ApiError("Google returned no Wifi networks")
            self.network_errors = {}
            networks = {}
            last_error = None
            for group in groups:
                if not isinstance(group, dict) or not isinstance(group.get("id"), str) or not group["id"]:
                    continue
                group_id = group["id"]
                try:
                    networks[group_id] = await self._snapshot_network(group, group_id)
                except (AuthError, RateLimitError):
                    # Account authentication and throttling apply to the whole session.
                    raise
                except ApiError as error:
                    last_error = error
                    self.network_errors[group_id] = {
                        "state": "denied" if error.status in (403, 404, 405) else "unavailable",
                        "http_status": error.status,
                    }
                except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
                    # No provider values or payloads are placed in errors or diagnostics.
                    last_error = ApiError("Unexpected Google network response")
                    self.network_errors[group_id] = {"state": "invalid_response", "http_status": None}
            if not networks:
                raise last_error or ApiError("No Google Wifi networks found on this account")
            return {"networks": networks, "network_errors": self.network_errors.copy()}
        except RateLimitError as error:
            self._retry_until = time.monotonic() + error.retry_after
            raise

    async def _snapshot_network(self, group, group_id):
        """Collect one network; optional endpoints retain their independent backoff."""
        from datetime import UTC, datetime
        read_status = self._read_status.setdefault(group_id, {})
        collected_at = datetime.now(UTC).isoformat()
        read_status["groups"] = {"state": "available", "retrieved_at": collected_at, "stale": False}
        prefix = f"groups/{quote(group_id, safe='')}/"
        status = await self._get(prefix + "status?prettyPrint=false")
        clients = await self._get(prefix + "stations?prettyPrint=false")
        if not isinstance(clients.get("stations"), list):
            raise ApiError("Google returned no client list")
        if any(
            not isinstance(station, dict)
            or not isinstance(station.get("id"), str)
            for station in clients["stations"]
        ):
            raise ApiError("Unexpected client record format")
        for key in ("status", "stations"):
            read_status[key] = {"state": "available", "retrieved_at": collected_at, "stale": False}
        # Traffic is optional. A throttled request still triggers backoff.
        try:
            metrics = await self._get(
                prefix + "realtimeMetrics?prettyPrint=false"
            )
            read_status["realtimeMetrics"] = {"state": "available", "retrieved_at": collected_at, "stale": False}
        except AuthError, RateLimitError:
            raise
        except ApiError as error:
            metrics = {}
            read_status["realtimeMetrics"] = {"state": "error", "http_status": error.status, "stale": True}
        self.radio_evidence["networks"].append({
            "status": radio_schema(status),
            "stations": radio_schema(clients),
            "metrics": radio_schema(metrics),
        })
        await self._poll_operations(group_id)
        reads = [self._optional(group_id, key, prefix+key+"?prettyPrint=false", ttl) for key, ttl in READS.items()]
        for mode, (_, _, ttl) in WINDOWS.items():
            period, query = request_window(mode)
            reads.append(self._optional(group_id, "usage_"+mode, prefix+"historicalUsage?"+query, ttl, period))
        read_results = await asyncio.gather(*reads, return_exceptions=True)
        for result in read_results:
            if isinstance(result, BaseException):
                raise result
        extras = self._optional_cache.get(group_id, {})
        await self._optional(group_id, "groupDetails", prefix.rstrip("/")+"?prettyPrint=false", 900)
        await self._optional("_account", "userPreferences", "userPreferences?prettyPrint=false", 3600)
        supplemental = []
        for ap in group.get("accessPoints", [])[:30]:
            if not isinstance(ap, dict) or not isinstance(ap.get("id"), str):
                continue
            aid = ap["id"]
            supplemental.append(self._optional(group_id, "hardware:"+aid, "accesspoints/"+quote(aid, safe="")+"/hardwareBundleSetupInfo?prettyPrint=false", 86400))
        versions = {(ap.get("accessPointProperties") or {}).get("firmwareVersion") for ap in group.get("accessPoints", []) if isinstance(ap, dict)}
        import re
        for version in sorted(v for v in versions if isinstance(v, str) and re.fullmatch(r"\d+(?:\.\d+){1,5}", v))[:10]:
            supplemental.append(self._optional("_firmware", "notes:"+version, "apSoftware/"+quote(version, safe="")+"/releaseNotes?prettyPrint=false", 21600))
        results = await asyncio.gather(*supplemental, return_exceptions=True)
        for result in results:
            if isinstance(result, BaseException):
                raise result
        extras = self._optional_cache.get(group_id, {})
        network = cloud_network(
            group, status, clients["stations"], metrics,
            await self._station_macs(group_id, clients["stations"]),
            extras.get("speedTestResults", {}),
        )
        for records in ([network], network["points"].values(), network["clients"].values()):
            for item in records:
                if not isinstance(item.get("name"), str) or len(item["name"]) > 512:
                    raise ApiError("Unexpected Google network identity format")
                if item.get("firmware") is not None and not isinstance(item["firmware"], str):
                    raise ApiError("Unexpected Google firmware format")
        network["google_telemetry"]["fullStatus"] = safe_metadata(status)
        network["google_telemetry"]["fullRealtimeMetrics"] = safe_metadata(metrics)
        for station in clients["stations"]:
            network["clients"][station["id"]]["_station_metadata"] = station
        apply_history(network, self._histories.get(group_id, {}))
        apply_extras(network, group, extras, self._read_status.get(group_id, {}), self._action_status.get(group_id, {}))
        from .information import clean, firmware_notes
        network["google_telemetry"]["groupDetails"] = clean(extras.get("groupDetails", {}))
        network["google_telemetry"]["accountPreferences"] = clean(self._optional_cache.get("_account", {}).get("userPreferences", {}))
        read_status["userPreferences"] = self._read_status.get("_account", {}).get("userPreferences", {}).copy()
        for aid, point in network["points"].items():
            version = point.get("firmware")
            note_status = self._read_status.get("_firmware", {}).get("notes:"+str(version), {"state": "not_supplied", "stale": True})
            read_status["notes:"+str(version)] = note_status.copy()
            point["firmware_notes"] = firmware_notes(self._optional_cache.get("_firmware", {}).get("notes:"+str(version), {}), version, note_status)
            point["hardware_setup_information"] = clean(extras.get("hardware:"+aid, {}))
            point["google_telemetry"]["hardwareSetupInformation"] = point["hardware_setup_information"]
        network["operations"] = self._operations.get(group_id, []).copy()
        network["last_operation"] = network["operations"][-1]["state"] if network["operations"] else "NONE"
        return network
