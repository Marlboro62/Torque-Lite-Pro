# -*- coding: utf-8 -*-
"""Diagnostics support for Torque Pro (hardened).

- Redacts additional sensitive fields (vin, refresh_token, api keys)
- Defensive coordinator access (works even if missing)
- Truncates long structures for readability

Place this file at: custom_components/torque_pro/diagnostics.py
"""
from __future__ import annotations

from typing import Any, Mapping
import itertools

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.components.diagnostics import async_redact_data

from .const import (
    DOMAIN,
    TORQUE_GPS_LAT,
    TORQUE_GPS_LON,
    TORQUE_GPS_ALTITUDE,
    TORQUE_GPS_ACCURACY,
)

# -----------------------------------------------------------------------------
# Fields to redact from diagnostics output
# -----------------------------------------------------------------------------
REDACT_KEYS: set[str] = {
    # emails / identity
    "Email", "email", "eml",
    # ids & tokens
    "session", "id", "Id", "token", "access_token", "refresh_token",
    # credentials / secrets
    "client_secret", "api_key", "apikey", "x-api-key",
    # vehicle identifiers
    "vin", "VIN", "vehicle_id", "VehicleId",
    # coordinates & geodata
    TORQUE_GPS_LAT, TORQUE_GPS_LON, TORQUE_GPS_ALTITUDE, TORQUE_GPS_ACCURACY,
    "lat", "lon", "latitude", "longitude", "bearing", "heading",
}


def _safe_get(hass: HomeAssistant, entry: ConfigEntry, key: str, default: Any = None) -> Any:
    domain_store = hass.data.get(DOMAIN) or {}
    if entry.entry_id in domain_store and isinstance(domain_store[entry.entry_id], Mapping):
        return domain_store[entry.entry_id].get(key, default)
    return domain_store.get(key, default)


def _collect_view_runtime(hass: HomeAssistant) -> dict[str, Any]:
    view = (hass.data.get(DOMAIN) or {}).get("view")
    if not view:
        return {}
    # Only expose non-sensitive runtime flags
    return {
        "url": getattr(view, "url", "/api/torque_pro"),
        "requires_auth": bool(getattr(view, "requires_auth", True)),
        "imperial_units": bool(getattr(view, "imperial", False)),
        "language_runtime": getattr(view, "lang", "en"),
        "email_filter_configured": bool(getattr(view, "email", "")),
        "sessions_in_memory": len(getattr(view, "_sessions", {}) or {}),
        "ttl_seconds": int(getattr(view, "_ttl_seconds", 0) or 0),
        "max_sessions": int(getattr(view, "_max_sessions", 0) or 0),
    }


def _truncate_mapping(m: Mapping[str, Any] | None, max_items: int = 80) -> dict[str, Any]:
    if not m:
        return {}
    if len(m) <= max_items:
        return dict(m)
    # Keep first N items by key order for readability
    items = list(itertools.islice(m.items(), max_items))
    out = dict(items)
    out["__truncated__"] = f"… +{len(m) - max_items} more keys"
    return out


def _build_session_snapshot(session: Mapping[str, Any] | None) -> dict[str, Any]:
    if not session:
        return {}

    values = _truncate_mapping(session.get("values"), 120)
    meta = _truncate_mapping(session.get("meta"), 200)
    unknown = _truncate_mapping(session.get("unknown"), 80)

    payload = {
        "id": session.get("id"),  # redacted later
        "last_seen": session.get("last_seen"),
        "lang": session.get("lang"),
        "profile": dict(session.get("profile") or {}),
        "values": values,
        "meta": meta,
        "unknown": unknown,
    }
    return async_redact_data(payload, REDACT_KEYS)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    # Config (email etc.) — redact sensitive fields
    conf = async_redact_data(dict(entry.data), REDACT_KEYS)
    opts = async_redact_data(dict(entry.options), REDACT_KEYS)

    # Runtime snapshot
    view_info = _collect_view_runtime(hass)

    # Coordinator & cars (defensive defaults)
    coordinator = _safe_get(hass, entry, "coordinator") or object()
    cars = getattr(coordinator, "cars", {}) or {}
    data = getattr(coordinator, "data", {}) or {}

    # Last received session (any entry) saved by the HTTP view
    last_session = (hass.data.get(DOMAIN) or {}).get("last_session")

    # Per-vehicle light snapshots (profile + available keys)
    vehicles: dict[str, Any] = {}
    for car_id, sess in cars.items():
        meta = sess.get("meta") or {}
        values = sess.get("values") or {}
        vehicles[car_id] = async_redact_data(
            {
                "profile": dict(sess.get("profile") or {}),
                "keys": sorted(list(values.keys()))[:200],  # cap for readability
                "units": {k: (meta.get(k) or {}).get("unit") for k in list(values.keys())[:200]},
            },
            REDACT_KEYS,
        )

    out = {
        "config_entry": {"data": conf, "options": opts},
        "runtime": view_info,
        "coordinator": {
            "cars_count": len(cars),
            "tracked_count": len(getattr(coordinator, "tracked", set()) or set()),
            "exposed_data_keys": list(data.keys())[:200],  # cap for readability
        },
        "last_session": _build_session_snapshot(last_session),
        "vehicles": vehicles,
    }
    return out


async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry, device: DeviceEntry
) -> dict[str, Any]:
    """Return diagnostics for a specific device (vehicle)."""
    # Find car_id from identifiers {(DOMAIN, car_id)}
    car_id: str | None = None
    for dom, ident in device.identifiers:
        if dom == DOMAIN:
            car_id = ident
            break

    coordinator = _safe_get(hass, entry, "coordinator")
    session = None
    if coordinator and car_id:
        cars = getattr(coordinator, "cars", {}) or {}
        session = cars.get(car_id)

    # Build a compact, redacted snapshot for the vehicle
    return {
        "device": {
            "id": device.id,
            "name": device.name,
            "model": device.model,
            "manufacturer": device.manufacturer,
            "sw_version": device.sw_version,
        },
        "vehicle_id": car_id,
        "snapshot": _build_session_snapshot(session),
    }
