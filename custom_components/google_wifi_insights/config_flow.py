"""UI setup; Google credentials are entered directly in Home Assistant."""

import hashlib
import re
import secrets

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ApiError, AuthError, CloudClient, LocalClient, google_auth
from .const import DEFAULT_INTERVAL, DOMAIN, MIN_INTERVAL
from .model import parse_points


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

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
        errors = {}
        reauth_entry = (
            self._get_reauth_entry()
            if self.source == config_entries.SOURCE_REAUTH
            else None
        )
        if not hasattr(self, "_android_id"):
            self._android_id = (
                reauth_entry.data["android_id"]
                if reauth_entry
                else secrets.token_hex(8)
            )
        if user_input is not None:
            email, token = (
                user_input["email"].strip().lower(),
                user_input["oauth_token"].strip(),
            )
            android_id = user_input["android_id"].strip()
            if "@" not in email or not re.fullmatch(r"[a-fA-F0-9]{16}", android_id):
                errors["base"] = "invalid_input"
            elif reauth_entry and email != reauth_entry.data["email"]:
                errors["base"] = "account_mismatch"
            elif not token.startswith(("oauth2_4/", "aas_et/", "oauth2rt_1/")):
                errors["base"] = "invalid_token"
            else:
                try:
                    if token.startswith("oauth2_4/"):
                        result = await self.hass.async_add_executor_job(
                            google_auth, email, token, android_id, True
                        )
                        token = result["Token"]
                    client = CloudClient(
                        async_get_clientsession(self.hass),
                        self.hass.async_add_executor_job,
                        email,
                        token,
                        android_id,
                    )
                    await client.snapshot()
                except AuthError:
                    errors["base"] = "invalid_auth"
                except ApiError:
                    errors["base"] = "cannot_connect"
                else:
                    data = {
                        "mode": "cloud",
                        "email": email,
                        "master_token": token,
                        "android_id": android_id,
                    }
                    if reauth_entry:
                        return self.async_update_reload_and_abort(
                            reauth_entry, data_updates=data
                        )
                    await self.async_set_unique_id(
                        "cloud:" + hashlib.sha256(email.encode()).hexdigest()
                    )
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title="Google WiFi Insights", data=data
                    )
        defaults = user_input or (reauth_entry.data if reauth_entry else {})
        return self.async_show_form(
            step_id="cloud",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required("email", default=defaults.get("email", "")): str,
                    vol.Required("oauth_token"): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        )
                    ),
                    vol.Required(
                        "android_id",
                        default=defaults.get("android_id", self._android_id),
                    ): str,
                }
            ),
        )

    async def async_step_reauth(self, entry_data):
        return await self.async_step_cloud()


class OptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
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
            if not errors:
                return self.async_create_entry(
                    title="", data={"scan_interval": user_input["scan_interval"]}
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
        return self.async_show_form(
            step_id="init", errors=errors, data_schema=vol.Schema(fields)
        )
