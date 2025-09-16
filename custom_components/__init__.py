# -*- coding: utf-8 -*-
"""The Torque Pro integration with Home Assistant."""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from .coordinator import TorqueCoordinator
from .api import TorqueReceiveDataView
from .const import (
    DOMAIN,
    PLATFORMS,
    STARTUP_MESSAGE,
    # Config data/options
    CONF_EMAIL,
    CONF_IMPERIAL,
    CONF_LANGUAGE,
    DEFAULT_LANGUAGE,
    RUNTIME_LANG_MAP,
    # Mémoire sessions (options + défauts)
    CONF_SESSION_TTL,
    CONF_MAX_SESSIONS,
    SESSION_TTL_SECONDS,
    MAX_SESSIONS,
)

_LOGGER: logging.Logger = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register static assets once (if folder exists). YAML setup not used."""
    static_dir = hass.config.path("custom_components/torque_pro/www")
    # Empêcher un double enregistrement après restart/Reload
    domain_store: dict[str, Any] = hass.data.setdefault(DOMAIN, {})
    if not domain_store.get("_static_registered"):
        if os.path.isdir(static_dir):
            try:
                hass.http.register_static_path("/torque_pro", static_dir)
                _LOGGER.debug("Static path /torque_pro registered from %s", static_dir)
            except Exception:  # noqa: BLE001
                _LOGGER.debug("Static path /torque_pro already registered or failed", exc_info=True)
        else:
            _LOGGER.debug("Static dir does not exist: %s", static_dir)
        domain_store["_static_registered"] = True
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old entry data to the latest version.

    - v<2 -> v2 : injecte la langue par défaut si absente.
    """
    if entry.version < 2:
        data = dict(entry.data)
        if CONF_LANGUAGE not in data:
            data[CONF_LANGUAGE] = DEFAULT_LANGUAGE
        hass.config_entries.async_update_entry(entry, data=data, version=2)
        _LOGGER.debug("Migrated config entry %s to version 2", entry.entry_id)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration via the UI."""
    # Espace de stockage du domaine
    domain_store: dict[str, Any] = hass.data.setdefault(DOMAIN, {})
    if "initialized" not in domain_store:
        _LOGGER.info(STARTUP_MESSAGE)
        domain_store["initialized"] = True

    # Données + options (fallback sur data)
    email = entry.data.get(CONF_EMAIL, "")
    imperial = entry.options.get(CONF_IMPERIAL, entry.data.get(CONF_IMPERIAL, False))
    language = entry.options.get(CONF_LANGUAGE, entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE))

    # Options mémoire sessions (avec fallback sur défauts)
    session_ttl_seconds = int(entry.options.get(CONF_SESSION_TTL, SESSION_TTL_SECONDS))
    max_sessions = int(entry.options.get(CONF_MAX_SESSIONS, MAX_SESSIONS))

    # Normalisation de la langue côté runtime (API ne gère que fr/en pour l’instant)
    sel = (language or DEFAULT_LANGUAGE).lower()
    lang_rt = RUNTIME_LANG_MAP.get(sel, "en")

    # Vue HTTP : la créer UNE fois, puis seulement MAJ de ses paramètres
    if "view" not in domain_store:
        view = TorqueReceiveDataView(
            hass,
            email_filter=email,
            imperial_units=imperial,
            default_language=lang_rt,
            session_ttl_seconds=session_ttl_seconds,
            max_sessions=max_sessions,
        )
        hass.http.register_view(view)
        domain_store["view"] = view
        _LOGGER.debug(
            "Torque view registered at %s (ttl=%s, max=%s, lang=%s, imperial=%s)",
            view.url, session_ttl_seconds, max_sessions, lang_rt, imperial,
        )
    else:
        view: TorqueReceiveDataView = domain_store["view"]
        # MAJ des paramètres runtime de la vue
        view.email = email or ""
        view.imperial = bool(imperial)
        view.lang = lang_rt
        # MAJ de l’échelle mémoire
        view._ttl_seconds = int(session_ttl_seconds)
        view._max_sessions = int(max_sessions)
        _LOGGER.debug(
            "Torque view updated (email=%s, imperial=%s, lang=%s, ttl=%s, max=%s)",
            view.email, view.imperial, view.lang, view._ttl_seconds, view._max_sessions,
        )

    # Store par entrée
    store: dict[str, Any] = {}
    domain_store[entry.entry_id] = store

    # Coordinator (global + par entrée pour compat)
    coordinator = TorqueCoordinator(hass, domain_store["view"], entry)
    domain_store["view"].coordinator = coordinator
    store["coordinator"] = coordinator
    # Gardé pour compat éventuelle, mais pas nécessaire si les plateformes lisent l’entrée
    domain_store["coordinator"] = coordinator

    # Charger les plateformes
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload si options changent
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload platforms and detach this entry from the view/coordinator."""
    results = await asyncio.gather(
        *[hass.config_entries.async_forward_entry_unload(entry, platform) for platform in PLATFORMS]
    )
    if not all(results):
        return False

    domain_store: dict[str, Any] = hass.data.get(DOMAIN, {})
    domain_store.pop(entry.entry_id, None)

    still_has_entries = any(k for k in domain_store.keys() if k not in {"view", "coordinator", "_static_registered"})
    view: TorqueReceiveDataView | None = domain_store.get("view")

    if view and not still_has_entries:
        # Détacher la vue (URL reste vivante) et purger l'ancien coordinator global
        view.coordinator = None
        domain_store.pop("coordinator", None)
        _LOGGER.debug("Torque view kept registered but detached (no active entries).")

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def async_remove_config_entry_device(
    hass: HomeAssistant,
    entry: ConfigEntry,
    device_entry: DeviceEntry,
) -> bool:
    """Autoriser la suppression d’un appareil (véhicule) depuis l’UI."""
    _LOGGER.debug("Removing device identifiers=%s", device_entry.identifiers)

    try:
        coordinator: TorqueCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    except KeyError:
        return True

    vehicle_keys = [id2 for (dom, id2) in device_entry.identifiers if dom == DOMAIN]

    for vkey in vehicle_keys:
        forget = getattr(coordinator, "forget_vehicle", None)
        if callable(forget):
            try:
                forget(vkey)
                _LOGGER.debug("Vehicle %s forgotten in coordinator", vkey)
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("forget_vehicle(%s) failed: %s", vkey, err)

    return True
