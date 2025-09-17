# -*- coding: utf-8 -*-
"""Constants for Torque Pro"""
from __future__ import annotations

from typing import Final
import json
import os

from homeassistant.const import Platform

# Nom & domaine
NAME: Final = "Torque Pro"
DOMAIN: Final = "torque_pro"

# Lecture sécurisée de la version depuis manifest.json
_manifest = os.path.join(os.path.dirname(__file__), "manifest.json")
try:
    with open(_manifest, encoding="utf-8") as file:
        VERSION: Final = json.load(file).get("version", "0.0.0")
except Exception:
    VERSION: Final = "0.0.0"

ATTRIBUTION: Final = "Torque Pro"
ISSUE_URL: Final = "https://github.com/Marlboro62/homeassistant/issues"

# --------- CONF (clés d’options/config) ----------
CONF_EMAIL: Final = "email"
CONF_IMPERIAL: Final = "imperial"
CONF_LANGUAGE: Final = "language"

# Options d’échelle mémoire des sessions
CONF_SESSION_TTL: Final = "session_ttl_seconds"
CONF_MAX_SESSIONS: Final = "max_sessions"

# Langue par défaut & support UI
DEFAULT_LANGUAGE: Final = "fr"
SUPPORTED_LANGS: Final = ("en", "fr")

# Normalisation runtime (API)
RUNTIME_LANG_MAP: Final = {
    "fr": "fr",
    "en": "en",
}

# --------- Préférences d’unités (optionnel) ----------
# Côté métrique
CONF_PRESSURE_METRIC: Final = "pressure_metric"      # kPa or bar
CONF_ECONOMY_METRIC: Final = "economy_metric"        # L/100km or km/L
CONF_TORQUE_METRIC: Final = "torque_metric"          # Nm
CONF_FLOW_METRIC: Final = "flow_metric"              # g/s or kg/h
CONF_POWER_METRIC: Final = "power_metric"            # kW or cv

DEFAULT_PRESSURE_METRIC: Final = "kPa"
DEFAULT_ECONOMY_METRIC: Final = "L/100km"
DEFAULT_TORQUE_METRIC: Final = "Nm"
DEFAULT_FLOW_METRIC: Final = "g/s"
DEFAULT_POWER_METRIC: Final = "kW"

# Côté impérial (affichage)
CONF_PRESSURE_IMPERIAL: Final = "pressure_imperial"   # psi or inHg
CONF_FLOW_IMPERIAL: Final = "flow_imperial"           # gal/min or lb/min
CONF_TORQUE_IMPERIAL: Final = "torque_imperial"       # ft-lb
CONF_POWER_IMPERIAL: Final = "power_imperial"         # hp

DEFAULT_PRESSURE_IMPERIAL: Final = "psi"
DEFAULT_FLOW_IMPERIAL: Final = "lb/min"
DEFAULT_TORQUE_IMPERIAL: Final = "ft-lb"
DEFAULT_POWER_IMPERIAL: Final = "hp"

# --------- Sessions mémoire (défauts) ----------
# Purge des sessions inactives (30 minutes)
SESSION_TTL_SECONDS: Final = 30 * 60
# Taille max du cache de sessions (LRU)
MAX_SESSIONS: Final = 100

# --------- Plateformes HA ----------
DEVICE_TRACKER: Final = "device_tracker"
SENSOR: Final = "sensor"
PLATFORMS: Final = [Platform.SENSOR, Platform.DEVICE_TRACKER]

# --------- Message de démarrage ----------
STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
FR:
{NAME}
Version: {VERSION}
Il s'agit d'une intégration personnalisée !
Si vous rencontrez des problèmes, vous pouvez ouvrir un ticket ici :
{ISSUE_URL}
-------------------------------------------------------------------
EN:
{NAME}
Version: {VERSION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""

# --------- Icônes par défaut ----------
DEFAULT_ICON: Final = "mdi:engine"
GPS_ICON: Final = "mdi:crosshairs-gps"
DISTANCE_ICON: Final = "mdi:map-marker-distance"
HIGHWAY_ICON: Final = "mdi:highway"
FUEL_ICON: Final = "mdi:gas-station"
TIME_ICON: Final = "mdi:clock"
CITY_ICON: Final = "mdi:city"
SPEED_ICON: Final = "mdi:speedometer"

# --------- Attributs partagés ----------
ATTR_ALTITUDE: Final = "altitude"
ATTR_VEHICLE_SPEED: Final = "speed"
ATTR_GPS_TIME: Final = "gps_time"

ENTITY_GPS: Final = "gps"

# --------- Clés normalisées GPS ----------
TORQUE_GPS_LAT: Final = "gpslat"
TORQUE_GPS_LON: Final = "gpslon"
TORQUE_GPS_ALTITUDE: Final = "gps_height"
TORQUE_GPS_ACCURACY: Final = "gps_acc"

# --------- Table des codes Torque ----------
# (garde ta table complète si tu en as une; ce bloc garde les essentiels)
TORQUE_CODES: Final = {
    "04": {"shortName": "engine_load", "fullName": "Engine Load", "unit": "%"},
    "05": {"shortName": "coolant_temp", "fullName": "Engine Coolant Temperature", "unit": "°C"},
    "06": {"shortName": "fuel_trim_b1_short", "fullName": "Fuel Trim Bank 1 Short Term", "unit": "%"},
    "07": {"shortName": "fuel_trim_b1_long", "fullName": "Fuel Trim Bank 1 Long Term", "unit": "%"},
    "08": {"shortName": "fuel_trim_b2_short", "fullName": "Fuel Trim Bank 2 Short Term", "unit": "%"},
    "09": {"shortName": "fuel_trim_b2_long", "fullName": "Fuel Trim Bank 2 Long Term", "unit": "%"},
    "0a": {"shortName": "fuel_pressure", "fullName": "Fuel pressure", "unit": "kPa"},
    "0b": {"shortName": "intake_manifold_pressure", "fullName": "Intake Manifold Pressure", "unit": "kPa"},
    "0c": {"shortName": "engine_rpm", "fullName": "Engine RPM", "unit": "rpm"},
    "0d": {"shortName": "speed_obd", "fullName": "Speed (OBD)", "unit": "km/h"},
    "0e": {"shortName": "timing_advance", "fullName": "Timing Advance", "unit": "°"},
    "0f": {"shortName": "intake_air_temp", "fullName": "Intake Air Temperature", "unit": "°C"},
    "10": {"shortName": "mass_air_flow_rate", "fullName": "Mass Air Flow Rate", "unit": "g/s"},
    "11": {"shortName": "throttle_position_manifold", "fullName": "Throttle Position (Manifold)", "unit": "%"},
    "1f": {"shortName": "run_time_since_start", "fullName": "Run time since engine start", "unit": "s"},
    "21": {"shortName": "dist_mil_on", "fullName": "Distance travelled with MIL/CEL lit", "unit": "km"},

    # --- FF10xx GPS subset ---
    "ff1001": {"shortName": "gps_spd", "fullName": "Vehicle Speed (GPS)", "unit": "km/h"},
    "ff1005": {"shortName": TORQUE_GPS_LON, "fullName": "GPS Longitude", "unit": "°"},
    "ff1006": {"shortName": TORQUE_GPS_LAT, "fullName": "GPS Latitude", "unit": "°"},
    "ff1010": {"shortName": TORQUE_GPS_ALTITUDE, "fullName": "GPS Altitude", "unit": "m"},

    # ---------- FF12xx – Performance, O2, trajets & divers ----------
    "ff1201": {"shortName": "mpg_instant", "fullName": "Miles Per Gallon(Instant)", "unit": "mpg"},
    "ff1202": {"shortName": "turbo_boost_vacuum_gauge", "fullName": "Turbo Boost & Vacuum Gauge", "unit": "psi"},
    "ff1203": {"shortName": "kpl_instant", "fullName": "Kilometers Per Litre(Instant)", "unit": "kpl"},
    "ff1204": {"shortName": "trip_distance", "fullName": "Trip Distance", "unit": "km"},
    "ff1205": {"shortName": "mpg_trip_avg", "fullName": "Trip average MPG", "unit": "mpg"},
    "ff1206": {"shortName": "kpl_trip_avg", "fullName": "Trip average KPL", "unit": "kpl"},
    "ff1207": {"shortName": "l_per_100_instant", "fullName": "Litres Per 100 Kilometer(Instant)", "unit": "L/100km"},
    "ff1208": {"shortName": "l_per_100_trip_avg", "fullName": "Trip average Litres/100 KM", "unit": "L/100km"},
    "ff120c": {"shortName": "trip_distance_stored", "fullName": "Trip distance (stored in vehicle profile)", "unit": "km"},
    "ff1214": {"shortName": "o2_b1s1_voltage", "fullName": "O2 {O2L:1} Voltage", "unit": "V"},
    "ff1215": {"shortName": "o2_b1s2_voltage", "fullName": "O2 {O2L:2} Voltage", "unit": "V"},
    "ff1216": {"shortName": "o2_b1s3_voltage", "fullName": "O2 {O2L:3} Voltage", "unit": "V"},
    "ff1217": {"shortName": "o2_b1s4_voltage", "fullName": "O2 {O2L:4} Voltage", "unit": "V"},
    "ff1218": {"shortName": "o2_b2s1_voltage", "fullName": "O2 {O2L:5} Voltage", "unit": "V"},
    "ff1219": {"shortName": "o2_b2s2_voltage", "fullName": "O2 {O2L:6} Voltage", "unit": "V"},
    "ff121a": {"shortName": "o2_b2s3_voltage", "fullName": "O2 {O2L:7} Voltage", "unit": "V"},
    "ff121b": {"shortName": "o2_b2s4_voltage", "fullName": "O2 {O2L:8} Voltage", "unit": "V"},
    "ff1220": {"shortName": "accel_x", "fullName": "Acceleration Sensor(X axis)", "unit": "g"},
    "ff1221": {"shortName": "accel_y", "fullName": "Acceleration Sensor(Y axis)", "unit": "g"},
    "ff1222": {"shortName": "accel_z", "fullName": "Acceleration Sensor(Z axis)", "unit": "g"},
    "ff1223": {"shortName": "accel_total", "fullName": "Acceleration Sensor(Total)", "unit": "g"},
    "ff1225": {"shortName": "torque", "fullName": "Torque", "unit": "ft-lb"},
    "ff1226": {"shortName": "horsepower_wheels", "fullName": "Horsepower (At the wheels)", "unit": "hp"},
    "ff122d": {"shortName": "time_0_60mph", "fullName": "0-60mph Time", "unit": "s"},
    "ff122e": {"shortName": "time_0_100kph", "fullName": "0-100kph Time", "unit": "s"},
    "ff122f": {"shortName": "time_quarter_mile", "fullName": "1/4 mile time", "unit": "s"},
    "ff1230": {"shortName": "time_eighth_mile", "fullName": "1/8 mile time", "unit": "s"},
    "ff1237": {"shortName": "spd_diff_gps_obd", "fullName": "GPS vs OBD Speed difference", "unit": "km/h"},
    "ff1238": {"shortName": "voltage_obd_adapter", "fullName": "Voltage (OBD Adapter)", "unit": "V"},
    "ff123a": {"shortName": "gps_satellites", "fullName": "GPS Satellites", "unit": None},
    "ff123b": {"shortName": "gps_bearing", "fullName": "GPS Bearing", "unit": "°"},
    "ff1240": {"shortName": "o2_o2l1_wide_eq_ratio", "fullName": "O2 {O2L:1} Wide Range Equivalence Ratio", "unit": "λ"},
    "ff1241": {"shortName": "o2_o2l2_wide_eq_ratio", "fullName": "O2 {O2L:2} Wide Range Equivalence Ratio", "unit": "λ"},
    "ff1242": {"shortName": "o2_o2l3_wide_eq_ratio", "fullName": "O2 {O2L:3} Wide Range Equivalence Ratio", "unit": "λ"},
    "ff1243": {"shortName": "o2_o2l4_wide_eq_ratio", "fullName": "O2 {O2L:4} Wide Range Equivalence Ratio", "unit": "λ"},
    "ff1244": {"shortName": "o2_o2l5_wide_eq_ratio", "fullName": "O2 {O2L:5} Wide Range Equivalence Ratio", "unit": "λ"},
    "ff1245": {"shortName": "o2_o2l6_wide_eq_ratio", "fullName": "O2 {O2L:6} Wide Range Equivalence Ratio", "unit": "λ"},
    "ff1246": {"shortName": "o2_o2l7_wide_eq_ratio", "fullName": "O2 {O2L:7} Wide Range Equivalence Ratio", "unit": "λ"},
    "ff1247": {"shortName": "o2_o2l8_wide_eq_ratio", "fullName": "O2 {O2L:8} Wide Range Equivalence Ratio", "unit": "λ"},
    "ff1249": {"shortName": "air_fuel_ratio_measured", "fullName": "Air Fuel Ratio(Measured)", "unit": ":1"},
    "ff124d": {"shortName": "air_fuel_ratio_commanded", "fullName": "Air Fuel Ratio(Commanded)", "unit": ":1"},
    "ff124f": {"shortName": "time_0_200kph", "fullName": "0-200kph Time", "unit": "s"},
    "ff1257": {"shortName": "co2_gkm_instant", "fullName": "CO₂ in g/km (Instantaneous)", "unit": "g/km"},
    "ff1258": {"shortName": "co2_gkm_avg", "fullName": "CO₂ in g/km (Average)", "unit": "g/km"},
    "ff125a": {"shortName": "fuel_flow_rate_min", "fullName": "Fuel flow rate/minute", "unit": "cc/min"},
    "ff125c": {"shortName": "fuel_cost_trip", "fullName": "Fuel cost (trip)", "unit": "cost"},
    "ff125d": {"shortName": "fuel_flow_rate_hr", "fullName": "Fuel flow rate/hour", "unit": "L/hr"},
    "ff125e": {"shortName": "time_60_120mph", "fullName": "60-120mph Time", "unit": "s"},
    "ff125f": {"shortName": "time_60_80mph", "fullName": "60-80mph Time", "unit": "s"},
    "ff1260": {"shortName": "time_40_60mph", "fullName": "40-60mph Time", "unit": "s"},
    "ff1261": {"shortName": "time_80_100mph", "fullName": "80-100mph Time", "unit": "s"},
    "ff1263": {"shortName": "avg_trip_speed_moving", "fullName": "Average trip speed(whilst moving only)", "unit": "km/h"},
    "ff1264": {"shortName": "time_100_0kph", "fullName": "100-0kph Time", "unit": "s"},
    "ff1265": {"shortName": "time_60_0mph", "fullName": "60-0mph Time", "unit": "s"},
    "ff1266": {"shortName": "trip_time_since_start", "fullName": "Trip Time(Since journey start)", "unit": "s"},
    "ff1267": {"shortName": "trip_time_stationary", "fullName": "Trip time(whilst stationary)", "unit": "s"},
    "ff1268": {"shortName": "trip_time_moving", "fullName": "Trip time(whilst moving)", "unit": "s"},
    "ff1269": {"shortName": "volumetric_efficiency_calc", "fullName": "Volumetric Efficiency (Calculated)", "unit": "%"},
    "ff126a": {"shortName": "distance_to_empty_est", "fullName": "Distance to empty (Estimated)", "unit": "km"},
    "ff126b": {"shortName": "fuel_remaining_calc", "fullName": "Fuel Remaining (Calculated from vehicle profile)", "unit": "%"},
    "ff126d": {"shortName": "cost_per_km_instant", "fullName": "Cost per mile/km (Instant)", "unit": "€/km"},
    "ff126e": {"shortName": "cost_per_km_trip", "fullName": "Cost per mile/km (Trip)", "unit": "€/km"},
    "ff1270": {"shortName": "barometer_android", "fullName": "Barometer (on Android device)", "unit": "mb"},
    "ff1271": {"shortName": "fuel_used_trip", "fullName": "Fuel used (trip)", "unit": "L"},
    "ff1272": {"shortName": "avg_trip_speed_overall", "fullName": "Average trip speed(whilst stopped or moving)", "unit": "km/h"},
    "ff1273": {"shortName": "engine_kw_wheels", "fullName": "Engine kW (At the wheels)", "unit": "kW"},
    "ff1275": {"shortName": "time_80_120kph", "fullName": "80-120kph Time", "unit": "s"},
    "ff1276": {"shortName": "time_60_130mph", "fullName": "60-130mph Time", "unit": "s"},
    "ff1277": {"shortName": "time_0_30mph", "fullName": "0-30mph Time", "unit": "s"},
    "ff1278": {"shortName": "time_0_100mph", "fullName": "0-100mph Time", "unit": "s"},
    "ff1280": {"shortName": "time_100_200kph", "fullName": "100-200kph Time", "unit": "s"},
    "ff1282": {"shortName": "egt_b1_s2", "fullName": "Exhaust gas temp Bank 1 Sensor 2", "unit": "°C"},
    "ff1283": {"shortName": "egt_b1_s3", "fullName": "Exhaust gas temp Bank 1 Sensor 3", "unit": "°C"},
    "ff1284": {"shortName": "egt_b1_s4", "fullName": "Exhaust gas temp Bank 1 Sensor 4", "unit": "°C"},
    "ff1286": {"shortName": "egt_b2_s2", "fullName": "Exhaust gas temp Bank 2 Sensor 2", "unit": "°C"},
    "ff1287": {"shortName": "egt_b2_s3", "fullName": "Exhaust gas temp Bank 2 Sensor 3", "unit": "°C"},
    "ff1288": {"shortName": "egt_b2_s4", "fullName": "Exhaust gas temp Bank 2 Sensor 4", "unit": "°C"},
    "ff128a": {"shortName": "nox_post_scr", "fullName": "NOx Post SCR", "unit": "ppm"},
    "ff1296": {"shortName": "pct_city_driving", "fullName": "Percentage of City driving", "unit": "%"},
    "ff1297": {"shortName": "pct_highway_driving", "fullName": "Percentage of Highway driving", "unit": "%"},
    "ff1298": {"shortName": "pct_idle_driving", "fullName": "Percentage of Idle driving", "unit": "%"},
    "ff129a": {"shortName": "android_battery_level", "fullName": "Android device Battery Level", "unit": "%"},
    "ff129b": {"shortName": "dpf_b1_outlet_temp", "fullName": "DPF Bank 1 Outlet Temperature", "unit": "°C"},
    "ff129c": {"shortName": "dpf_b2_inlet_temp", "fullName": "DPF Bank 2 Inlet Temperature", "unit": "°C"},
    "ff129d": {"shortName": "dpf_b2_outlet_temp", "fullName": "DPF Bank 2 Outlet Temperature", "unit": "°C"},
    "ff129e": {"shortName": "maf_sensor_b", "fullName": "Mass air flow sensor B", "unit": "g/s"},

    # ---------- FF12A* – Suralimentation / Pression (B) ----------
    "ff12a1": {"shortName": "intake_manifold_abs_pressure_b", "fullName": "Intake Manifold Abs Pressure B", "unit": "kPa"},
    "ff12a4": {"shortName": "boost_pressure_commanded_b", "fullName": "Boost Pressure Commanded B", "unit": "kPa"},
    "ff12a5": {"shortName": "boost_pressure_sensor_a", "fullName": "Boost Pressure Sensor A", "unit": "kPa"},
    "ff12a6": {"shortName": "boost_pressure_sensor_b", "fullName": "Boost Pressure Sensor B", "unit": "kPa"},
    "ff12ab": {"shortName": "exhaust_pressure_b2", "fullName": "Exhaust Pressure Bank 2", "unit": "kPa"},

    # ---------- FF12B* – DPF & Hybrid/EV ----------
    "ff12b0": {"shortName": "dpf_b1_inlet_pressure", "fullName": "DPF Bank 1 Inlet Pressure", "unit": "kPa"},
    "ff12b1": {"shortName": "dpf_b1_outlet_pressure", "fullName": "DPF Bank 1 Outlet Pressure", "unit": "kPa"},
    "ff12b2": {"shortName": "dpf_b2_inlet_pressure", "fullName": "DPF Bank 2 Inlet Pressure", "unit": "kPa"},
    "ff12b3": {"shortName": "dpf_b2_outlet_pressure", "fullName": "DPF Bank 2 Outlet Pressure", "unit": "kPa"},
    "ff12b4": {"shortName": "hybrid_ev_batt_current", "fullName": "Hybrid/EV System Battery Current", "unit": "A"},
    "ff12b5": {"shortName": "hybrid_ev_batt_power", "fullName": "Hybrid/EV System Battery Power", "unit": "W"},
    "ff12b6": {"shortName": "positive_kinetic_energy_pke", "fullName": "Positive Kinetic Energy (PKE)", "unit": "km/hr^2"},

    # ---------- FF52xx – Moyennes long terme ----------
    "ff5201": {"shortName": "mpg_long_term_avg", "fullName": "Miles Per Gallon(Long Term Average)", "unit": "mpg"},
    "ff5202": {"shortName": "kpl_long_term_avg", "fullName": "Kilometers Per Litre(Long Term Average)", "unit": "kpl"},
    "ff5203": {"shortName": "l_per_100_long_term_avg", "fullName": "Litres Per 100 Kilometer(Long Term Average)", "unit": "L/100km"},
}

# --- Ensure critical GPS/Speed PIDs are present (idempotent) ---
_CRITICAL_TORQUE_CODES = {
    "0d":     {"shortName": "speed_obd",            "fullName": "Speed (OBD)",           "unit": "km/h"},
    "ff1001": {"shortName": "gps_spd",              "fullName": "Vehicle Speed (GPS)",   "unit": "km/h"},
    "ff1005": {"shortName": TORQUE_GPS_LON,         "fullName": "GPS Longitude",         "unit": "°"},
    "ff1006": {"shortName": TORQUE_GPS_LAT,         "fullName": "GPS Latitude",          "unit": "°"},
    "ff1010": {"shortName": TORQUE_GPS_ALTITUDE,    "fullName": "GPS Altitude",          "unit": "m"},
    "ff1239": {"shortName": TORQUE_GPS_ACCURACY,    "fullName": "GPS Accuracy",          "unit": "m"},
}
for _k, _v in _CRITICAL_TORQUE_CODES.items():
    TORQUE_CODES.setdefault(_k, _v)
# --- end ensure block ---
