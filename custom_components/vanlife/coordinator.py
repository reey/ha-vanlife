from __future__ import annotations

import hashlib
import logging
import time
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    APP_INFO_HEADER,
    CONF_BASE_URL,
    DEFAULT_BASE_URL,
    DOMAIN,
    MOVING_THRESHOLD_SECS,
    POLL_INTERVAL_MOVING,
    POLL_INTERVAL_STATIONARY,
)

_LOGGER = logging.getLogger(__name__)


class VanLifeCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls the VanLife cloud API and adjusts frequency based on movement."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._entry = entry
        self._base_url: str = entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL)
        self._email: str = entry.data["email"]
        self._password: str = entry.data["password"]
        self._session_uid: str | None = None
        self._session_token: str | None = None

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=POLL_INTERVAL_STATIONARY),
        )

    # ------------------------------------------------------------------
    # Low-level HTTP helpers
    # ------------------------------------------------------------------

    def _headers(self, *, authenticated: bool = True) -> dict[str, str]:
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "app-info": APP_INFO_HEADER,
        }
        if authenticated and self._session_token:
            headers["Cookie"] = f"uid={self._session_uid}; token={self._session_token}"
        return headers

    async def _post(self, path: str, body: dict, *, authenticated: bool = True) -> dict:
        session = async_get_clientsession(self.hass)
        resp = await session.post(
            f"{self._base_url}{path}",
            json=body,
            headers=self._headers(authenticated=authenticated),
        )
        resp.raise_for_status()
        return await resp.json(content_type=None)

    # ------------------------------------------------------------------
    # API calls
    # ------------------------------------------------------------------

    async def _login(self) -> None:
        encoded = (
            hashlib.sha256(f"email={self._email}&password={self._password}".encode())
            .hexdigest()
            .lower()
        )
        res = await self._post(
            "/api/v1/account/login_by_password",
            {"email": self._email, "password": encoded},
            authenticated=False,
        )
        if res.get("code") != 0 or not res.get("data", {}).get("token"):
            raise UpdateFailed(f"Login failed: {res.get('message', res)}")
        self._session_uid = res["data"]["uid"]
        self._session_token = res["data"]["token"]
        _LOGGER.debug("VanLife: logged in as uid=%s", self._session_uid)

    async def _fetch_devices(self) -> list[dict]:
        res = await self._post(
            "/api/v1/device-mgr/query-self-bind",
            {"page": 0, "page_size": 50},
        )
        if res.get("code") != 0:
            raise UpdateFailed(f"device list error: {res.get('message', res)}")
        data = res.get("data") or {}
        if isinstance(data, list):
            return data
        return data.get("items") or []

    async def _fetch_position(self, order_id: str) -> dict | None:
        res = await self._post(
            "/api/v1/device-mgr/get_latest_position",
            {"order_id": order_id},
        )
        if res.get("code") != 0:
            _LOGGER.debug("VanLife: no position for order %s – %s", order_id, res.get("message"))
            return None
        return res.get("data")

    # ------------------------------------------------------------------
    # Coordinator update
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> dict[str, Any]:
        if not self._session_token:
            await self._login()

        # Refresh device list every cycle so newly bound bikes are discovered.
        try:
            devices = await self._fetch_devices()
        except UpdateFailed:
            # Likely a stale session; re-authenticate once and retry.
            _LOGGER.info("VanLife: fetch failed, refreshing session")
            await self._login()
            devices = await self._fetch_devices()

        result: dict[str, Any] = {}
        any_moving = False

        for device in devices:
            device_id = str(device.get("device_id") or "")
            order_id = str(device.get("order_id") or "")
            if not device_id or not order_id:
                continue

            position = await self._fetch_position(order_id)
            is_moving = False
            if position and position.get("timestamp"):
                age_secs = time.time() - float(position["timestamp"])
                is_moving = age_secs < MOVING_THRESHOLD_SECS

            if is_moving:
                any_moving = True

            result[device_id] = {
                "device": device,
                "position": position,
                "is_moving": is_moving,
            }

        # Dynamically slow down or speed up polling.
        desired_interval = timedelta(
            seconds=POLL_INTERVAL_MOVING if any_moving else POLL_INTERVAL_STATIONARY
        )
        if self.update_interval != desired_interval:
            _LOGGER.debug(
                "VanLife: adjusting poll interval to %ss (%s)",
                desired_interval.total_seconds(),
                "moving" if any_moving else "stationary",
            )
            self.update_interval = desired_interval

        return result
