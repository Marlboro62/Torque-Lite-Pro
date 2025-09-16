# Create & Use a Long‑Lived Access Token in Home Assistant

A **Long‑Lived Access Token (LLAT)** is an API access token tied to your Home Assistant user account, valid for several years (up to ~10 years). It lets you call the REST or WebSocket API **without** interactive login each time.

> 🔐 Treat your token like a password. If it leaks, revoke it immediately.

---

## Table of contents
- [Prerequisites](#prerequisites)
- [Create a token (UI)](#create-a-token-ui)
- [Rotate / revoke a token](#rotate--revoke-a-token)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)

---

## Prerequisites

- Access to your Home Assistant instance (e.g. `http://homeassistant.local:8123`).
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
