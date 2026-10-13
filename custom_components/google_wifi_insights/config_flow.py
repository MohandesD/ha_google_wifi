"""UI setup; Google credentials are entered directly in Home Assistant."""

import hashlib
import re
import secrets

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    ApiError,
    AuthError,
    AuthServiceError,
    CloudClient,
    LocalClient,
    NoNetworksError,
    RateLimitError,
    google_auth,
)
from .auth import CredentialInputError, normalize_email, normalize_google_token
from .const import DEFAULT_INTERVAL, DOMAIN, MIN_INTERVAL
from .model import parse_points


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        super().__init__()
        self._email = ""
        self._android_id = secrets.token_hex(8)
        self._master_android_id = ""
        self._credential_step = "cloud_cookie"
        self._pending = None
        self._pending_client = None
        self._retry_error = "cannot_connect"

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlow()

    async def async_step_user(self, user_input=None):
        return self.async_show_menu(step_id="user", menu_options=["local", "cloud"])

    async def async_step_local(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                points = parse_points(user_input["points"])
                client = LocalClient(async_get_clientsession(self.hass), points)
                await client.snapshot()
            except ValueError:
                errors["base"] = "invalid_points"
            except ApiError:
                errors["base"] = "cannot_connect"
            else:
                identity = hashlib.sha256(
                    ";".join(sorted(point["host"] for point in points)).encode()
                ).hexdigest()
                await self.async_set_unique_id("local:" + identity)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Google WiFi Insights (local)",
                    data={"mode": "local", "points": points},
                )
        return self.async_show_form(
            step_id="local",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "points",
                        default=(user_input or {}).get(
                            "points", "Google WiFi=192.168.86.1"
                        ),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(multiline=True)
                    ),
                }
            ),
        )

    async def async_step_cloud(self, user_input=None):
        self._clear_pending()
        return self.async_show_menu(
            step_id="cloud", menu_options=["cloud_cookie", "cloud_master"]
        )

    async def async_step_cloud_cookie(self, user_input=None):
        return await self._async_credentials("cloud_cookie", user_input)

    async def async_step_cloud_master(self, user_input=None):
        return await self._async_credentials("cloud_master", user_input)

    def _reauth_entry(self):
        if self.source == config_entries.SOURCE_REAUTH:
            return self._get_reauth_entry()
        return None

    def _clear_pending(self):
        self._pending = None
        self._pending_client = None

    def _show_credentials(self, errors=None):
        fields = {
            vol.Required("email", default=self._email): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.EMAIL)
            ),
            vol.Required("oauth_token"): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
        }
        if self._credential_step == "cloud_master":
            fields[vol.Required("android_id", default=self._master_android_id)] = str
        return self.async_show_form(
            step_id=self._credential_step,
            errors=errors,
            data_schema=vol.Schema(fields),
        )

    async def _async_credentials(self, step_id, user_input):
        self._credential_step = step_id
        if user_input is None:
            return self._show_credentials()
        self._clear_pending()
        try:
            email = normalize_email(user_input["email"])
        except CredentialInputError as error:
            return self._show_credentials({"email": error.reason})
        self._email = email
        entry = self._reauth_entry()
        if entry and self._email != entry.data["email"].strip().lower():
            return self._show_credentials({"base": "account_mismatch"})
        method = "cookie" if step_id == "cloud_cookie" else "master"
        if method == "master":
            android_id = user_input["android_id"].strip()
            if not re.fullmatch(r"[a-fA-F0-9]{16}", android_id):
                return self._show_credentials({"android_id": "invalid_android_id"})
            self._master_android_id = android_id
        else:
            android_id = self._android_id
        try:
            token = normalize_google_token(user_input["oauth_token"], method)
        except CredentialInputError as error:
            if error.reason == "wrong_token_type":
                self._credential_step = "cloud_master" if method == "cookie" else "cloud_cookie"
            return self._show_credentials({"oauth_token": error.reason})
        if entry is None:
            await self.async_set_unique_id("cloud:" + hashlib.sha256(self._email.encode()).hexdigest())
            self._abort_if_unique_id_configured()
        try:
            if method == "cookie":
                result = await self.hass.async_add_executor_job(
                    google_auth, self._email, token, android_id, True
                )
                token = result["Token"]
        except AuthError as error:
            return self._show_credentials({"base": error.reason})
        except RateLimitError:
            return self._show_credentials({"base": "rate_limited"})
        except AuthServiceError:
            return self._show_credentials({"base": "auth_unavailable"})
        except ApiError:
            return self._show_credentials({"base": "cannot_connect"})
        self._pending = {
            "mode": "cloud", "email": self._email,
            "master_token": token, "android_id": android_id,
        }
        self._pending_client = CloudClient(
            async_get_clientsession(self.hass), self.hass.async_add_executor_job,
            self._email, token, android_id,
        )
        return await self._async_validate_pending()

    async def _async_validate_pending(self):
        try:
            await self._pending_client.async_validate_account()
        except AuthError as error:
            self._clear_pending()
            return self._show_credentials({"base": error.reason})
        except RateLimitError:
            self._retry_error = "rate_limited"
        except AuthServiceError:
            self._retry_error = "auth_unavailable"
        except NoNetworksError:
            self._retry_error = "no_networks"
        except ApiError as error:
            self._retry_error = "account_access" if error.status == 403 else "cannot_connect"
        else:
            data = self._pending
            self._clear_pending()
            if entry := self._reauth_entry():
                return self.async_update_reload_and_abort(entry, data_updates=data)
            return self.async_create_entry(title="Google WiFi Insights", data=data)
        return await self.async_step_cloud_retry()

    async def async_step_cloud_retry(self, user_input=None):
        if self._pending is None:
            return await self.async_step_cloud()
        if user_input is not None:
            if user_input.get("new_token"):
                return await self.async_step_cloud()
            return await self._async_validate_pending()
        return self.async_show_form(
            step_id="cloud_retry",
            errors={"base": self._retry_error},
            data_schema=vol.Schema(
                {vol.Optional("new_token", default=False): bool}
            ),
        )

    async def async_step_reauth(self, entry_data):
        if entry_data.get("mode") != "cloud":
            return self.async_abort(reason="not_cloud")
        self._email = entry_data["email"]
        self._android_id = entry_data["android_id"]
        self._master_android_id = entry_data["android_id"]
        return await self.async_step_cloud()


class OptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        return self.async_show_menu(
            step_id="init",
            menu_options=["polling", "renew_auth"]
            if self.config_entry.data["mode"] == "cloud" else ["polling"],
        )

    async def async_step_renew_auth(self, user_input=None):
        entry = self.config_entry
        if entry.data["mode"] != "cloud":
            return self.async_abort(reason="not_cloud")
        active = next(entry.async_get_active_flows(self.hass, {config_entries.SOURCE_REAUTH}), None)
        if active is None:
            active = await self.hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": config_entries.SOURCE_REAUTH, "entry_id": entry.entry_id},
                data=dict(entry.data),
            )
        result = self.async_create_entry(title="", data=None)
        result["next_flow"] = (config_entries.FlowType.CONFIG_FLOW, active["flow_id"])
        return result

    async def async_step_polling(self, user_input=None):
        errors = {}
        if user_input is not None:
            if self.config_entry.data["mode"] == "local":
                try:
                    points = parse_points(user_input["points"])
                    await LocalClient(
                        async_get_clientsession(self.hass), points
                    ).snapshot()
                except ValueError:
                    errors["base"] = "invalid_points"
                except ApiError:
                    errors["base"] = "cannot_connect"
                else:
                    self.hass.config_entries.async_update_entry(
                        self.config_entry,
                        data={**self.config_entry.data, "points": points},
                    )
            gateway = user_input.get("lan_gateway", "").strip()
            if self.config_entry.data["mode"] == "cloud" and gateway:
                from .lan import private_host
                if private_host(gateway) is None:
                    errors["base"] = "invalid_points"
            if not errors:
                options = {**self.config_entry.options, "scan_interval": user_input["scan_interval"]}
                if self.config_entry.data["mode"] == "cloud":
                    if gateway:
                        options["lan_gateway"] = gateway
                    else:
                        options.pop("lan_gateway", None)
                return self.async_create_entry(
                    title="", data=options
                )
        fields = {
            vol.Required(
                "scan_interval",
                default=self.config_entry.options.get(
                    "scan_interval", DEFAULT_INTERVAL
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=MIN_INTERVAL, max=3600))
        }
        if self.config_entry.data["mode"] == "local":
            text = "\n".join(
                f"{point['name']}={point['host']}"
                for point in self.config_entry.data["points"]
            )
            fields[vol.Required("points", default=text)] = selector.TextSelector(
                selector.TextSelectorConfig(multiline=True)
            )
        else:
            fields[vol.Optional("lan_gateway", default=self.config_entry.options.get("lan_gateway", ""))] = selector.TextSelector()
        return self.async_show_form(
            step_id="polling", errors=errors, data_schema=vol.Schema(fields)
        )
