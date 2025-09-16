# -*- coding: utf-8 -*-
"""Sensor platform for Torque Pro (compatible unique_id + FR fallback).

- Restauration compatible avec l'ancien schéma d'UID ("{entry}-{veh}-{short}")
- Utilise la base TorqueEntity pour un device propre (attribution, device_info)
- Conserve *exactement* l'UID historique pour éviter toute migration
- Fallback si labels_fr n'est pas présent (labels EN)
- Améliore la déduction du nom d’appareil : si le profil n’a pas (encore) de nom,
  on relit le Device Registry (si existant) ; sinon on évite le hash brut.
"""
from __future__ import annotations

from typing import Any
import logging
import math  # filtre inf/nan

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant  # noqa: E402
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity

from .entity import TorqueEntity
from .const import DOMAIN

# labels_fr est facultatif à l'exécution
try:  # pragma: no cover - import-time branch
    from .labels_fr import FR_BY_KEY
except Exception:  # noqa: BLE001
    FR_BY_KEY = {}

_LOGGER = logging.getLogger(__name__)

# --------------------------------------------------------------------
# Helpers internes
# --------------------------------------------------------------------


def _infer_device_class(short: str, unit: str | None) -> SensorDeviceClass | None:
    """Assigne un device_class prudent en fonction de l’unité et du nom court."""
    u = (unit or "").strip()
    s = (short or "").lower()

    if u in ("°C", "°F"):
        return SensorDeviceClass.TEMPERATURE
    if u in ("kPa", "bar", "psi", "inHg", "mb", "mbar", "hPa"):
        return SensorDeviceClass.PRESSURE
    if u in ("V", "mV"):
        return SensorDeviceClass.VOLTAGE
    if u in ("km/h", "mph", "m/s"):
        return SensorDeviceClass.SPEED
    if u in ("A", "mA"):
        return SensorDeviceClass.CURRENT
    if u in ("km", "mi", "m"):
        return SensorDeviceClass.DISTANCE
    if "battery" in s or "batt" in s:
        return SensorDeviceClass.BATTERY
    return None


_NONFINITE_STR = {"inf", "+inf", "-inf", "infinity", "nan"}


def _is_non_finite(v: Any) -> bool:
    """True si v est inf/-inf/nan (numérique) ou chaîne équivalente."""
    try:
        if isinstance(v, (int, float)):
            return not math.isfinite(float(v))
        if isinstance(v, str):
            return v.strip().lower() in _NONFINITE_STR
    except Exception:
        return True
    return False


def _suggest_precision(short: str, unit: str | None) -> int | None:
    """Précision d'affichage conseillée selon l’unité / le type."""
    u = (unit or "").strip()
    s = (short or "").lower()

    # Vitesses
    if u in ("km/h", "mph", "m/s"):
        return 1
    # Pressions
    if u in ("kPa", "bar", "psi", "inHg", "mb", "mbar", "hPa"):
        return 1
    # Température / tension / intensité
    if u in ("°C", "°F"):
        return 1
    if u in ("V", "mV", "A", "mA"):
        return 2
    # Distances
    if u in ("km", "mi"):
        return 1
    if u in ("m",):
        return 0

    # Débits / consommations / économie de carburant
    if u in ("L/hr", "L/h", "L/m"):
        return 2
    if u in ("cc/min",):
        return 1
    if u in ("g/s", "lb/min"):
        return 2
    if u in ("L/100km", "mpg", "kpl"):
        return 1

    # Puissance
    if u in ("kW", "hp"):
        return 1

    # Angles / pourcentages
    if u in ("°",):
        return 0
    if u in ("%",):
        return 1

    # Quelques clés spécifiques sans unité
    if "rpm" in s:
        return 0
    return None


# -------- Valeurs qui doivent retomber à 0 si absentes --------
_ZERO_DEFAULT_SHORTS = {
    "trip_distance",            # ff1204
    "trip_distance_stored",     # ff120c
    "dist_mil_on",              # 0x21
    "dist_since_codes_cleared", # 0x31
    "trip_time_since_start",    # ff1266
    "trip_time_stationary",     # ff1267
    "trip_time_moving",         # ff1268
    "engine_kw_wheels",         # ff1273 → Puiss. kW (roues)
    "horsepower_wheels",        # ff1226 → Puiss. roues hp
}


def _should_zero(short: str, unit: str | None) -> bool:
    """Détermine si le capteur doit afficher 0 en l'absence de valeur."""
    s = (short or "").lower()
    u = (unit or "").strip()
    if s in _ZERO_DEFAULT_SHORTS:
        return True
    # Règle générique : compteurs de trajet/distance/temps
    if any(tok in s for tok in ("trip", "dist", "distance", "time")) and u in ("km", "mi", "m", "s", "min"):
        return True
    return False


# --------------------------------------------------------------------
# Plateforme sensor (s'appuie sur le coordinateur)
# --------------------------------------------------------------------
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Configure les capteurs Torque Pro à partir du coordinator."""
    try:
        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    except Exception:  # noqa: BLE001
        _LOGGER.debug("Coordinator non disponible pour %s", DOMAIN)
        return

    entities: list[TorqueSensor] = []
    seen: set[str] = set()  # pour dédupliquer par unique_id

    def _push(e: "TorqueSensor") -> None:
        if e.unique_id in seen:
            return
        seen.add(e.unique_id)  # type: ignore[arg-type]
        entities.append(e)

    # 0) Restauration depuis le registre d'entités (entités connues)
    try:
        ent_reg = er.async_get(hass)
        for ent in ent_reg.entities.values():
            if ent.config_entry_id != entry.entry_id:
                continue
            if ent.domain != "sensor":
                continue
            if ent.platform != DOMAIN:
                continue  # nécessite DOMAIN == "torque_pro" dans const.py

            uid = ent.unique_id or ""

            # Cas 1: ancien schéma (hérité) => "{entry}-{veh}-{short}"
            legacy_prefix = f"{entry.entry_id}-"
            if uid.startswith(legacy_prefix) and "-" in uid[len(legacy_prefix):]:
                suffix = uid[len(legacy_prefix):]
                vehicle_id, short = suffix.rsplit("-", 1)
            # Cas 2: éventuel nouveau schéma => f"{DOMAIN}_{entry}_{veh}_{short}"
            elif uid.startswith(f"{DOMAIN}_{entry.entry_id}_"):
                suffix = uid[len(f"{DOMAIN}_{entry.entry_id}_"):]
                try:
                    vehicle_id, short = suffix.rsplit("_", 1)
                except ValueError:
                    continue
            else:
                continue

            name = ent.original_name or ent.name or FR_BY_KEY.get(short) or short
            meta = {"name": name, "unit": None}

            sensor = _make_sensor(coordinator, entry, vehicle_id, short, meta)
            _push(sensor)

            # Marquer comme déjà tracké pour empêcher un doublon à la 1ʳᵉ trame
            try:
                if not hasattr(coordinator, "tracked") or coordinator.tracked is None:
                    coordinator.tracked = set()
                coordinator.tracked.add(f"{vehicle_id}:{short}")
            except Exception:  # noqa: BLE001
                _LOGGER.debug("Impossible de marquer %s:%s comme tracké", vehicle_id, short)
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Restauration des sensors depuis le registre a échoué")

    # 1) Snapshot initial des capteurs "créables" connus du coordinator
    if hasattr(coordinator, "iter_current_sensors"):
        try:
            for veh_id, short, meta in coordinator.iter_current_sensors():  # type: ignore[attr-defined]
                _push(_make_sensor(coordinator, entry, veh_id, short, meta))
        except Exception:  # noqa: BLE001
            _LOGGER.exception("iter_current_sensors a échoué")

    if entities:
        async_add_entities(entities)

    # 2) Ajout dynamique des futurs capteurs
    if hasattr(coordinator, "set_sensor_adder"):
        def _adder(veh_id: str, short: str, meta: dict[str, Any]):
            try:
                async_add_entities([_make_sensor(coordinator, entry, veh_id, short, meta)])
            except Exception:  # noqa: BLE001
                _LOGGER.exception("sensor adder a échoué pour %s/%s", veh_id, short)

        try:
            coordinator.set_sensor_adder(_adder)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            _LOGGER.exception("set_sensor_adder a échoué")


def _make_sensor(coordinator, entry: ConfigEntry, vehicle_id: str, short: str, meta: dict[str, Any]) -> "TorqueSensor":
    name = (meta.get("name") or FR_BY_KEY.get(short) or short).strip()
    unit = (meta.get("unit") or "").strip() or None
    return TorqueSensor(coordinator, entry, vehicle_id, short, name, unit)


# ------ Récupération du nom/firmware profil depuis le coordinator ------
def _profile_name_and_version(coordinator, vehicle_id: str) -> tuple[str, str | None]:
    """Retourne (nom_profil, version_app) connus pour ce véhicule, avec fallback sain.

    Stratégie :
    1) d’abord le nom du profil reçu dans la dernière trame (cars[veh]['profile']['Name'])
    2) sinon, essayer le Device Registry (peut déjà contenir un nom humain si le device a été créé)
    3) sinon, un nom générique « Vehicle ABCDEF » (évite d’utiliser le hash brut)
    """
    try:
        cars = getattr(coordinator, "cars", {}) or {}
        prof = (cars.get(vehicle_id) or {}).get("profile", {}) or {}
        name = (prof.get("Name") or prof.get("name") or "").strip()
        ver = prof.get("version") or None
    except Exception:
        name, ver = "", None

    def _is_poor(n: str) -> bool:
        if not n:
            return True
        s = n.strip()
        return (not s) or (s.lower() in {"vehicle", "véhicule"}) or (s == vehicle_id)

    # 2) Lire le Device Registry si le nom de profil est absent/peu utile
    if _is_poor(name):
        try:
            dev_reg = dr.async_get(coordinator.hass)
            dev = dev_reg.async_get_device(identifiers={(DOMAIN, vehicle_id)})
            if dev and (dev.name or dev.model):
                name = (dev.name or dev.model or "").strip()
        except Exception:  # noqa: BLE001
            pass

    # 3) Dernier filet de sécurité : éviter un nom basé sur le hash complet
    if _is_poor(name):
        short_id = (vehicle_id or "").strip()
        short_id = short_id[:6] if short_id else "unknown"
        name = f"Vehicle {short_id}"

    return name, ver


class TorqueSensor(TorqueEntity, SensorEntity, RestoreEntity):
    """Capteur dynamique alimenté par le coordinator Torque Pro."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        config_entry: ConfigEntry,
        vehicle_id: str,
        short: str,
        name: str,
        unit: str | None,
    ) -> None:
        # DeviceInfo avec le nom du profil pour de bons entity_id
        car_name, car_ver = _profile_name_and_version(coordinator, vehicle_id)
        device = DeviceInfo(
            identifiers={(DOMAIN, vehicle_id)},
            manufacturer="Torque Pro",
            model=car_name,
            name=car_name,        # <<< utilisé par HA pour préfixer les entity_id
            sw_version=car_ver,
        )
        super().__init__(coordinator, config_entry, short, device)

        # IMPORTANT: conserver l'UID historique pour éviter une migration
        self._attr_unique_id = f"{config_entry.entry_id}-{vehicle_id}-{short}"

        # Identifiants locaux
        self._car_id = vehicle_id
        self._vehicle_id = vehicle_id
        self._short = short

        # Présentation
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = self._pick_icon(short, unit)

        # Précision d'affichage conseillée (frontend)
        prec = _suggest_precision(short, unit)
        if prec is not None:
            self._attr_suggested_display_precision = prec

        # Device & state classes (prudent)
        dc = _infer_device_class(short, unit)
        if dc is not None:
            self._attr_device_class = dc
            self._attr_state_class = SensorStateClass.MEASUREMENT

        # Valeur restaurée (fallback tant qu'aucune donnée fraîche)
        self._attr_native_value = None

    @property
    def available(self) -> bool:
        """Rendre l'entité disponible même sans trame récente."""
        try:
            data = getattr(self.coordinator, "data", {}) or {}
            if self._car_id in data:
                return True
            if getattr(self, "_attr_native_value", None) is not None:
                return True
            if _should_zero(self._short, getattr(self, "_attr_native_unit_of_measurement", None)):
                return True
        except Exception:
            pass
        return True

    async def async_added_to_hass(self) -> None:
        """Restaure le dernier état + (re)déduit classes si besoin."""
        await super().async_added_to_hass()
        try:
            last = await self.async_get_last_state()
            if not last:
                return

            # Unité (si absente du méta)
            uom = last.attributes.get("unit_of_measurement") or last.attributes.get(
                "native_unit_of_measurement"
            )
            if uom and not getattr(self, "_attr_native_unit_of_measurement", None):
                self._attr_native_unit_of_measurement = uom

            # Précision suggérée (si pas encore posée)
            if getattr(self, "_attr_suggested_display_precision", None) is None:
                prev_prec = last.attributes.get("suggested_display_precision")
                if isinstance(prev_prec, int):
                    self._attr_suggested_display_precision = prev_prec
                else:
                    p = _suggest_precision(self._short, getattr(self, "_attr_native_unit_of_measurement", None))
                    if p is not None:
                        self._attr_suggested_display_precision = p

            # Valeur de secours (affichée tant qu’aucune donnée récente)
            if last.state not in ("unknown", "unavailable") and not _is_non_finite(last.state):
                self._attr_native_value = last.state
            else:
                self._attr_native_value = None

            # Recalcul device_class si non posé
            if not getattr(self, "_attr_device_class", None):
                dc = _infer_device_class(self._short, getattr(self, "_attr_native_unit_of_measurement", None))
                if dc is not None:
                    self._attr_device_class = dc

            # Reposer une state_class si utile
            if not getattr(self, "_attr_state_class", None):
                prev_sc = (last.attributes.get("state_class") or "").strip().lower()
                mapping = {
                    "measurement": SensorStateClass.MEASUREMENT,
                    "total": SensorStateClass.TOTAL,
                    "total_increasing": SensorStateClass.TOTAL_INCREASING,
                }
                self._attr_state_class = mapping.get(prev_sc)
                if self._attr_state_class is None and (
                    getattr(self, "_attr_device_class", None) is not None
                    or getattr(self, "_attr_native_unit_of_measurement", None)
                ):
                    self._attr_state_class = SensorStateClass.MEASUREMENT
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Restauration d'état a échoué pour %s", self.unique_id)

    @property
    def native_value(self) -> Any:
        """Valeur courante depuis le coordinator, sinon valeur restaurée/0."""
        # Lecture live via le coordonnateur si dispo
        getv = getattr(self.coordinator, "get_value", None)
        if callable(getv):
            val = getv(self._car_id, self._short)
        else:
            data = getattr(self.coordinator, "data", {}) or {}
            vehicle = data.get(self._car_id) or {}
            values = vehicle.get("values") or {}
            val = values.get(self._short)

        # Anti inf/nan
        if _is_non_finite(val):
            val = None

        # Si aucune valeur live, tenter le fallback restauré
        if val is None:
            fallback = getattr(self, "_attr_native_value", None)
            if _is_non_finite(fallback):
                fallback = None
            val = fallback

        # Défaut à 0 pour les compteurs (distance/temps/trajet...)
        unit = getattr(self, "_attr_native_unit_of_measurement", None)
        if val is None and _should_zero(self._short, unit):
            val = 0

        # Arrondi esthétique si numérique
        prec = getattr(self, "_attr_suggested_display_precision", None)
        if isinstance(val, (int, float)) and math.isfinite(float(val)) and prec is not None:
            try:
                return round(float(val), prec)
            except Exception:
                return val

        return val

    # ------------------
    # Icônes utilitaires
    # ------------------
    def _pick_icon(self, short: str, unit: str | None) -> str | None:
        s = (short or "").lower()
        u = (unit or "").strip().lower()

        # --- RÈGLES FORTES PAR NOM (prioritaires) ---
        # Batterie (y compris "android_battery_level")
        if "batt" in s or "battery" in s or s.startswith("android_batt") or s == "android_battery_level":
            return "mdi:battery"

        # Throttle / papillon
        if "throttle" in s or "papillon" in s:
            return "mdi:car-cruise-control"

        # Boost / turbo / MAP
        if "boost" in s or "turbo" in s or "manifold" in s or s.endswith("_map"):
            return "mdi:car-turbocharger"

        # MAF / débit d'air
        if s == "mass_air_flow_rate" or "maf" in s or ("air" in s and ("flow" in s or "debit" in s or "rate" in s)):
            return "mdi:air-filter"

        # Sondes O2 / lambda
        if "o2" in s or "lambda" in s:
            return "mdi:molecule"

        # GPS & positionnement
        if s in ("gpslat", "gpslon", "gps_height", "gps_acc", "gps_sats", "gps_bearing", "gps_spd"):
            return {
                "gpslat": "mdi:crosshairs-gps",
                "gpslon": "mdi:crosshairs-gps",
                "gps_height": "mdi:altimeter",
                "gps_acc": "mdi:crosshairs-gps",
                "gps_sats": "mdi:satellite-variant",
                "gps_bearing": "mdi:compass",
                "gps_spd": "mdi:speedometer",
            }[s]

        # Distances / trajets
        if "dist" in s or "distance" in s or "trip_distance" in s or "trip" in s:
            return "mdi:map-marker-distance"

        # Accélérations / G – icônes spécifiques par axe
        if s == "accel_x":
            return "mdi:axis-x-arrow"
        if s == "accel_y":
            return "mdi:axis-y-arrow"
        if s == "accel_z":
            return "mdi:axis-z-arrow"
        if s == "accel_total" or "accel" in s or "gforce" in s or "g_force" in s:
            return "mdi:axis-arrow"

        # Puissance aux roues
        if "hp" in s or "kw" in s or "engine_kw_wheels" in s or "horsepower_wheels" in s or "puiss" in s:
            return "mdi:engine"

        # Régime / RPM
        if "rpm" in s:
            return "mdi:gauge"

        # Conso / économie de carburant
        if "mpg" in s or "kpl" in s or "km_l" in s or "l_100" in s or "l/100" in s:
            return "mdi:gas-station"

        # Précision / accuracy GPS
        if ("acc" in s and "gps" in s) or "accuracy" in s:
            return "mdi:crosshairs-gps"

        # --- FALLBACKS PAR UNITÉ ---
        if u in ("km/h", "mph", "m/s"):
            return "mdi:speedometer"
        if u in ("kpa", "bar", "psi", "inhg", "mb", "mbar", "hpa"):
            return "mdi:gauge"
        if u in ("v", "mv", "a", "ma"):
            return "mdi:flash"
        if u in ("°c", "°f"):
            return "mdi:thermometer"
        if u in ("km", "mi", "m"):
            return "mdi:map-marker-distance"
        if u in ("min", "s"):
            return "mdi:timer-outline"
        if u in ("l/100km", "mpg", "kpl", "l/hr", "l/h", "l/m", "cc/min", "g/s", "lb/min"):
            return "mdi:gas-station"
        if u in ("°",):
            return "mdi:compass"
        if u in ("%",):
            return "mdi:gauge"

        return None
