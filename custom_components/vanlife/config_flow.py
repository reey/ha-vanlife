from __future__ import annotations

import hashlib
import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import APP_INFO_HEADER, CONF_BASE_URL, DEFAULT_BASE_URL, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required("email"): str,
        vol.Required("password"): str,
        vol.Optional(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
    }
)


async def _validate_credentials(hass, base_url: str, email: str, password: str) -> str:
    """Return uid on success, raise ValueError on auth failure."""
    encoded = (
        hashlib.sha256(f"email={email}&password={password}".encode())
        .hexdigest()
        .lower()
    )
    session = async_get_clientsession(hass)
    resp = await session.post(
        f"{base_url}/api/v1/account/login_by_password",
        json={"email": email, "password": encoded},
        headers={
            "Content-Type": "application/json",
            "app-info": APP_INFO_HEADER,
        },
    )
    resp.raise_for_status()
    data = await resp.json(content_type=None)
    if data.get("code") != 0 or not data.get("data", {}).get("token"):
        raise ValueError(data.get("message", "unknown error"))
    return str(data["data"]["uid"])


class VanLifeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial setup of a VanLife account."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            email = user_input["email"].strip()
            base_url = user_input[CONF_BASE_URL].rstrip("/")

            try:
                uid = await _validate_credentials(
                    self.hass, base_url, email, user_input["password"]
                )
            except ValueError:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected error during VanLife login")
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(uid)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"VanLife ({email})",
                    data={
                        "email": email,
                        "password": user_input["password"],
                        CONF_BASE_URL: base_url,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )
