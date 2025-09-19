# -*- coding: utf-8 -*-
"""Base entity for the Torque Pro integration.

This wraps Home Assistant's CoordinatorEntity to:
- attach entities to a per-vehicle Device (stable identifiers)
- offer helpers to access coordinator data for a given car/key
- provide a consistent **stable** unique_id scheme independent of entry_id
- dynamically name the Device from the latest Torque profile (Name/version)

Sensors and trackers can subclass this and override presentation details
(name, icon, classes). The base class also migrates legacy unique_ids that
were based on entry_id to the new stable scheme to preserve history.
"""
from __future__ import annotations

from typing import Any, Iterable, Tuple, Optional, List
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

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

        # Micro-ajustement 1: log si car_id inconnu (aide au diagnostic)
        if self._car_id == "unknown":
            _LOGGER.warning(
                "TorqueEntity created with unknown car_id (sensor_key=%s)", self._sensor_key
            )

        # --- Stable unique_id (independent of entry_id) ---
        # Format: f"{DOMAIN}-{vehicle_id}" or f"{DOMAIN}-{vehicle_id}-{short}"
        self._attr_unique_id = self._build_stable_unique_id()

    # -------------------------
    # Unique ID helpers & migration
    # -------------------------
    def _build_stable_unique_id(self) -> str:
        """New stable unique_id that survives entry removal/re-creation."""
        base = f"{DOMAIN}-{self._car_id}"
        return f"{base}-{self._sensor_key}" if self._sensor_key else base

    def _legacy_unique_ids(self) -> List[str]:
        """All legacy unique_id formats we want to migrate from."""
        e = self._config_entry.entry_id
        c = self._car_id
        s = self._sensor_key

        legacy: list[str] = []

        # Old hyphen-based (as reported): "{entry_id}-{vehicle_id}-{short?}"
        if s:
            legacy.append(f"{e}-{c}-{s}")
        legacy.append(f"{e}-{c}")

        # Old underscore-based that existed in this base class:
        # "{DOMAIN}_{entry_id}_{vehicle_id}" + "_{short?}"
        if s:
            legacy.append(f"{DOMAIN}_{e}_{c}_{s}")
        legacy.append(f"{DOMAIN}_{e}_{c}")

        # Super defensive: "{DOMAIN}-{entry_id}-{vehicle_id}-{short?}"
        if s:
            legacy.append(f"{DOMAIN}-{e}-{c}-{s}")
        legacy.append(f"{DOMAIN}-{e}-{c}")

        # Remove duplicates while preserving order
        dedup: list[str] = []
        seen: set[str] = set()
        for uid in legacy:
            if uid not in seen:
                dedup.append(uid)
                seen.add(uid)
        return dedup

    async def async_added_to_hass(self) -> None:
        """Handle entity added: migrate legacy unique_id → stable unique_id."""
        await super().async_added_to_hass()

        try:
            # Micro-ajustement 2: fallback plus tolérant pour déterminer le domaine
            platform_domain = getattr(getattr(self, "platform", None), "domain", None)
            if not platform_domain:
                # Optionnel: permettre à un sous-classe de définir _domain si nécessaire
                platform_domain = getattr(self, "_domain", None)
            if not platform_domain:
                # Dernier recours: heuristique sur le nom de classe
                name = self.__class__.__name__.lower()
                if "sensor" in name:
                    platform_domain = "sensor"
                elif "tracker" in name or "device" in name:
                    platform_domain = "device_tracker"

            if not platform_domain:
                # Si on ne peut toujours pas déterminer, on abandonne proprement
                _LOGGER.debug("Could not resolve platform domain for %s; skip UID migration", self)
                return

            registry = er.async_get(self.hass)
            new_uid = self._build_stable_unique_id()

            # If registry already uses the new UID, nothing to do.
            existing_new = registry.async_get_entity_id(platform_domain, DOMAIN, new_uid)
            if existing_new:
                return

            # Look for any legacy UID and migrate the first match.
            for old_uid in self._legacy_unique_ids():
                ent_id = registry.async_get_entity_id(platform_domain, DOMAIN, old_uid)
                if ent_id:
                    _LOGGER.debug(
                        "Migrating %s unique_id from '%s' to '%s' for entity %s",
                        platform_domain,
                        old_uid,
                        new_uid,
                        ent_id,
                    )
                    registry.async_update_entity(ent_id, new_unique_id=new_uid)
                    break

            # Ensure the entity object reports the stable UID
            self._attr_unique_id = new_uid

        except Exception:  # noqa: BLE001
            _LOGGER.exception("TorqueEntity unique_id migration failed")

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

    @staticmethod
    def _is_poor_name(name: str | None, car_id: str) -> bool:
        if not name:
            return True
        s = name.strip()
        return (not s) or (s.lower() in {"vehicle", "véhicule"}) or (s == car_id)

    @property
    def device_info(self) -> DeviceInfo | dict:
        """DeviceInfo for the vehicle, with robust name/version fallbacks.

        Priority:
        1) profile Name if valid
        2) name/model from stored device_info (passed at __init__)
        3) name/model from Device Registry (if the device already exists)
        4) synthetic "Vehicle ABCDEF" (short car_id) to avoid hash-y names
        """
        # Identifiers (support both DeviceInfo and dict)
        idents = getattr(self._device_info, "identifiers", None)
        if idents is None and isinstance(self._device_info, dict):
            idents = self._device_info.get("identifiers")
        if not idents:
            idents = {(DOMAIN, self._car_id)}

        # Candidates from stored device_info
        stored_name = getattr(self._device_info, "name", None)
        if stored_name is None and isinstance(self._device_info, dict):
            stored_name = self._device_info.get("name")

        stored_model = getattr(self._device_info, "model", None)
        if stored_model is None and isinstance(self._device_info, dict):
            stored_model = self._device_info.get("model")

        stored_sw = getattr(self._device_info, "sw_version", None)
        if stored_sw is None and isinstance(self._device_info, dict):
            stored_sw = self._device_info.get("sw_version")

        prof = self.coordinator_profile() or {}
        raw_name = (prof.get("Name") or prof.get("name") or "").strip()
        sw_ver = prof.get("version") or stored_sw

        # Choose effective name
        if not self._is_poor_name(raw_name, self._car_id):
            effective_name = raw_name
        else:
            effective_name = (stored_name or stored_model or "").strip()

            # Last resort: read Device Registry (may already hold a human name)
            if self._is_poor_name(effective_name, self._car_id):
                try:
                    dev_reg = dr.async_get(self.hass)
                    dev = dev_reg.async_get_device(identifiers={(DOMAIN, self._car_id)})
                    if dev and (dev.name or dev.model):
                        effective_name = (dev.name or dev.model or "").strip()
                except Exception:  # noqa: BLE001
                    pass

        # Synthetic fallback (avoid exposing the raw hash)
        if self._is_poor_name(effective_name, self._car_id):
            short_id = (self._car_id or "").strip()[:6] or "unknown"
            effective_name = f"Vehicle {short_id}"

        out: dict[str, Any] = {
            "identifiers": idents,
            "manufacturer": "Torque Pro",
        }
        if effective_name:
            out["name"] = effective_name
            out["model"] = effective_name
        if sw_ver:
            out["sw_version"] = sw_ver

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
