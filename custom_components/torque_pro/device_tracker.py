# -*- coding: utf-8 -*-
"""Device tracker for Torque Pro (stable unique_id + migration via TorqueEntity)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Dict, Any
import logging

from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.components.device_tracker.const import SourceType as TrackerSourceType
from homeassistant.const import (
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    ATTR_GPS_ACCURACY,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers import device_registry as dr

from .entity import TorqueEntity
from .const import (
    ATTR_ALTITUDE,
    ATTR_VEHICLE_SPEED,
    ATTR_GPS_TIME,
    DOMAIN,
    ENTITY_GPS,
    GPS_ICON,
    TORQUE_GPS_ACCURACY,
    TORQUE_GPS_LAT,
    TORQUE_GPS_LON,
    TORQUE_GPS_ALTITUDE,
)

if TYPE_CHECKING:
    from .coordinator import TorqueCoordinator

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Setup device_tracker platform."""
    coordinator: "TorqueCoordinator" = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    coordinator.async_add_device_tracker = async_add_entities

    # Ensure the coordinator has a 'tracked' set to avoid duplicates
    try:
        if not hasattr(coordinator, "tracked") or coordinator.tracked is None:
            coordinator.tracked = set()
    except Exception:  # noqa: BLE001
        coordinator.tracked = set()

    # Restore trackers from the Device Registry (one per Torque vehicle device)
    dev_reg = dr.async_get(hass)
    devices = [
        device
        for device in dev_reg.devices.values()
        if any(ident[0] == DOMAIN for ident in device.identifiers)
    ]
    _LOGGER.debug("%d device_tracker to restore", len(devices))

    restored_entities: list[TorqueDeviceTracker] = []
    for device in devices:
        # Get car_id from device identifiers
        car_id: Optional[str] = None
        for dom, ident in device.identifiers:
            if dom == DOMAIN:
                car_id = ident
                break

        if car_id:
            # Mark as tracked to prevent coordinator from creating a duplicate
            try:
                coordinator.tracked.add(f"{car_id}:{ENTITY_GPS}")
            except Exception:  # noqa: BLE001
                _LOGGER.debug("Unable to mark %s:%s as tracked", car_id, ENTITY_GPS)

        _LOGGER.debug("Restoring device_tracker for %s", device.name or device.model)
        device_info = DeviceInfo(
            identifiers=device.identifiers,
            manufacturer=device.manufacturer or "Torque Pro",
            model=device.model,
            name=device.name,
            sw_version=device.sw_version,
        )
        restored_entities.append(TorqueDeviceTracker(coordinator, entry, device_info))

    if restored_entities:
        async_add_entities(restored_entities)


class TorqueDeviceTracker(TorqueEntity, TrackerEntity, RestoreEntity):
    """Represent a tracked device."""

    _attr_icon = GPS_ICON
    _attr_has_entity_name = True  # display name = "<Device name> GPS"

    def __init__(self, coordinator: "TorqueCoordinator", config_entry: ConfigEntry, device: DeviceInfo):
        # Base TorqueEntity sets a **stable** unique_id (DOMAIN-vehicle-gps) and
        # migrates legacy entry_id-based unique_ids in async_added_to_hass.
        super().__init__(coordinator, config_entry, ENTITY_GPS, device)
        # Human-friendly entity name; device name comes from device_info/profile
        self._attr_name = "GPS"
        self._restored_state: Optional[Dict[str, Any]] = None

    # ---- Tracker properties ----
    @property
    def battery_level(self) -> Optional[int]:
        """Return the battery level of the device (unknown)."""
        return None

    @property
    def source_type(self) -> TrackerSourceType:
        """Return the source type (GPS)."""
        return TrackerSourceType.GPS

    @property
    def location_accuracy(self) -> float:
        """Return GPS accuracy in meters (float)."""
        val = self.coordinator.get_value(self._car_id, TORQUE_GPS_ACCURACY)
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                pass

        if self._restored_state and self._restored_state.get(ATTR_GPS_ACCURACY) is not None:
            try:
                return float(self._restored_state[ATTR_GPS_ACCURACY])
            except (ValueError, TypeError):
                pass

        return 0.0

    @property
    def latitude(self) -> Optional[float]:
        """Return latitude value of the device."""
        val = self.coordinator.get_value(self._car_id, TORQUE_GPS_LAT)
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                return None

        if self._restored_state and self._restored_state.get(ATTR_LATITUDE) is not None:
            try:
                return float(self._restored_state[ATTR_LATITUDE])
            except (ValueError, TypeError):
                return None
        return None

    @property
    def longitude(self) -> Optional[float]:
        """Return longitude value of the device."""
        val = self.coordinator.get_value(self._car_id, TORQUE_GPS_LON)
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                return None

        if self._restored_state and self._restored_state.get(ATTR_LONGITUDE) is not None:
            try:
                return float(self._restored_state[ATTR_LONGITUDE])
            except (ValueError, TypeError):
                return None
        return None

    # ---- Extra attributes ----
    @property
    def extra_state_attributes(self) -> Dict[str, Any] | None:
        """Expose altitude, speed and GPS time as extra attributes."""
        attrs: Dict[str, Any] = {}

        # Altitude
        alt = self.coordinator.get_value(self._car_id, TORQUE_GPS_ALTITUDE)
        if alt is not None:
            try:
                attrs[ATTR_ALTITUDE] = float(alt)
            except (ValueError, TypeError):
                pass
        elif self._restored_state and self._restored_state.get(ATTR_ALTITUDE) is not None:
            try:
                attrs[ATTR_ALTITUDE] = float(self._restored_state[ATTR_ALTITUDE])
            except (ValueError, TypeError):
                pass

        # Speed: prefer GPS, then OBD, then generic "speed"
        spd = (
            self.coordinator.get_value(self._car_id, "gps_spd")
            or self.coordinator.get_value(self._car_id, "speed_obd")
            or self.coordinator.get_value(self._car_id, ATTR_VEHICLE_SPEED)
        )
        if spd is not None:
            try:
                attrs[ATTR_VEHICLE_SPEED] = float(spd)
            except (ValueError, TypeError):
                pass
        elif self._restored_state and self._restored_state.get(ATTR_VEHICLE_SPEED) is not None:
            try:
                attrs[ATTR_VEHICLE_SPEED] = float(self._restored_state[ATTR_VEHICLE_SPEED])
            except (ValueError, TypeError):
                pass

        # GPS timestamp (if provided by Torque)
        gps_time = self.coordinator.get_value(self._car_id, "time")
        if gps_time is not None:
            try:
                attrs[ATTR_GPS_TIME] = int(gps_time)
            except (ValueError, TypeError):
                pass
        elif self._restored_state and self._restored_state.get(ATTR_GPS_TIME) is not None:
            try:
                attrs[ATTR_GPS_TIME] = int(self._restored_state[ATTR_GPS_TIME])
            except (ValueError, TypeError):
                pass

        return attrs or None

    # ---- State restoration (on startup) ----
    async def async_added_to_hass(self) -> None:
        """Called when entity is about to be added to Home Assistant."""
        await super().async_added_to_hass()  # handles UID migration in base class
        state = await self.async_get_last_state()
        if state is None:
            _LOGGER.debug("No previous state for %s", self.entity_id)
            return

        attr = state.attributes
        _LOGGER.debug("Restored state for %s", self.entity_id)
        self._restored_state = {
            ATTR_ALTITUDE: attr.get(ATTR_ALTITUDE),
            ATTR_LATITUDE: attr.get(ATTR_LATITUDE),
            ATTR_LONGITUDE: attr.get(ATTR_LONGITUDE),
            ATTR_GPS_ACCURACY: attr.get(ATTR_GPS_ACCURACY),
            ATTR_VEHICLE_SPEED: attr.get(ATTR_VEHICLE_SPEED),
            ATTR_GPS_TIME: attr.get(ATTR_GPS_TIME),
        }
