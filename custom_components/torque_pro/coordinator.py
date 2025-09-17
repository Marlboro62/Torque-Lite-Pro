# -*- coding: utf-8 -*-
"""Coordinator for Torque Pro."""
from __future__ import annotations

from typing import Any, Optional, Callable, Iterable, Tuple
import logging
import math  # filtre inf/nan

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers import device_registry as dr
from homeassistant.util import slugify

from .const import DOMAIN, ENTITY_GPS, TORQUE_GPS_LAT, TORQUE_GPS_LON
from .device_tracker import TorqueDeviceTracker  # créé ici si GPS dispo

_LOGGER: logging.Logger = logging.getLogger(__name__)


# --- helpers non-fini ---
_NONFINITE_STR = {"inf", "+inf", "-inf", "infinity", "nan"}


def _is_non_finite(v: Any) -> bool:
    """True si v est inf/-inf/nan (numérique) ou une chaîne équivalente."""
    try:
        if isinstance(v, (int, float)):
            return not math.isfinite(float(v))
        if isinstance(v, str):
            return v.strip().lower() in _NONFINITE_STR
    except Exception:
        return True
    return False


class TorqueCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]] | None]):
    """Coordonnateur central de Torque Pro (gère entités & véhicules)."""

    # Callback fourni par sensor.py pour ajouter dynamiquement des sensors
    _sensor_adder: Optional[Callable[[str, str, dict[str, Any]], None]] = None
    # Callback AddEntities pour les device_tracker (fourni par platform device_tracker)
    async_add_device_tracker: Optional[Callable[[list[Any]], None]] = None

    def __init__(
        self,
        hass: HomeAssistant,
        view: Any,
        entry: ConfigEntry,
    ) -> None:
        # Pas d'update_interval: on pousse les données à l'arrivée
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=None)
        self.hass = hass
        self.entry = entry
        self.view = view
        view.coordinator = self

        # Capteurs/trackers déjà créés (car_id:short) / (car_id:ENTITY_GPS)
        self.tracked: set[str] = set()

        # Données par véhicule (dernière session reçue)
        self.cars: dict[str, dict[str, Any]] = {}

        # Données exposées aux entités (CoordinatorEntity lit self.data)
        # On expose un dict {car_id: session}
        self.data: dict[str, dict[str, Any]] = {}

    async def _async_update_data(self) -> dict[str, dict[str, Any]] | None:
        """Pas de polling : fonctionnement uniquement en push."""
        return self.data

    # ---------- API pour sensor.py ----------
    def set_sensor_adder(self, adder: Callable[[str, str, dict[str, Any]], None]) -> None:
        """Enregistre le callback d'ajout dynamique de sensors (fourni par sensor.py)."""
        self._sensor_adder = adder

    def iter_current_sensors(self) -> Iterable[Tuple[str, str, dict[str, Any]]]:
        """Énumère l'ensemble des (veh_id, short, meta) 'créables' à l'instant T."""
        for car_id, session in self.cars.items():
            meta_map = session.get("meta") or {}
            for short, meta in meta_map.items():
                if not self._is_creatable_sensor(short, meta):
                    continue
                yield (car_id, short, meta)

    # ---------- Utilitaires ----------
    @staticmethod
    def _is_textual_sensor(name: str) -> bool:
        """Retourne True si le capteur est textuel pertinent."""
        if not name:
            return False
        n = name.strip().lower()
        return n.endswith(("status", "state", "mode")) or "état" in n or "statut" in n

    def _is_creatable_sensor(self, short: str, meta: dict[str, Any]) -> bool:
        """Filtre commun pour éviter de créer des capteurs inutiles."""
        if short in (TORQUE_GPS_LAT, TORQUE_GPS_LON):
            return False
        name = (meta.get("name") or short).strip()
        unit = (meta.get("unit") or "").strip()
        if unit == "" and not self._is_textual_sensor(name):
            return False
        if name == short:  # noms peu descriptifs -> éviter
            return False
        return True

    def get_value(self, car_id: str, key: str) -> Any:
        """Récupère une valeur dans self.cars[car_id]['values'][key], filtrée."""
        data = self.cars.get(car_id)
        if not data:
            return None
        val = (data.get("values") or {}).get(key)
        return None if _is_non_finite(val) else val  # garde-fou

    def get_meta(self, car_id: str) -> dict[str, Any]:
        """Récupère la map meta pour un véhicule."""
        data = self.cars.get(car_id)
        if not data:
            return {}
        return data.get("meta", {})  # type: ignore[return-value]

    # ---------- Registre appareils ----------
    def _ensure_device_registry(self, car_id: str, profile: dict[str, Any]) -> str:
        """Crée / met à jour le Device dans le Device Registry et renvoie le nom retenu.

        - Si le profil envoie un "mauvais" nom (vide, 'Vehicle', même que l'ID/hash),
          on conserve le nom existant s'il est meilleur ; sinon on fabrique 'Vehicle xxxxxx'.
        """
        dev_reg = dr.async_get(self.hass)
        raw_name = (profile or {}).get("Name") or ""
        sw_ver = (profile or {}).get("version")

        existing = dev_reg.async_get_device(identifiers={(DOMAIN, car_id)})

        def _is_poor(n: str) -> bool:
            if not n:
                return True
            s = n.strip()
            if not s:
                return True
            if s == car_id:
                return True
            if s.lower() in {"vehicle", "véhicule"}:
                return True
            return False

        if _is_poor(raw_name):
            if existing and existing.name:
                effective_name = existing.name
            else:
                effective_name = f"Vehicle {car_id[:6]}"
        else:
            effective_name = raw_name

        # Création si absent
        device = dev_reg.async_get_or_create(
            config_entry_id=self.entry.entry_id,
            identifiers={(DOMAIN, car_id)},
            manufacturer="Torque Pro",
            model=effective_name,
            name=effective_name,
            sw_version=sw_ver,
        )

        # Mise à jour si nécessaire (sans dégrader un bon nom)
        updates: dict[str, Any] = {}
        if device.name != effective_name:
            updates["name"] = effective_name
        if device.model != effective_name:
            updates["model"] = effective_name
        if sw_ver and getattr(device, "sw_version", None) != sw_ver:
            updates["sw_version"] = sw_ver

        if updates:
            dev_reg.async_update_device(device.id, **updates)
            _LOGGER.debug("Device %s updated with %s", car_id, updates)

        return effective_name

    # ---------- Flux de données (appelé par l'API) ----------
    async def update_from_session(self, session_data: dict[str, Any]) -> None:
        """Reçoit une session depuis la vue HTTP et notifie les entités (async)."""
        try:
            profile = session_data.get("profile") or {}
            car_name = profile.get("Name") or "Vehicle"

            # ID technique STABLE : profile.Id si présent, sinon slugify(Name)
            car_id = profile.get("Id") or slugify(car_name)

            # Filtrer TOUTES les valeurs non finies (inf/nan/Infinity)
            vals = session_data.get("values") or {}
            for k, v in list(vals.items()):
                if _is_non_finite(v):
                    vals[k] = None

            # Mémorise la session (exposée aux entités)
            self.cars[car_id] = session_data
            self.data[car_id] = session_data

            # Assure la présence + cohérence du Device Registry et récupère le nom retenu
            effective_name = self._ensure_device_registry(car_id, profile)

            # Création du device_tracker si GPS dispo et pas déjà restauré
            values = session_data.get("values") or {}
            if (
                TORQUE_GPS_LAT in values
                and TORQUE_GPS_LON in values
                and f"{car_id}:{ENTITY_GPS}" not in self.tracked
                and callable(self.async_add_device_tracker)
            ):
                device = DeviceInfo(
                    identifiers={(DOMAIN, car_id)},
                    manufacturer="Torque Pro",
                    model=effective_name,
                    name=effective_name,  # affichage = nom du profil retenu
                    sw_version=profile.get("version"),
                )
                self.tracked.add(f"{car_id}:{ENTITY_GPS}")
                self.async_add_device_tracker([TorqueDeviceTracker(self, self.entry, device)])

            # Détecte les nouveaux capteurs "créables" et appelle l'adder du sensor.py
            meta_map = session_data.get("meta") or {}
            if self._sensor_adder:
                for short, meta in meta_map.items():
                    if not self._is_creatable_sensor(short, meta):
                        continue
                    tracked_key = f"{car_id}:{short}"
                    if tracked_key in self.tracked:
                        continue
                    try:
                        self._sensor_adder(car_id, short, meta)
                        self.tracked.add(tracked_key)
                    except Exception:  # noqa: BLE001
                        _LOGGER.exception("sensor adder callback failed for %s/%s", car_id, short)

            # Notifie les entités (expose tout le dict {car_id: session})
            self.async_set_updated_data(self.data)

        except Exception:  # noqa: BLE001
            _LOGGER.exception("update_from_session failed")

    # ---------- Maintenance ----------
    def forget_vehicle(self, vehicle_key: str) -> None:
        """Oublie un véhicule (car_id)."""
        self.cars.pop(vehicle_key, None)
        self.data.pop(vehicle_key, None)
        to_remove = {k for k in self.tracked if k.startswith(f"{vehicle_key}:")}
        if to_remove:
            self.tracked.difference_update(to_remove)
        _LOGGER.debug("Forgot vehicle %s; removed %d tracked keys", vehicle_key, len(to_remove))
