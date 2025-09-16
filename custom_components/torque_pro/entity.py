# -*- coding: utf-8 -*-
"""Base entity for the Torque Pro integration.

This wraps Home Assistant's CoordinatorEntity to:
- attach entities to a per-vehicle Device (stable identifiers)
- offer helpers to access coordinator data for a given car/key
- provide a consistent default unique_id scheme
- dynamically name the Device from the latest Torque profile (Name/version)

Sensors and trackers can subclass this and override presentation details
(name, icon, classes) and even the unique_id when maintaining legacy IDs.
"""
from __future__ import annotations

from typing import Any, Iterable, Optional, Tuple
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class TorqueEntity(CoordinatorEntity):
    """Base class binding an entity to a Torque vehicle and coordinator."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        config_entry: ConfigEntry,
        sensor_key: str | None,
        device_info: DeviceInfo | dict,
        *,
        vehicle_id: str | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._sensor_key = (sensor_key or "").strip()

        # Keep a copy; expose via property (DeviceInfo or dict)
        self._device_info: DeviceInfo | dict = device_info

        # Derive car id, prefer explicit param; accept DeviceInfo or dict
        idents = getattr(device_info, "identifiers", None)
        if idents is None and isinstance(device_info, dict):
            idents = device_info.get("identifiers")
        self._car_id = (vehicle_id or self._extract_vehicle_id(idents)) or "unknown"

        # Default UID (children can override to preserve legacy IDs)
        self._attr_unique_id = f"{DOMAIN}_{config_entry.entry_id}_{self._car_id}"
        if self._sensor_key:
            self._attr_unique_id += f"_{self._sensor_key}"

    # -------------------------
    # Device / identifiers
    # -------------------------
    @staticmethod
    def _extract_vehicle_id(identifiers: Optional[Iterable[Tuple[str, str]]]) -> str | None:
        if not identifiers:
            return None
        try:
            for domain, veh in identifiers:
                if domain == DOMAIN and veh:
                    return veh
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Bad identifiers payload on DeviceInfo/dict identifiers")
        return None

    @property
    def device_info(self) -> DeviceInfo | dict:
        """DeviceInfo for the vehicle, with dynamic name/version from the profile.

        Works whether the stored device_info is a DeviceInfo or a plain dict.
        """
        # Identifiers (support both DeviceInfo and dict)
        idents = getattr(self._device_info, "identifiers", None)
        if idents is None and isinstance(self._device_info, dict):
            idents = self._device_info.get("identifiers")
        if not idents:
            idents = {(DOMAIN, self._car_id)}

        prof = self.coordinator_profile() or {}
        out: dict[str, Any] = {
            "identifiers": idents,
            "manufacturer": "Torque Pro",
        }

        name = prof.get("Name") or prof.get("name")
        if name:
            out["name"] = name

        ver = prof.get("version")
        if ver:
            out["sw_version"] = ver

        return out

    # -------------------------
    # Convenience helpers
    # -------------------------
    @property
    def car_id(self) -> str:
        return self._car_id

    @property
    def sensor_key(self) -> str:
        return self._sensor_key

    def coordinator_vehicle(self) -> dict[str, Any] | None:
        data = getattr(self.coordinator, "data", {}) or {}
        return data.get(self._car_id)

    def coordinator_profile(self) -> dict[str, Any] | None:
        veh = self.coordinator_vehicle()
        if not veh:
            return None
        return veh.get("profile") or None

    def coordinator_values(self) -> dict[str, Any]:
        veh = self.coordinator_vehicle() or {}
        return veh.get("values") or {}

    def get_coordinator_value(self, key: str) -> Any:
        # Prefer dedicated API when available
        getv = getattr(self.coordinator, "get_value", None)
        if callable(getv):
            try:
                return getv(self._car_id, key)
            except Exception:  # noqa: BLE001
                _LOGGER.debug("Coordinator.get_value failed for %s/%s", self._car_id, key)
        return self.coordinator_values().get(key)

    # -------------------------
    # Availability (optional TTL logic at coordinator level)
    # -------------------------
    @property
    def available(self) -> bool:
        has_data = self.coordinator_vehicle() is not None
        if not has_data:
            return super().available
        # If coordinator exposes a freshness check, use it
        is_fresh = getattr(self.coordinator, "is_vehicle_fresh", None)
        if callable(is_fresh):
            try:
                return bool(is_fresh(self._car_id))
            except Exception:  # noqa: BLE001
                return True
        return True
