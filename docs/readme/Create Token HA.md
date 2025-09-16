# Create & Use a Long‑Lived Access Token in Home Assistant

A **Long‑Lived Access Token (LLAT)** is an API access token tied to your Home Assistant user account, valid for several years (up to ~10 years). It lets you call the REST or WebSocket API **without** interactive login each time.

> 🔐 Treat your token like a password. If it leaks, revoke it immediately.

---

## Table of contents
- [Prerequisites](#prerequisites)
- [Create a token (UI)](#create-a-token-ui)
- [Store the token safely](#store-the-token-safely)
- [Use the token (REST examples)](#use-the-token-rest-examples)
- [Use the token (WebSocket example)](#use-the-token-websocket-example)
- [Rotate / revoke a token](#rotate--revoke-a-token)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)

---

## Prerequisites

- Access to your Home Assistant instance (e.g. `https://homeassistant.local:8123`).
- A Home Assistant user account with the necessary permissions *(a token inherits the same permissions as its user)*.
- A password manager or another safe place to store the token.

---

## Create a token (UI)

1. **Open your profile**  
   In Home Assistant, click your user name at the bottom‑left of the sidebar.

2. **Go to the “Security” tab** → **Long‑Lived Access Tokens**. Click **Create Token**.

3. **Name the token** (e.g., `script_backup`, `bot_discord`, `grafana`) and confirm.

4. **Copy the token immediately** — it will not be shown again.

5. *(Optional)* **Generate a QR code** to transfer the token to another device.


### Screenshots

![Create Token / Security tab](https://raw.githubusercontent.com/Marlboro62/Torque-Lite-Pro/main/docs/images/Token/Create%20Token.png)
![Name the token](https://raw.githubusercontent.com/Marlboro62/Torque-Lite-Pro/main/docs/images/Token/Name%20Token.png)
![Copy the token](https://raw.githubusercontent.com/Marlboro62/Torque-Lite-Pro/main/docs/images/Token/Key%20Token.png)
![Optional QR code](https://raw.githubusercontent.com/Marlboro62/Torque-Lite-Pro/main/docs/images/Token/QRCode%20Key%20Token.png)

---

## Store the token safely

- Password manager (recommended).
- Environment variable (for dev/CI):
  ```bash
  export HA_BASE_URL="https://homeassistant.local:8123"
  export HA_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  ```
- Home Assistant `secrets.yaml` (for use *inside* HA).
- **Never** commit tokens to Git.

---

## Use the token (REST examples)

All REST calls must include:
```
Authorization: Bearer <YOUR_TOKEN>
Content-Type: application/json
```

### cURL
```bash
# Get all states
curl -sS -H "Authorization: Bearer $HA_TOKEN"      -H "Content-Type: application/json"      "$HA_BASE_URL/api/states" | jq .

# Turn a light on
curl -sS -X POST -H "Authorization: Bearer $HA_TOKEN"      -H "Content-Type: application/json"      -d '{"entity_id":"light.living_room"}'      "$HA_BASE_URL/api/services/light/turn_on"
```

### Python (requests)
```python
import os, requests
base = os.environ["HA_BASE_URL"]
token = os.environ["HA_TOKEN"]

headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Read an entity state
r = requests.get(f"{base}/api/states/sensor.outdoor_temperature", headers=headers)
print(r.json())

# Call a service
requests.post(
    f"{base}/api/services/switch/turn_off",
    headers=headers,
    json={"entity_id": "switch.coffee_machine"},
)
```

### Node.js (fetch)
```js
const base = process.env.HA_BASE_URL;
const token = process.env.HA_TOKEN;

const headers = {
  "Authorization": `Bearer ${token}`,
  "Content-Type": "application/json"
};

const states = await fetch(`${base}/api/states`, { headers }).then(r => r.json());
console.log(states.length, "states");
```

---

## Use the token (WebSocket example)

```js
// Minimal WebSocket auth flow
const base = process.env.HA_BASE_URL.replace(/^http/, "ws");
const token = process.env.HA_TOKEN;

const ws = new WebSocket(`${base}/api/websocket`);
ws.onmessage = (ev) => {
  const msg = JSON.parse(ev.data);
  if (msg.type === "auth_required") {
    ws.send(JSON.stringify({ type: "auth", access_token: token }));
  } else if (msg.type === "auth_ok") {
    console.log("Authenticated!");
    // Subscribe to state_changed events
    ws.send(JSON.stringify({ id: 1, type: "subscribe_events", event_type: "state_changed" }));
  } else {
    console.log(msg);
  }
};
```

---

## Rotate / revoke a token

- **Rotate**: create a new token, update your apps/services, then delete the old token.
- **Revoke**: Profile → **Security** → **Long‑Lived Access Tokens** → 🗑️ next to the token.

---

## Troubleshooting

- **401 Unauthorized**
  - Missing/incorrect `Authorization` header.
  - Token was revoked or expired.
  - URL points to the wrong HA instance.

- **403 Forbidden**
  - Your user doesn’t have permission for the action/service.

- **CORS errors in browser**
  - Prefer server‑side calls (backend, add‑ons, automations) or configure a proxy that handles CORS.

---

## FAQ

**How long do LLATs last?**  
Up to ~10 years from creation.

**Do tokens have scopes?**  
No. A token inherits the permissions of the user who created it.

**Can I see the token value later?**  
No. You can only copy it once at creation time. If you’ve lost it, create a new token.

**Is a QR code required?**  
No. It’s optional — just a convenience.

---

### License

You may copy/paste this README into your repository. Screenshots are yours to include under your repo’s license.
