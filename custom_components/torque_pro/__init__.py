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
from homeassistant.exceptions import ConfigEntryNotReady

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


def _log(level: int, emoji: str, msg: str, *args, exc_info: bool = False) -> None:
    """Helper pour logs homogènes avec emoji + placeholders %s."""
    _LOGGER.log(level, "%s " + msg, emoji, *args, exc_info=exc_info)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register static assets once (if folder exists). YAML setup not used."""
    static_dir = hass.config.path("custom_components/torque_pro/www")
    domain_store: dict[str, Any] = hass.data.setdefault(DOMAIN, {})
    if not domain_store.get("_static_registered"):
        if os.path.isdir(static_dir):
            try:
                hass.http.register_static_path("/torque_pro", static_dir)
                _LOGGER.debug("Static path /torque_pro registered from %s", static_dir)
            except Exception as err:  # noqa: BLE001
                _log(logging.WARNING, "⚠️", "Torque Pro problème — échec register_static_path: %s", err, exc_info=True)
            else:
                domain_store["_static_registered"] = True
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

    # Vue HTTP : la créer UNE fois, puis seulement MAJ de ses paramètres partagés (TTL, max...)
    if "view" not in domain_store:
        try:
            view = TorqueReceiveDataView(
                hass,
                email_filter=email,            # compat héritée ; non utilisée en mode multi-route
                imperial_units=imperial,       # valeur par défaut (route-specific override ensuite)
                default_language=lang_rt,      # valeur par défaut (route-specific override ensuite)
                session_ttl_seconds=session_ttl_seconds,
                max_sessions=max_sessions,
            )
        except Exception as err:  # noqa: BLE001
            _log(logging.ERROR, "⛔️", "Torque Pro non démarré — création de la vue a échoué: %s", err, exc_info=True)
            raise ConfigEntryNotReady from err

        try:
            hass.http.register_view(view)
        except Exception as err:  # noqa: BLE001
            _log(logging.ERROR, "⛔️", "Torque Pro non démarré — register_view a échoué: %s", err, exc_info=True)
            raise ConfigEntryNotReady from err

        domain_store["view"] = view
        _LOGGER.debug(
            "Torque view registered at %s (ttl=%s, max=%s, lang=%s, imperial=%s)",
            view.url, session_ttl_seconds, max_sessions, lang_rt, imperial,
        )
    else:
        view: TorqueReceiveDataView = domain_store["view"]
        try:
            # MAJ des paramètres runtime **partagés** de la vue
            view.lang = lang_rt                # défaut d'UI/lang
            view.imperial = bool(imperial)     # défaut d'UI/unité
            view._ttl_seconds = int(session_ttl_seconds)
            view._max_sessions = int(max_sessions)
        except Exception as err:  # noqa: BLE001
            _log(logging.WARNING, "⚠️", "Torque Pro problème — mise à jour des paramètres de la vue: %s", err, exc_info=True)
        else:
            _LOGGER.debug(
                "Torque view updated (default_lang=%s, default_imperial=%s, ttl=%s, max=%s)",
                view.lang, view.imperial, view._ttl_seconds, view._max_sessions,
            )

    # Store par entrée
    store: dict[str, Any] = {}
    domain_store[entry.entry_id] = store

    # Coordinator (global + par entrée pour compat)
    try:
        coordinator = TorqueCoordinator(hass, domain_store["view"], entry)
    except Exception as err:  # noqa: BLE001
        _log(logging.ERROR, "⛔️", "Torque Pro non démarré — initialisation du coordinator a échoué: %s", err, exc_info=True)
        raise ConfigEntryNotReady from err

    # Attachements & multi-entry routing
    view = domain_store["view"]
    try:
        # Route dédiée à CETTE entrée (email/coordinator/lang/unité spécifiques)
        view.upsert_route(
            entry.entry_id,
            email=email or None,
            coordinator=coordinator,
            imperial=bool(imperial),
            lang=lang_rt,
        )
        view.set_active(True)  # la vue devient active tant qu'au moins une route existe
    except Exception as err:  # noqa: BLE001
        _log(logging.WARNING, "⚠️", "Torque Pro problème — upsert_route a échoué: %s", err, exc_info=True)

    # Stocker pour accès plateformes
    try:
        store["coordinator"] = coordinator
        # Gardé pour compat éventuelle (legacy code lisant hass.data[DOMAIN]['coordinator'])
        hass.data[DOMAIN]["coordinator"] = coordinator
    except Exception as err:  # noqa: BLE001
        _log(logging.WARNING, "⚠️", "Torque Pro problème — stockage coordinator: %s", err, exc_info=True)

    # Charger les plateformes
    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception as err:  # noqa: BLE001
        _log(logging.ERROR, "⛔️", "Torque Pro non démarré — chargement des plateformes a échoué: %s", err, exc_info=True)
        raise ConfigEntryNotReady from err

    # ✅ Message clair dans les journaux une fois l’entrée prête
    try:
        view_url = view.url if view else "(n/a)"
    except Exception:  # noqa: BLE001
        view_url = "(n/a)"

    _log(
        logging.INFO,
        "✅",
        "Torque Pro ok — view=%s, entry=%s, email=%s, lang=%s, imperial=%s, session_ttl=%s, max_sessions=%s",
        view_url,
        entry.entry_id,
        email or "(any)",
        lang_rt,
        imperial,
        session_ttl_seconds,
        max_sessions,
    )

    # Reload si options changent
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload platforms and detach this entry from the view/coordinator."""
    results = await asyncio.gather(
        *[hass.config_entries.async_forward_entry_unload(entry, platform) for platform in PLATFORMS],
        return_exceptions=True,
    )
    if not all(r is True for r in results):
        _log(logging.WARNING, "⚠️", "Torque Pro problème — déchargement partiel des plateformes: %s", results)

    domain_store: dict[str, Any] = hass.data.get(DOMAIN, {})
    # Retire les données spécifiques à l'entrée
    domain_store.pop(entry.entry_id, None)

    view: TorqueReceiveDataView | None = domain_store.get("view")

    # Supprimer la route associée à cette entrée (vue persistante mais potentiellement inactive)
    if view:
        try:
            view.remove_route(entry.entry_id)
            _LOGGER.debug(
                "Removed route for entry=%s; view active=%s",
                entry.entry_id,
                getattr(view, "is_active", lambda: True)(),
            )
        except Exception:  # noqa: BLE001
            _log(logging.WARNING, "⚠️", "Torque Pro problème — remove_route(%s) a échoué", entry.entry_id, exc_info=True)

    # Déterminer s'il reste des entrées actives
    still_has_entries = any(
        k for k in domain_store.keys() if k not in {"view", "coordinator", "_static_registered", "initialized"}
    )

    if view and not still_has_entries:
        # Détacher le coordinator global legacy ; la vue restera enregistrée mais inactive
        try:
            view.coordinator = None
        except Exception:
            pass
        domain_store.pop("coordinator", None)
        _LOGGER.debug("Torque view kept registered but detached/inactive (no active entries).")

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    _LOGGER.info("♻️ Reloading Torque Pro entry %s ...", entry.entry_id)
    try:
        await async_unload_entry(hass, entry)
        await async_setup_entry(hass, entry)
    except Exception as err:  # noqa: BLE001
        _log(logging.ERROR, "⛔️", "Torque Pro non démarré — reload a échoué: %s", err, exc_info=True)
        return
    _log(logging.INFO, "✅", "Torque Pro ok — reloaded — entry=%s", entry.entry_id)


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
                _log(logging.WARNING, "⚠️", "Torque Pro problème — forget_vehicle(%s) a échoué: %s", vkey, err, exc_info=True)

    return True
