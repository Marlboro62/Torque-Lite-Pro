# -*- coding: utf-8 -*-
"""Public HTTP endpoint for Torque Pro (receives Torque uploads).

- Expose /api/torque_pro (auth required by default)
- Parses Torque Pro GET/POST uploads
- Maintains an in-memory LRU of recent sessions (TTL + size cap)
- Keeps native metric units at ingestion; only annotates user unit preference
- Forwards normalized sessions to the proper Coordinator based on email (multi-entry routing)
"""
from __future__ import annotations

from typing import Any, Dict, Tuple, Callable
from collections import OrderedDict
from numbers import Number
from datetime import datetime, timedelta, timezone
import logging
import inspect
import math
import re

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.util import slugify

# labels_fr is optional at runtime; fall back gracefully if missing
try:  # pragma: no cover
    from .labels_fr import FR_BY_KEY
except Exception:  # noqa: BLE001
    FR_BY_KEY = {}

from .const import (
    DOMAIN,
    DEFAULT_LANGUAGE,
    RUNTIME_LANG_MAP,
    SESSION_TTL_SECONDS,
    MAX_SESSIONS,
    TORQUE_CODES,
    TORQUE_GPS_LAT,
    TORQUE_GPS_LON,
    TORQUE_GPS_ALTITUDE,
    TORQUE_GPS_ACCURACY,
)

_LOGGER = logging.getLogger(__name__)

# -----------------------------
# Libellés FR (lazy init)
# -----------------------------
_LABELS_FR: dict[str, str] | None = None


def _ensure_labels_fr() -> dict[str, str]:
    """Build once: map english fullName -> french label from metas."""
    global _LABELS_FR
    if _LABELS_FR is not None:
        return _LABELS_FR

    labels: dict[str, str] = {}
    for meta in TORQUE_CODES.values():
        full_en = (meta.get("fullName") or "").strip().lower()
        short = meta.get("shortName") or ""
        fr = FR_BY_KEY.get(short)
        if full_en and fr:
            labels[full_en] = fr

    _LABELS_FR = labels
    return _LABELS_FR


def get_label(lang: str, full_en: str) -> str:
    """Return localized label if known; else english fallback."""
    if (lang or DEFAULT_LANGUAGE).lower() == "fr":
        labels = _ensure_labels_fr()
        key = (full_en or "").strip().lower()
        return labels.get(key, full_en)
    return full_en


# -----------------------------
# Helpers
# -----------------------------
_POOR_NAME_RE = re.compile(r"^\s*vehicle\s*\d+\s*$", re.IGNORECASE)


def _is_poor_name(name: str | None) -> bool:
    """True for empty names, 'vehicle', 'véhicule', or 'Vehicle 123456' fallback."""
    if not name:
        return True
    s = name.strip()
    if not s:
        return True
    low = s.lower()
    if low in {"vehicle", "véhicule"}:
        return True
    return bool(_POOR_NAME_RE.match(low))


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_number(raw: Any) -> float | None:
    """Parse float (comma decimals ok) and drop non-finite."""
    if raw is None:
        return None
    try:
        s = str(raw).strip()
        if s == "":
            return None
        s = s.replace(",", ".")
        sl = s.lower()
        if sl in ("inf", "+inf", "-inf", "infinity", "nan"):
            return None
        v = float(s)
        return v if math.isfinite(v) else None
    except Exception:  # noqa: BLE001
        return None


def _pick_lang(query_lang: str | None) -> str:
    lang = (query_lang or DEFAULT_LANGUAGE).strip().lower()
    return RUNTIME_LANG_MAP.get(lang, DEFAULT_LANGUAGE)


def _valid_lat_lon(lat: float | None, lon: float | None) -> tuple[float | None, float | None]:
    """Validate coordinate bounds; return None for invalid parts."""
    if lat is not None and not (-90.0 <= lat <= 90.0):
        lat = None
    if lon is not None and not (-180.0 <= lon <= 180.0):
        lon = None
    return lat, lon


def _norm_key(k: str) -> str:
    """Normalize a key for tolerant comparison (case/dots/dashes/underscores)."""
    return k.lower().replace(".", "").replace("-", "").replace("_", "").strip()


def _extract_profile_name(q: Dict[str, str]) -> str:
    """Try several possible keys used by Torque variants for the profile name."""
    candidates = (
        "profileName", "profile_name", "profile",
        "vehicleName", "vehicle", "carName", "car",
        "name", "profilename", "profile.name"
    )
    wanted = {_norm_key(c) for c in candidates}
    for k, v in q.items():
        if _norm_key(k) in wanted:
            s = str(v).strip()
            if s:
                return s
    return ""


# -----------------------------
# Unit conversion helpers (kept for future use, not applied at ingestion)
# -----------------------------
try:  # pragma: no cover
    import pint  # type: ignore

    _UREG = pint.UnitRegistry(autoconvert_offset_to_baseunit=True)

    def _conv_with_pint(v: float, src: str, dst: str) -> float:
        return _UREG.Quantity(v, src).to(dst).magnitude

except Exception:  # noqa: BLE001
    _UREG = None

    def _conv_with_pint(v: float, src: str, dst: str) -> float:  # type: ignore
        raise RuntimeError("pint not available")


# Table compact (not used during ingestion anymore)
_CONV: dict[str, Tuple[str, Callable[[float], float]]] = {
    "km/h": ("mph", (lambda v: _conv_with_pint(v, "kilometer/hour", "mile/hour")) if _UREG else (lambda v: v * 0.621371)),
    "km": ("mi", (lambda v: _conv_with_pint(v, "kilometer", "mile")) if _UREG else (lambda v: v * 0.621371)),
    "m": ("ft", (lambda v: _conv_with_pint(v, "meter", "foot")) if _UREG else (lambda v: v * 3.280839895)),
    "kPa": ("psi", (lambda v: _conv_with_pint(v, "kilopascal", "psi")) if _UREG else (lambda v: v * 0.145037738)),
    "bar": ("psi", (lambda v: _conv_with_pint(v, "bar", "psi")) if _UREG else (lambda v: v * 14.5037738)),
    "mb": ("inHg", (lambda v: _conv_with_pint(v, "millibar", "inch_Hg")) if _UREG else (lambda v: v * 0.02953)),
    "°C": ("°F", (lambda v: _conv_with_pint(v, "degC", "degF")) if _UREG else (lambda v: v * 9.0 / 5.0 + 32.0)),
    "L": ("gal", (lambda v: _conv_with_pint(v, "liter", "gallon")) if _UREG else (lambda v: v * 0.264172052)),
    "L/hr": ("gal/hr", (lambda v: _conv_with_pint(v, "liter/hour", "gallon/hour")) if _UREG else (lambda v: v * 0.264172052)),
    "cc/min": ("gal/min", (lambda v: _conv_with_pint(v, "milliliter/minute", "gallon/minute")) if _UREG else (lambda v: v * 0.000264172052)),
    "g/s": ("lb/min", (lambda v: _conv_with_pint(v, "gram/second", "pound/minute")) if _UREG else (lambda v: v * 0.1322773573)),
    "Nm": ("ft-lb", (lambda v: _conv_with_pint(v, "newton*meter", "foot*pound")) if _UREG else (lambda v: v * 0.737562149)),
    "kW": ("hp", (lambda v: _conv_with_pint(v, "kilowatt", "horsepower")) if _UREG else (lambda v: v * 1.34102209)),
}

# NOTE: we intentionally DO NOT apply conversions at ingestion anymore.


# ---- s -> min pour les temps de trajet ----
_SECONDS_TO_MIN = {
    "trip_time_since_start",   # ff1266
    "trip_time_stationary",    # ff1267
    "trip_time_moving",        # ff1268
}


def _normalize_runtime_units(values: Dict[str, Any], meta: Dict[str, Dict[str, Any]]) -> None:
    """Convertit certains temps de secondes en minutes (plus lisibles)."""
    for short in list(meta.keys()):
        m = meta.get(short) or {}
        unit = (m.get("unit") or "").strip()
        if short in _SECONDS_TO_MIN and unit == "s":
            v = values.get(short)
            if isinstance(v, Number) and math.isfinite(float(v)):
                values[short] = float(v) / 60.0
                m["unit"] = "min"
                meta[short] = m


# ---- Synthèse économie carburant : kpl/mpg <-> L/100km ----
def _is_num(x: Any) -> bool:
    try:
        return isinstance(x, (int, float)) and math.isfinite(float(x))
    except Exception:
        return False


def _synth_economy(values: Dict[str, Any], meta: Dict[str, Dict[str, Any]], lang: str) -> None:
    """Crée L/100km à partir de kpl/mpg (et réciproquement) pour instant/trip/long term."""
    MPG_TO_L_PER_100 = 235.215  # 100 * L_per_gallon / km_per_mile

    def _add(short: str, val: float, unit: str, full_en: str) -> None:
        if short in values and _is_num(values[short]):
            return
        values[short] = float(val)
        meta.setdefault(short, {
            "name": get_label(lang, full_en),
            "unit": unit,
            "full_en": full_en,
            "code": "",
        })

    # Long term
    kpl = values.get("kpl_long_term_avg")
    l100 = values.get("l_per_100_long_term_avg")
    mpg = values.get("mpg_long_term_avg")
    if _is_num(kpl) and not _is_num(l100) and float(kpl) > 0:
        _add("l_per_100_long_term_avg", 100.0 / float(kpl), "L/100km",
             "Litres Per 100 Kilometer(Long Term Average)")
    elif _is_num(l100) and not _is_num(kpl) and float(l100) > 0:
        _add("kpl_long_term_avg", 100.0 / float(l100), "kpl",
             "Kilometers Per Litre(Long Term Average)")
    elif _is_num(mpg) and not _is_num(l100) and float(mpg) > 0:
        _add("l_per_100_long_term_avg", MPG_TO_L_PER_100 / float(mpg), "L/100km",
             "Litres Per 100 Kilometer(Long Term Average)")

    # Trip avg
    kpl = values.get("kpl_trip_avg")
    l100 = values.get("l_per_100_trip_avg")
    mpg = values.get("mpg_trip_avg")
    if _is_num(kpl) and not _is_num(l100) and float(kpl) > 0:
        _add("l_per_100_trip_avg", 100.0 / float(kpl), "L/100km", "Trip average Litres/100 KM")
    elif _is_num(l100) and not _is_num(kpl) and float(l100) > 0:
        _add("kpl_trip_avg", 100.0 / float(l100), "kpl", "Trip average KPL")
    elif _is_num(mpg) and not _is_num(l100) and float(mpg) > 0:
        _add("l_per_100_trip_avg", MPG_TO_L_PER_100 / float(mpg), "L/100km", "Trip average Litres/100 KM")

    # Instant
    kpl = values.get("kpl_instant")
    l100 = values.get("l_per_100_instant")
    mpg = values.get("mpg_instant")
    if _is_num(kpl) and not _is_num(l100) and float(kpl) > 0:
        _add("l_per_100_instant", 100.0 / float(kpl), "L/100km", "Litres Per 100 Kilometer(Instant)")
    elif _is_num(l100) and not _is_num(kpl) and float(l100) > 0:
        _add("kpl_instant", 100.0 / float(l100), "kpl", "Kilometers Per Litre(Instant)")
    elif _is_num(mpg) and not _is_num(l100) and float(mpg) > 0:
        _add("l_per_100_instant", MPG_TO_L_PER_100 / float(mpg), "L/100km", "Litres Per 100 Kilometer(Instant)")


# -----------------------------
# HTTP View
# -----------------------------
class TorqueReceiveDataView(HomeAssistantView):
    """Receive Torque Pro payloads (GET/POST)."""

    url = "/api/torque_pro"
    name = "api:torque_pro"
    requires_auth = True  # set to False only if your app cannot send token

    # NOTE: old single-coordinator attachment kept for backward compat, not used in routing
    coordinator: Any | None = None

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        email_filter: str | None = None,  # kept for backward compat; ignored in multi-entry mode
        default_language: str = DEFAULT_LANGUAGE,
        imperial_units: bool = False,
        # runtime memory-scaling (from options)
        session_ttl_seconds: int | None = None,
        max_sessions: int | None = None,
    ) -> None:
        self.hass = hass
        # legacy per-view fields (used only as fallback if no route exists)
        self.email = (email_filter or "").strip()
        self.lang = _pick_lang(default_language)
        self.imperial = bool(imperial_units)

        # In-memory sessions LRU: {session_id: {...}}, oldest on the left
        self._sessions: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
        self._ttl_seconds = int(session_ttl_seconds or SESSION_TTL_SECONDS)
        self._max_sessions = int(max_sessions or MAX_SESSIONS)

        # Mémoire des derniers bons noms
        self._last_name_by_email: Dict[str, str] = {}
        self._last_name_by_id: Dict[str, str] = {}

        # -------- Multi-entry routing --------
        # entry_id -> {"coordinator": ..., "email": str, "imperial": bool, "lang": str}
        self._entry_routes: dict[str, dict[str, Any]] = {}
        # email_lower -> entry_id
        self._email_to_entry: dict[str, str] = {}

        # Vue HTTP persistante : active tant qu'au moins une route existe
        self._active: bool = True

    # -------- Routing helpers (multi-entry) --------
    def upsert_route(
        self,
        entry_id: str,
        *,
        email: str | None,
        coordinator: Any,
        imperial: bool,
        lang: str,
    ) -> None:
        """Register/refresh a route for a config entry."""
        email_norm = (email or "").strip().lower()
        prev = self._entry_routes.get(entry_id)
        if prev and prev.get("email"):
            self._email_to_entry.pop(prev["email"], None)

        self._entry_routes[entry_id] = {
            "coordinator": coordinator,
            "email": email_norm,
            "imperial": bool(imperial),
            "lang": _pick_lang(lang),
        }
        if email_norm:
            self._email_to_entry[email_norm] = entry_id

        # Activer la vue dès qu'au moins une route est présente
        self._active = True

    def remove_route(self, entry_id: str) -> None:
        """Unregister a route when a config entry is unloaded."""
        prev = self._entry_routes.pop(entry_id, None)
        if prev and prev.get("email"):
            self._email_to_entry.pop(prev["email"], None)
        # Désactiver la vue si plus aucune entrée n'est configurée
        if not self._entry_routes:
            self._active = False

    def set_active(self, active: bool) -> None:
        """Activer/désactiver explicitement la vue (optionnel)."""
        self._active = bool(active)

    def is_active(self) -> bool:
        return self._active

    def _pick_route(self, email: str | None) -> dict[str, Any] | None:
        """Choose a route based on email; if only one route exists, allow missing email."""
        key = (email or "").strip().lower()
        if key and key in self._email_to_entry:
            return self._entry_routes.get(self._email_to_entry[key])
        if not key and len(self._entry_routes) == 1:
            return next(iter(self._entry_routes.values()))
        # As a final legacy fallback, if no routes exist but a legacy coordinator/email is set
        if not self._entry_routes and (self.coordinator or self.email):
            return {
                "coordinator": self.coordinator,
                "email": (self.email or "").strip().lower(),
                "imperial": self.imperial,
                "lang": self.lang,
            }
        return None

    # -------------------------
    # Housekeeping
    # -------------------------
    def _cleanup_sessions(self) -> None:
        """TTL + LRU cap; robust even if order was altered elsewhere."""
        cutoff = _now_utc() - timedelta(seconds=self._ttl_seconds)

        # 1) TTL strict
        while self._sessions:
            sid, sess = next(iter(self._sessions.items()))
            last = sess.get("last_seen")
            if last is None or last <= cutoff:
                self._sessions.popitem(last=False)
            else:
                break

        # 2) LRU size cap
        while len(self._sessions) > self._max_sessions:
            self._sessions.popitem(last=False)

    def _upsert_and_touch(self, session: Dict[str, Any]) -> None:
        """Insert or replace session and mark it as most recently used."""
        self._sessions[session["id"]] = session
        self._sessions.move_to_end(session["id"], last=True)

    # -------------------------
    # Core parsing
    # -------------------------
    @staticmethod
    def _extract_app_version(q: Dict[str, str]) -> str:
        """Prefer explicit app version keys; ignore protocol 'v'/'ver' unless semver-like."""
        for k in ("appVersion", "app_version", "apkVersion", "versionName", "version"):
            v = str(q.get(k, "")).strip()
            if v:
                return v
        for k in ("ver", "v"):
            v = str(q.get(k, "")).strip()
            if v and any(ch in v for ch in ".-"):
                return v
        return ""

    def _parse_fields(self, q: Dict[str, str], lang: str, *, imperial_override: bool | None = None) -> Dict[str, Any] | None:
        """Parse Torque query-string/form-data into a normalized session dict."""
        eml = (q.get("eml") or q.get("email") or "").strip()

        session_id = (q.get("session") or "").strip()
        if not session_id:
            _LOGGER.debug("Missing 'session' in payload")
            return None

        vehicle_id = (q.get("id") or "").strip()

        # Extraction robuste du nom de profil
        profile_name = _extract_profile_name(q)

        # App version (prefer explicit keys; don't treat bare 'v=9' as app version)
        app_version = self._extract_app_version(q)
        if (q.get("v") or q.get("ver")) and not app_version:
            _LOGGER.debug(
                "Ignoring protocol version v=%s/ver=%s (no app version provided)",
                q.get("v"), q.get("ver")
            )

        # Optional direct GPS fields alongside FF10xx PIDs
        lat_direct = _parse_number(q.get("lat"))
        lon_direct = _parse_number(q.get("lon"))
        lat_direct, lon_direct = _valid_lat_lon(lat_direct, lon_direct)

        values: Dict[str, Any] = {}
        meta: Dict[str, Dict[str, Any]] = {}
        unknown: Dict[str, Any] = {}
        _UNKNOWN_CAP = 80  # defensive

        for key, raw in q.items():
            if not key or key[0].lower() != "k":
                continue
            code = key[1:].lower()
            meta_code = TORQUE_CODES.get(code)
            if not meta_code:
                if len(unknown) < _UNKNOWN_CAP:
                    unknown[code] = raw
                continue

            short = meta_code["shortName"]
            unit = meta_code.get("unit") or ""
            full_en = meta_code.get("fullName") or short
            name_fr = get_label(lang, full_en)

            val = _parse_number(raw)
            values[short] = val if val is not None else raw
            meta[short] = {
                "name": name_fr,
                "unit": unit,
                "full_en": full_en,
                "code": code,
            }

        if lat_direct is not None:
            values[TORQUE_GPS_LAT] = lat_direct
            meta.setdefault(
                TORQUE_GPS_LAT,
                {"name": get_label(lang, "GPS Latitude"), "unit": "°", "full_en": "GPS Latitude", "code": "ff1006"},
            )
        if lon_direct is not None:
            values[TORQUE_GPS_LON] = lon_direct
            meta.setdefault(
                TORQUE_GPS_LON,
                {"name": get_label(lang, "GPS Longitude"), "unit": "°", "full_en": "GPS Longitude", "code": "ff1005"},
            )

        alt_direct = _parse_number(q.get("alt") or q.get("altitude"))
        if alt_direct is not None:
            values[TORQUE_GPS_ALTITUDE] = alt_direct
            meta.setdefault(
                TORQUE_GPS_ALTITUDE,
                {"name": get_label(lang, "GPS Altitude"), "unit": "m", "full_en": "GPS Altitude", "code": "ff1010"},
            )
        acc_direct = _parse_number(q.get("acc") or q.get("accuracy"))
        if acc_direct is not None:
            values[TORQUE_GPS_ACCURACY] = acc_direct
            meta.setdefault(
                TORQUE_GPS_ACCURACY,
                {"name": get_label(lang, "GPS Accuracy"), "unit": "m", "full_en": "GPS Accuracy", "code": "ff1239"},
            )

        # Si aucun nom n'est fourni OU s'il ressemble à un fallback, réutiliser le dernier bon nom
        if not profile_name or _is_poor_name(profile_name):
            remembered = (vehicle_id and self._last_name_by_id.get(vehicle_id)) or (eml and self._last_name_by_email.get(eml)) or ""
            if remembered and not _is_poor_name(remembered):
                profile_name = remembered

        # Fallback neutre si toujours rien
        if not profile_name:
            profile_name = f"Vehicle {session_id[:6]}"

        # Preference d'unité (annotation seulement)
        imperial_flag = self.imperial if imperial_override is None else bool(imperial_override)
        unit_preference = "imperial" if imperial_flag else "metric"

        profile = {
            "Name": profile_name,
            "Id": vehicle_id or slugify(profile_name),
            "Email": eml,
        }
        if app_version:
            profile["version"] = app_version

        # IMPORTANT: Pas de conversion impériale à l’ingestion.
        # Les unités de 'meta' restent telles que déclarées dans TORQUE_CODES (métriques).
        # Les entités HA feront la conversion d'affichage selon la préférence globale HA
        # (ou en utilisant 'unit_preference' ci-dessous si tu veux une logique avancée ailleurs).

        # s -> min pour les temps de trajet
        _normalize_runtime_units(values, meta)

        # kpl/mpg <-> L/100km (synthèse utile, ne casse pas le natif)
        _synth_economy(values, meta, lang)

        # Drop any remaining non-finite numerics
        for k, v in list(values.items()):
            try:
                if isinstance(v, (int, float)) and not math.isfinite(float(v)):
                    values[k] = None
            except Exception:
                values[k] = None

        session = {
            "id": session_id,
            "last_seen": _now_utc(),
            "profile": profile,
            "values": values,
            "meta": meta,
            "unknown": unknown,
            "lang": lang,
            "unit_preference": unit_preference,  # <-- annotation (no conversion done)
        }

        # Mémoriser le bon nom pour les futures trames sans nom
        if not _is_poor_name(profile_name):
            vid = profile.get("Id") or vehicle_id
            if eml:
                self._last_name_by_email[eml] = profile_name
            if vid:
                self._last_name_by_id[vid] = profile_name

        return session

    async def _async_publish_data(self, session: Dict[str, Any], coordinator: Any | None) -> None:
        """Publish the session to the given coordinator if present (handles sync/async)."""
        if coordinator:
            upd = getattr(coordinator, "update_from_session", None)
            if callable(upd):
                try:
                    if inspect.iscoroutinefunction(upd):
                        await upd(session)  # type: ignore[misc]
                    else:
                        await self.hass.async_add_executor_job(upd, session)  # type: ignore[misc]
                except Exception:  # noqa: BLE001
                    _LOGGER.exception("Coordinator.update_from_session failed")
            else:
                _LOGGER.debug("Coordinator has no 'update_from_session' method")
        else:
            _LOGGER.debug("No coordinator resolved for session; not forwarded")

        self.hass.data.setdefault(DOMAIN, {})["last_session"] = session

    # -------------------------
    # HTTP handlers
    # -------------------------
    async def get(self, request: web.Request) -> web.Response:
        """Handle GET /api/torque_pro."""
        try:
            # Vue persistante mais inactive : pas d'entrée configurée → 404
            if not self._active:
                _LOGGER.debug("Torque Pro view inactive (no config entries); returning 404.")
                return web.Response(status=404, text="Not Found")

            self._cleanup_sessions()
            q = dict(request.query)

            # route selection based on email
            eml = (q.get("eml") or q.get("email") or "").strip()
            route = self._pick_route(eml)
            if route is None:
                _LOGGER.debug("No matching route for email=%s; IGNORE", eml or "<none>")
                return web.Response(text="IGNORED")

            lang = _pick_lang(q.get("lang") or q.get("language") or route["lang"])
            session = self._parse_fields(q, lang, imperial_override=route["imperial"])
            if session is None:
                return web.Response(text="IGNORED")
            self._upsert_and_touch(session)
            await self._async_publish_data(session, route.get("coordinator"))
            return web.Response(text="OK!")
        except Exception as err:  # noqa: BLE001
            _LOGGER.exception("Error handling Torque Pro GET: %s", err)
            return web.Response(status=500, text="Error")

    async def post(self, request: web.Request) -> web.Response:
        """Some Torque Pro variants upload via POST (x-www-form-urlencoded)."""
        try:
            # Vue persistante mais inactive : pas d'entrée configurée → 404
            if not self._active:
                _LOGGER.debug("Torque Pro view inactive (no config entries); returning 404.")
                return web.Response(status=404, text="Not Found")

            self._cleanup_sessions()
            data: Dict[str, str] = {}
            if request.can_read_body:
                form = await request.post()
                data = {k: str(v) for k, v in form.items()}

            eml = (data.get("eml") or data.get("email") or "").strip()
            route = self._pick_route(eml)
            if route is None:
                _LOGGER.debug("No matching route for email=%s; IGNORE", eml or "<none>")
                return web.Response(text="IGNORED")

            lang = _pick_lang(data.get("lang") or data.get("language") or route["lang"])
            session = self._parse_fields(data, lang, imperial_override=route["imperial"])
            if session is None:
                return web.Response(text="IGNORED")
            self._upsert_and_touch(session)
            await self._async_publish_data(session, route.get("coordinator"))
            return web.Response(text="OK!")
        except Exception as err:  # noqa: BLE001
            _LOGGER.exception("Error handling Torque Pro POST: %s", err)
            return web.Response(status=500, text="Error")

    async def head(self, request: web.Request) -> web.Response:
        """Torque Pro may probe the URL via HEAD; reply 200 to avoid app alert."""
        return web.Response(status=200)
