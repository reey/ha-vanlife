from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import VanLifeCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: VanLifeCoordinator = hass.data[DOMAIN][entry.entry_id]
    known_ids: set[str] = set()

    @callback
    def _check_for_new_devices() -> None:
        new_entities = [
            VanLifeTrackerEntity(coordinator, device_id)
            for device_id in coordinator.data
            if device_id not in known_ids
        ]
        if new_entities:
            known_ids.update(e.device_id for e in new_entities)
            async_add_entities(new_entities)

    _check_for_new_devices()
    # Keep checking on subsequent coordinator updates to catch newly bound bikes.
    entry.async_on_unload(coordinator.async_add_listener(_check_for_new_devices))


class VanLifeTrackerEntity(CoordinatorEntity[VanLifeCoordinator], TrackerEntity):
    """Represents a single Vanebike as a device tracker entity."""

    _attr_has_entity_name = True
    _attr_name = None  # use device name as the entity name

    def __init__(self, coordinator: VanLifeCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self.device_id = device_id
        self._attr_unique_id = f"vanlife_{device_id}"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def _data(self) -> dict[str, Any]:
        return self.coordinator.data.get(self.device_id, {})

    @property
    def _device(self) -> dict[str, Any]:
        return self._data.get("device") or {}

    @property
    def _position(self) -> dict[str, Any] | None:
        return self._data.get("position")

    # ------------------------------------------------------------------
    # TrackerEntity contract
    # ------------------------------------------------------------------

    @property
    def available(self) -> bool:
        return self.device_id in self.coordinator.data

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        pos = self._position
        if pos and pos.get("lat") is not None:
            return pos["lat"] / 1e7
        return None

    @property
    def longitude(self) -> float | None:
        pos = self._position
        if pos and pos.get("lng") is not None:
            return pos["lng"] / 1e7
        return None

    @property
    def location_accuracy(self) -> int:
        return 0

    # ------------------------------------------------------------------
    # HA entity metadata
    # ------------------------------------------------------------------

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.device_id)},
            name=self._device.get("device_name") or f"VanLife {self.device_id}",
            manufacturer="Vanebike",
            model=self._device.get("model_name") or self._device.get("device_model"),
            serial_number=self._device.get("device_serial_number"),
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        pos = self._position or {}
        raw_ts = pos.get("timestamp")
        timestamp = (
            datetime.fromtimestamp(raw_ts, tz=timezone.utc).isoformat()
            if raw_ts is not None
            else None
        )
        return {
            "is_moving": self._data.get("is_moving", False),
            "order_id": self._device.get("order_id"),
            "frame_id": self._device.get("device_frame_id"),
            "bt_mac": self._device.get("device_bt_mac"),
            "last_gps_report": timestamp,
        }
