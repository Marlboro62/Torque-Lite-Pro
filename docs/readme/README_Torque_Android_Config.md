# Configure Torque (Android) with a Bluetooth OBD‑II Adapter

This guide walks through setting up **Torque Lite/Pro** on an Android phone and (optionally) enabling data upload to your server/Home Assistant.

> Works with most ELM327‑compatible Bluetooth adapters. Use a reputable brand to avoid connection issues.

---

## Prerequisites

- Android phone with **Torque Lite** or **Torque Pro** installed
- A **Bluetooth OBD‑II** adapter (ELM327 compatible)
- Your car’s OBD port (usually under the dashboard)
- *(Optional)* A server endpoint (e.g., Home Assistant webhook) if you plan to upload live data

---

## Quick Start

1. **Plug the OBD‑II adapter** into the vehicle’s OBD port.
2. **Pair the adapter in Android**: *Settings → Bluetooth* → select the adapter (PIN often `1234` or `0000`).
3. **Open Torque** → *Settings → OBD2 Adapter Settings*.
4. **Connection type**: **Bluetooth** → **Choose your adapter**.
5. Enable **Faster communication** and (if needed) **Use alternate OBD header/connection** for older adapters.
6. *(Optional)* Create a **Vehicle Profile** and assign the adapter.
7. *(Optional)* For server upload: *Settings → Data Logging & Upload* → **Upload to Web Server** and set your URL.
8. Return to the dashboard; confirm **Adapter** and **ECU** icons are both green.

---

## Detailed Steps (with 16 screenshots)

### 1) Install & launch Torque
Open Torque and grant requested permissions (Bluetooth, location for GPS logging).  
![Step 01 – Launch_Torque_and_grant_permissions](https://raw.githubusercontent.com/Marlboro62/Torque-Lite-Pro/main/docs/images/Torque/01_Launch_Torque_and_grant_permissions.png)

### 2) Pair the adapter in Android
Android **Settings → Bluetooth** → pair your ELM327 device (default PIN is often `1234`/`0000`).  
![Step 02 – Pair_Bluetooth_OBD2_adapter_in_Android](https://raw.githubusercontent.com/Marlboro62/Torque-Lite-Pro/main/docs/images/Torque/02_Pair_Bluetooth_OBD2_adapter_in_Android.png)

### 3–7) Adapter configuration in Torque
- **Settings → OBD2 Adapter Settings**  
- **Connection type**: **Bluetooth**  
- **Choose Bluetooth device**: pick the adapter you just paired  
- Recommended options:  
  - **Faster communication** ✅  
  - **Disable ELM327 auto‑timing** *(try if you see timeouts)*  
  - **Alternate Bluetooth connection** *(use only if you cannot connect otherwise)*  
![Step 03 – Open_Torque_Settings](https://raw.githubusercontent.com/Marlboro62/Torque-Lite-Pro/main/docs/images/Torque/03_Open_Torque_Settings.png)
![Step 04 – OBD2_Adapter_Settings](https://raw.githubusercontent.com/Marlboro62/Torque-Lite-Pro/main/docs/images/Torque/04_OBD2_Adapter_Settings.png)
![Step 05 – Select_connection_type_Bluetooth](https://raw.githubusercontent.com/Marlboro62/Torque-Lite-Pro/main/docs/images/Torque/05_Select_connection_type_Bluetooth.png)
![Step 06 – Choose_your_paired_adapter](https://raw.githubusercontent.com/Marlboro62/Torque-Lite-Pro/main/docs/images/Torque/06_Choose_your_paired_adapter.png)
![Step 07 – Recommended_adapter_options](https://raw.githubusercontent.com/Marlboro62/Torque-Lite-Pro/main/docs/images/Torque/07_Recommended_adapter_options.png)

### 8–9) Create a Vehicle Profile (optional but recommended)
- **Settings → Vehicle Profile → Add Profile**  
- Fill in name, fuel type, engine displacement, weight (if you want MPG/consumption calcs).  
- Assign your **paired adapter** to this profile.  
![Step 08 – Create_Vehicle_Profile](https://raw.githubusercontent.com/Marlboro62/Torque-Lite-Pro/main/docs/images/Torque/08_Create_Vehicle_Profile.png)
![Step 09 – Fill_profile_details_and_assign_adapter](https://raw.githubusercontent.com/Marlboro62/Torque-Lite-Pro/main/docs/images/Torque/09_Fill_profile_details_and_assign_adapter.png)

### 10) Verify the connection
Return to the main screen and connect. The **Adapter** and **ECU** icons should turn **green**.  
![Step 10 – Check_connection_status](https://raw.githubusercontent.com/Marlboro62/Torque-Lite-Pro/main/docs/images/Torque/10_Check_connection_status.png)

### 11) Add gauges (optional)
Long‑press on the dashboard → **Add display** → choose a gauge type and PID.  
![Step 11 – Add_dashboard_gauges_optional](https://raw.githubusercontent.com/Marlboro62/Torque-Lite-Pro/main/docs/images/Torque/11_Add_dashboard_gauges_optional.png)

### 12–15) Enable data logging & web upload (optional)
- **Settings → Data Logging & Upload**  
- Toggle **Upload to web‑server**  
- **Web server URL**: use your endpoint (examples below)  
- Choose **Upload only when connected** and **Mobile data/Wi‑Fi** according to your plan  
- Select which **PIDs/sensors** to upload  
![Step 12 – Open_Data_Logging_and_Upload](https://raw.githubusercontent.com/Marlboro62/Torque-Lite-Pro/main/docs/images/Torque/12_Open_Data_Logging_and_Upload.png)
![Step 13 – Enable_Upload_to_Web_Server_and_set_URL](https://raw.githubusercontent.com/Marlboro62/Torque-Lite-Pro/main/docs/images/Torque/13_Enable_Upload_to_Web_Server_and_set_URL.png)
![Step 14 – Choose_upload_conditions_only_when_connected](https://raw.githubusercontent.com/Marlboro62/Torque-Lite-Pro/main/docs/images/Torque/14_Choose_upload_conditions_only_when_connected.png)
![Step 15 – Select_PIDs_to_upload](https://raw.githubusercontent.com/Marlboro62/Torque-Lite-Pro/main/docs/images/Torque/15_Select_PIDs_to_upload.png)

**Example endpoints**
- **Home Assistant webhook** (recommended):  
  `https://<HA_BASE>/api/webhook/<YOUR_WEBHOOK_ID>`  
- **Custom backend**: any HTTPS endpoint that can handle Torque’s querystring format.

> Note: Torque uses **HTTP GET** with sensor values as URL parameters. If your server expects POST/headers, use a small relay script or reverse‑proxy to adapt the request.

### 16) Test your upload
Use **Test web logging** in Torque, then check your server for a `200 OK`/incoming data.  
![Step 16 – Verify_upload_Test_Web_Logging](https://raw.githubusercontent.com/Marlboro62/Torque-Lite-Pro/main/docs/images/Torque/16_Verify_upload_Test_Web_Logging.png)

---

## Troubleshooting

- **Adapter connects but ECU won’t**  
  - Start the engine or switch ignition to ON.  
  - Try disabling *ELM327 auto‑timing* or enabling *Alternate connection*.  
- **No data / very slow**  
  - Uncheck experimental options; use a quality adapter.  
  - Reduce the number of live gauges to increase polling speed.  
- **Web upload not received**  
  - Verify the exact URL (HTTPS, no trailing spaces).  
  - Use the **Test web logging** button and inspect your server logs.  
  - Some carriers block non‑HTTPS traffic—prefer HTTPS.  
- **Battery drain**  
  - Set *Upload only when connected* and close the app when not in use.

---

## File naming for screenshots

Place your 16 screenshots in:  
`docs/images/Torque/`

Expected names (you can change them, but then update the links):
```
01_Launch_Torque_and_grant_permissions.png
02_Pair_Bluetooth_OBD2_adapter_in_Android.png
03_Open_Torque_Settings.png
04_OBD2_Adapter_Settings.png
05_Select_connection_type_Bluetooth.png
06_Choose_your_paired_adapter.png
07_Recommended_adapter_options.png
08_Create_Vehicle_Profile.png
09_Fill_profile_details_and_assign_adapter.png
10_Check_connection_status.png
11_Add_dashboard_gauges_optional.png
12_Open_Data_Logging_and_Upload.png
13_Enable_Upload_to_Web_Server_and_set_URL.png
14_Choose_upload_conditions_only_when_connected.png
15_Select_PIDs_to_upload.png
16_Verify_upload_Test_Web_Logging.png
```

If your repo layout differs, change the RAW link prefix at the top of this file.

---

### License

Free to use in your repo. Replace the screenshots and tweak steps to match your setup.
