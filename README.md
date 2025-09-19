![HA Torque](https://raw.githubusercontent.com/Marlboro62/Torque-Lite-Pro/main/docs/images/logo.png)

[![Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/nothing_one)

# Torque Pro — Home Assistant Integration 🇬🇧

> **Real-time push** of **OBD-II** data from the Android app **Torque Pro** into **Home Assistant**.  
> Dynamically creates sensors, a per-vehicle GPS *device tracker*, keeps **native metric units**, localizes labels (EN/FR), and exposes an **HTTP endpoint**.

*[Version française]*: voir [readme_fr.md](./readme_fr.md)

![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Custom%20Component-03a9f4)
![HACS](https://img.shields.io/badge/HACS-Custom-blue.svg)
![Status](https://img.shields.io/badge/iot__class-local__push-brightgreen)
![Version](https://img.shields.io/badge/version-2025.09.3.2-informational)

---

## 🔌 Required Hardware

- **OBD-II Bluetooth (ELM327)**
- Amazon: [OBD2 Bluetooth](https://amzn.to/48bHmPj) *(affiliate link — thank you!)*

---

## ✨ Features

- **Local HTTP receiver** at **`/api/torque_pro`** (GET/POST/HEAD).  
  Home Assistant authentication **required by default** (recommended).
- **Dynamic entity creation**:
  - *Sensors* for known PIDs (with inferred **device_class**/**state_class** when appropriate).
  - **Per-vehicle GPS device tracker** (lat/lon/alt/accuracy/GPS speed).
- **Data hygiene & robustness**: NaN/Inf filtering, validated GPS bounds, **s→min** rounding for trip times, **L/100 ↔ KPL/MPG** synthesis when one side is missing.
- **Language & labels**: EN/FR with automatic fallback.
- **Stable IDs**: no accidental fusion between vehicles/profiles.
- **Diagnostics**: detailed, sensitive fields redacted.

> Domain: `torque_pro` — IoT class: `local_push` — Dependency: `http`

---

## 📦 Installation

### Via HACS (recommended)
1. **HACS → Integrations →** ••• **→ Custom repositories** → add this repo.
2. Search **Torque Pro** and install.
3. Restart Home Assistant if prompted.

### Manual install
1. Copy `custom_components/torque_pro/` into `config/custom_components/`.
2. Restart Home Assistant.

---

## ⚙️ Configuration (UI)

1. **Settings → Devices & Services → Add Integration → “Torque Pro”.**
2. Fill in:
   - **Email (required)**: used to **route** uploads (`eml=<your email>`).
   - **Language**: `en` or `fr` (sensor labels).
   - **Memory preferences**: session TTL (60–86400 s), LRU size (10–1000).

> You can create **multiple entries** (e.g., *Torque Pro Aline* / *Torque Pro Mikaël*) and route each phone via its **`eml=`**.

---

## 📱 “Torque Pro” App Settings (Android)

**Torque Pro → Settings → Data Logging & Upload → Web server URL**

- **URL**: `https://your-domain/api/torque_pro`
- **Method**: GET **or** POST (both supported)
- **Parameters** (in the URL, after `?`):
  - `session=${session}`  ← **required**
  - `eml=<email>`        ← must **match** the HA entry that should receive the data
  - `profileName=${profile}` *(or `vehicle=${profile}` / `name=${profile}`)*  ← **recommended** (keeps each profile/car/person separate)
  - `id=${vehicleId}`     *(optional, encouraged)*
  - `lang=en`             *(optional)*
  - **GPS fallback** *(if your profile doesn’t include GPS PIDs)*:  
    `lat=${lat}&lon=${lon}&alt=${altitude}&acc=${gpsacc}`

> **Torque automatically** appends `k<code>=<value>` pairs for PIDs.  
> Do **not** add `imperial=`: ingestion remains **metric-native** (HA handles display conversion).

### Examples (multi-entry)
- **Aline’s phone**:  
  `https://torque.duckdns.org/api/torque_pro?eml=aline.couvreur10@gmail.com&lang=en&session=${session}&profileName=${profile}&id=${vehicleId}`
- **Mikaël’s phone**:  
  `https://torque.duckdns.org/api/torque_pro?eml=<mikael_email>&lang=en&session=${session}&profileName=${profile}&id=${vehicleId}`

---

## ✅ PID Best Practices

Avoid checking *everything* in Torque:

1. Too many PIDs **slow down** ECU reads and **inflate** uploads.
2. You’ll create **unnecessary sensors** (noise).
3. Risk of **duplicates**: the integration already synthesizes **L/100 ↔ KPL/MPG** if one side is present.
4. Many PIDs are **unsupported** on some ECUs (0/N.A.) — uncheck them.

---

## 🧩 Entities Created

- **Device** per vehicle (ID **deterministic**).
- **Sensors (`sensor.*`)**: created *on the fly* (EN/FR label, unit, suggested display precision).  
  Examples: RPM, OBD/GPS speed, temperatures, MAF/MAP, barometric pressure, battery voltage, fuel economy, etc.
- **Device tracker (`device_tracker.*`)**: lat/lon/alt/accuracy/GPS speed.

> GPS lat/lon feed the **device_tracker** and aren’t duplicated as sensors.

---

## 🔐 Security (important)

Torque **cannot** send an `Authorization` header. For secure public exposure:

- Use a **reverse proxy** (Nginx/Traefik) that **injects** `Authorization: Bearer <token>`.
- Or restrict access via **VPN** (WireGuard/Tailscale) / local network.
- **Avoid** exposing the endpoint openly on the Internet.

> By default, the endpoint requires HA auth. Never expose tokens in clear text.

---

## ⚙️ Behavior & Options

- **LRU/TTL memory**: sessions kept with configurable TTL (60–86400 s) and max size (10–1000).
- **Availability**: entities remain available while recent data exists (or last restored / 0 for some counters).
- **Units / display**:
  - **Metric-native** ingestion (no destructive conversions).
  - **L/100 ↔ KPL/MPG** synthesis if one side is missing.
  - **s→min** rounding for trip time.
  - **Suggested display precision** by unit (speed, pressure, etc.).
- **Stable per-vehicle/profile ID** (prevents cross-profile/phone fusion):
  - based on `slug(profileName)` + `id[:4]` + small email-derived salt (if present).
- **Multi-entry**: `eml=` **routes** to the proper entry.

---

## 🛠️ Troubleshooting

- **“IGNORED / No matching route”** in logs → the `eml=` URL param doesn’t match **any configured entry**.
- **404 Not Found** → no active entry for the integration (HTTP view inactive).
- **No data** → ensure `session=${session}` and OBD/network connectivity.

### Debug logs (optional)
```yaml
logger:
  logs:
    custom_components.torque_pro.api: debug
    custom_components.torque_pro.coordinator: debug
```
You’ll see `Resolved profile → …` with the computed ID.

---

## 📄 License

This distribution is governed by the **Written Authorization Required License (LAER-TPHA-1.0)** — *Permitted use:* **Torque Pro ↔ Home Assistant**.

**TL;DR**: **personal, non-commercial** use. Any other use requires **written authorization**.

### ✅ Allowed without prior approval
- Install and use **on your own Home Assistant instance**, for **non-commercial** purposes.

### ❌ Forbidden without written authorization
- Reproduction, forks or published derivative works,
- Modification, publication or **distribution** of code/binary,
- Integration into other projects/products,
- Hosting, **SaaS**, marketplaces, images/packs,
- Any **commercial** use (direct or indirect).

See [`LICENSE`](./LICENSE).  
Request authorization: [open a “License request” issue](../../issues/new?assignees=&labels=license%2Clegal&template=license_request.yml&title=License%20request%3A%20).

> *“Torque”, “Torque Lite” and “Torque Pro” are trademarks of their respective owners.*

---

## 🙌 Acknowledgements

- **Torque Pro** app (Android — OBD-II)
- **Home Assistant** community

---

## ☕ Support

If you enjoy this project, you can support me here:  
[![Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/nothing_one)

---

## 📄 Changelog (excerpt)

- **2025.09.3** — Manifest versioning, API/coordinator robustness cleanup, FR i18n, hardened diagnostics.  
- **2025.09.3.1** — Multi-entry email routing, metric-native ingestion (unit preference annotation), legacy unique_id preservation, persistent HTTP view (inactive 404), app version parsing fix.  
- **2025.09.3.2** — Deterministic per-vehicle profile ID (slug(profileName)+id[:4]+email-salt) to prevent cross-device fusion; rounded trip times (s→min) and dropped negative GPS accuracy; improved profile name normalization/memory; enriched diagnostics (profile.Id, unit_preference, app version); sensor platform overhaul: stable unique_id + migration, suggested precision & device/state classes, zero-default for trip/distance/time counters, non-finite filtering, improved icon mapping.
