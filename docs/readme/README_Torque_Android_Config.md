# Configure Torque (Android) for Web Upload

This guide shows how to configure **Torque Lite/Pro** on Android to select PIDs to log and upload them to a web endpoint (e.g., a Home Assistant webhook). Screenshots are in French; labels match the English app.

> ⚠️ Live upload can use mobile data. Prefer Wi‑Fi or set upload conditions accordingly.

## Prerequisites
- Android phone with **Torque** installed
- Bluetooth OBD‑II adapter paired in Android
- A HTTPS endpoint to receive data (Home Assistant webhook or your own server)

## Steps (1–15)

### Step 01 – Open Torque → tap the **gear** icon.
![](docs/images/TorquePhone/01_open_settings.png)

### Step 02 – Choose **Settings**.
![](docs/images/TorquePhone/02_settings_menu.png)

### Step 03 – Go to **Data Logging & Upload**.
![](docs/images/TorquePhone/03_data_logging_menu.png)

### Step 04 – Tap **Select what to log**.
![](docs/images/TorquePhone/04_select_what_to_log.png)

### Step 05 – In the PID list, open the **⋮** menu.
![](docs/images/TorquePhone/05_pid_manager_overflow.png)

### Step 06 – Tick the sensors you want to upload.
![](docs/images/TorquePhone/06_choose_sensors.png)

### Step 07 – Enable **Upload to web server** and tap **Web server URL**.
![](docs/images/TorquePhone/07_enable_web_upload.png)

### Step 08 – Enter your **Web server URL** (e.g., HA webhook).
![](docs/images/TorquePhone/08_enter_web_url.png)

### Step 09 – Enable **Send https: Bearer Token** if required by your server.
![](docs/images/TorquePhone/09_set_bearer_token.png)

### Step 10 – Paste the **Bearer token** (e.g., LLAT) and confirm.
![](docs/images/TorquePhone/10_enter_bearer_token.png)

### Step 11 – Tap **User email** (optional).
![](docs/images/TorquePhone/11_set_user_email.png)

### Step 12 – Enter the email to associate with uploads (optional).
![](docs/images/TorquePhone/12_enter_user_email.png)

### Step 13 – Adjust **File Logging** preferences if you also keep local logs.
![](docs/images/TorquePhone/13_file_logging_prefs.png)

### Step 14 – Review **Trip Logging** options.
![](docs/images/TorquePhone/14_trip_logging_prefs.png)

### Step 15 – On the home screen, tap the **vehicle profile** to select/switch vehicles.
![](docs/images/TorquePhone/15_choose_vehicle_profile.png)

---

## Web server URL examples
- **Home Assistant webhook** (recommended):
  ```
  https://<HA_BASE_URL>/api/webhook/<YOUR_WEBHOOK_ID>
  ```
- **Custom backend**: any HTTPS endpoint that responds with `OK`/`200` works. Torque sends data as **HTTP GET** query parameters.

## Notes on tokens & email
- **Send https: Bearer Token** adds `Authorization: Bearer <token>` to HTTPS uploads. Use it only if your endpoint requires it.
- The **User email** field is optional and only used by certain web services; it isn’t needed for Home Assistant webhooks.

## Tips
- Keep the number of logged sensors small for faster updates.
- Use **Upload only when OBD connected** to avoid empty logs.
- If uploads fail, tap **Test web logging** and check your server logs.

## License
You can reuse this README in your repository. Replace or extend the screenshots as needed.