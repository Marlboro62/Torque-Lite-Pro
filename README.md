<div style="text-align: center;">
  <br>
  <img src="https://raw.githubusercontent.com/Marlboro62/Torque-Lite-Pro/main/docs/images/logo.png" alt="HA Torque logo" width="336" style="display: block; margin: 0 auto;" />
</div>

# Torque Pro — Home Assistant Integration

<div style="border:1px solid #f0c36d; background:#fff8e1; padding:12px 16px; border-radius:8px;">
  <strong>⚠️ Warning — Unofficial Project</strong><br>
  This project is developed independently and is <strong>not affiliated with, approved by, or endorsed by</strong>
  the <strong>Torque Lite/Pro</strong> application.<br>
  <small>“Torque”, “Torque Lite”, and “Torque Pro” are trademarks of their respective owners.</small>
</div>

---

> **Real‑time push of OBD‑II data from the Android Torque Pro app into Home Assistant.**  
> Dynamically creates sensors, a per‑vehicle GPS *device tracker*, normalizes units (metric/imperial), translates labels (EN/FR), and exposes a secured HTTP endpoint.

*[French version]*: see [README.fr.md](./README.fr.md)

![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Custom%20Component-03a9f4)
![Status](https://img.shields.io/badge/iot__class-local__push-brightgreen)
![Version](https://img.shields.io/badge/version-2025.09.3-informational)
![HACS](https://img.shields.io/badge/HACS-Custom-blue.svg)

---

## 🔌 Required equipment: OBD-II interface

- **OBD2 Bluetooth (ELM327)**
- Amazon : [OBD2 Bluetooth](https://amzn.to/48bHmPj)

> *Affiliate link: this supports the project at no extra cost to you.*

---

## ✨ Features

- **Local HTTP intake** on `/api/torque_pro` (GET/POST/HEAD). Home Assistant auth required by default (**recommended**).
- **Dynamic entity creation**:
  - *Sensors* for known OBD‑II PIDs (with inferred *device_class* / *state_class* when appropriate).
  - **Per‑vehicle GPS device_tracker** (latitude, longitude, accuracy, altitude, GPS speed).
- **Normalization & resilience**: consistent filtering of `NaN/Inf`, value/unit cleanup.
- **Units & language**: metric/imperial, EN/FR labels (automatic fallback if a label is unknown).
- **Backward compat**: same `unique_id` scheme as previous releases to avoid migrations.
- **Hardened diagnostics**: sensitive fields (email, tokens, VIN, coordinates, etc.) are masked in the report.

> Domain: `torque_pro` — Type: `service` — IoT class: `local_push` — Dependencies: `http` — Requirements: `pint>=0.24`

---

## 📦 Installation

### Via HACS (recommended)
1. **HACS → Integrations →** ••• **→ Custom repositories** → add the repository containing this component.
2. Search for **Torque Pro** and install.
3. Restart Home Assistant if prompted.

### Manual install
1. Copy the folder `custom_components/torque_pro/` into your Home Assistant config at `config/custom_components/`.
2. Restart Home Assistant.

---

## ⚙️ Configuration (UI)

1. **Settings → Devices & Services → Add Integration → “Torque Pro”.**
2. Fill in:
   - **Email** (required): used as an API‑side filter (uploads must include `eml=<your email>`).
   - **Units**: metric or imperial (automatic conversion).
   - **Language**: `en` or `fr` for sensor labels.
3. Open **Options** to fine‑tune:
   - **In‑memory session TTL** (range **60–86400 s**).
   - **Max cache size** (range **10–1000** sessions).

> No YAML needed — everything is configured via the UI.

---

## 🔐 Authentication & security

The endpoint **requires Home Assistant authentication** by default (`Authorization: Bearer <TOKEN>`). The Torque Pro app **cannot add a custom HTTP header**, so you will need one of the following setups.

### Option A — Reverse proxy (recommended)
Send uploads through a proxy that **injects** the `Authorization` header. Example **Nginx**:

```nginx
# replace <HA_HOST:PORT> and <YOUR_LONG_LIVED_TOKEN>
location /api/torque_pro {
    proxy_pass http://<HA_HOST:PORT>/api/torque_pro;
    proxy_set_header Authorization "Bearer <YOUR_LONG_LIVED_TOKEN>";
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header Host $host;
    # (optional) also restrict by IP / firewall
}
```

> Create the **Long‑Lived Access Token** under **Profile → Long‑Lived Access Tokens**. Treat this token as a secret.

**Caddy** example:

```caddyfile
:443 {
  reverse_proxy <HA_HOST:PORT> {
    header_up Authorization "Bearer <YOUR_LONG_LIVED_TOKEN>"
  }
}
```

### Option B — (Not recommended) Disable auth in the view
In `api.py`, the view defines:

```python
requires_auth = True  # set to False only if your app cannot send a token
```

Switching this to `False` **exposes** the endpoint publicly if your instance is reachable from the internet. Avoid unless on a strictly isolated LAN.

---

## 📱 “Torque Pro” app settings (Android)

In **Torque Pro**:  
**Settings → Data Logging & Upload → Web server URL**

- **URL**: the public URL of your proxy or Home Assistant, e.g.  
  `https://example.com/api/torque_pro`
- **Method**: GET or POST (both supported).
- **Parameters sent**: Torque automatically appends `k<code>=<value>` pairs for PIDs.  
  **Also add**:
  - `session`: a session id (e.g. `${session}`).
  - `eml`: your email (must **match** the HA config if the filter is enabled).
  - (optional) `id` (vehicle id), `vehicle`/`profileName` (profile name), `vin`, `lang`, `imperial`.
  - (GPS fallback) `lat`, `lon`, `alt`, `acc` if your profile does not send the GPS PIDs.

> The integration tolerates many key variants from Torque and automatically sanitizes values.

---

## 🧪 Quick test (without Torque)

```bash
curl -X POST "https://<your_domain>/api/torque_pro" \
  -H "Authorization: Bearer <YOUR_LONG_LIVED_TOKEN>" \
  -d "session=test-123" \
  -d "eml=you@example.com" \
  -d "id=veh-001" \
  -d "vehicle=My Car" \
  -d "k0d=88.0" \            # Speed (OBD)
  -d "kff1006=48.8566" \     # GPS Lat
  -d "kff1005=2.3522" \      # GPS Lon
  -d "kff1010=35" \          # GPS Altitude (m)
  -d "kff1239=6.5"           # GPS Accuracy (m)
```

If everything is OK, you will see a **device** for the vehicle and the corresponding entities (sensors + `device_tracker`).

---

## 🧩 Entities created

- **Device** per vehicle (stable identifier).
- **Sensors**: created *on the fly* for each detected “creatable” PID (EN/FR label, unit, display precision).  
  Common examples: RPM, OBD/GPS speed, coolant temp, MAF, MAP, barometric pressure, battery voltage, fuel consumption, etc.
- **Device tracker**: latitude/longitude/accuracy/altitude/GPS speed + `gps_time` when present.

> Pure GPS values (lat/lon) are **not** duplicated as sensors; they feed the *device_tracker* instead.

---

## 🧰 Options & behavior

- **TTL & in‑memory cache**: received sessions are kept in an LRU cache with a configurable TTL (**60–86400 s**) and a max size (**10–1000**).  
- **Availability**: entities remain available as long as the coordinator retains recent data.  
- **Units**: automatic conversions (km/h ↔ mph, kPa/bar ↔ psi, m ↔ ft, °C ↔ °F, etc.).  
- **Language**: labels translated to EN (or FR) when known; otherwise an English fallback is used.

---

## 🛠️ Troubleshooting

- **No data**: check the **token** or the proxy (Option A), and ensure Torque sends both `session` **and** `eml` (if configured).  
- **Missing entities**: some unit‑less PIDs are not created by default (except text‑only status/state/mode sensors).  
- **Wrong coordinates**: the integration validates lat/lon bounds. Ensure Torque sends GPS PIDs (`ff1005/ff1006/ff1010/ff1239`) or parameters `lat/lon/alt/acc`.

Generate a **diagnostics report** from Home Assistant’s UI (sensitive info will be masked).

---

## 🧾 License

This distribution is subject to the **Written Authorization Required License (LAER-TPHA-1.0)** — *Permitted use:* **Torque Pro ↔ Home Assistant**.

**TL;DR:** personal, **non-commercial use only**. Any other use requires **written authorization**.

### ✅ Allowed without prior approval
- Install and use this component **on your own Home Assistant instance** to connect the Android app *Torque Pro*,
- for **strictly non-commercial** purposes.

### ❌ Prohibited without prior written consent
- Reproduction, forking, or publishing derivative works,
- Modification, publication, or **distribution** of the code/binaries,
- Integration into other projects/products,
- Hosting, **SaaS**, marketplaces, images/packs,
- Any **commercial** use (direct or indirect).

**Full text:** see [`LICENSE`](./LICENSE).  
**Request authorization:** [open a “License request” issue](../../issues/new?assignees=&labels=license%2Clegal&template=license_request.yml&title=License%20request%3A%20).

> *“Torque”, “Torque Lite”, and “Torque Pro” are trademarks of their respective owners. Unofficial project.*


## 🙌 Acknowledgments

- **Torque Pro** (OBD‑II) — Android
- Home Assistant community

---

## 📄 Changelog (excerpt)

- **2025.09.3** — Manifest versioning, API/coordinate robustness cleanup, FR i18n, hardened diagnostics.
