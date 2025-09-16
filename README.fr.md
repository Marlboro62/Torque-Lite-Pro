# Torque Pro — Intégration Home Assistant 🇫🇷

« Projet non affilié à l’application “Torque Lite / Pro”. »

> **Push temps réel des données OBD-II depuis l’app Android Torque Pro vers Home Assistant.**  
> Crée dynamiquement les capteurs, un *device tracker* GPS par véhicule, normalise les unités (métrique/impérial), traduit les libellés (FR/EN) et expose un endpoint HTTP sécurisé.

*[English version]*: see **README.md**  
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Custom%20Component-03a9f4)
![HACS](https://img.shields.io/badge/HACS-Custom-blue.svg)
![Status](https://img.shields.io/badge/iot__class-local__push-brightgreen)
![Version](https://img.shields.io/badge/version-2025.09.3-informational)

---

## ✨ Fonctionnalités

- **Réception HTTP locale** sur `/api/torque_pro` (GET/POST/HEAD). Authentification Home Assistant requise par défaut (**recommandé**).
- **Création dynamique** des entités :
  - *Sensors* pour les PIDs OBD-II connus (avec *device_class* / *state_class* inférés quand c’est pertinent).
  - **Device tracker GPS** par véhicule (latitude, longitude, précision, altitude, vitesse GPS).
- **Normalisation & robustesse** : filtrage systématique des `NaN/Inf`, nettoyage des unités et des valeurs.
- **Unités & langue** : métrique/impérial au choix, libellés FR/EN (fallback automatique si un libellé n’est pas connu).
- **Compat rétro** : schéma d’`unique_id` identique aux versions précédentes pour éviter toute migration.
- **Diagnostics durcis** : les champs sensibles (email, tokens, VIN, coordonnées, etc.) sont masqués dans le rapport.

> Domaine : `torque_pro` — Type : `service` — IoT class : `local_push` — Dépendances : `http` — Requirements : `pint>=0.24`

---

## 📦 Installation

### Via HACS (recommandé)
1. **HACS → Intégrations →** ••• **→ Dépôts personnalisés** → ajoutez le dépôt contenant ce composant.
2. Recherchez **Torque Pro** puis installez.
3. Redémarrez Home Assistant si demandé.

### Installation manuelle
1. Copiez le dossier `custom_components/torque_pro/` dans votre répertoire `config/custom_components/` de Home Assistant.
2. Redémarrez Home Assistant.

---

## ⚙️ Configuration (UI)

1. **Paramètres → Intégrations → Ajouter une intégration → “Torque Pro”.**
2. Renseignez :
   - **E‑mail** (obligatoire) : sert de filtre côté API (les uploads doivent inclure `eml=<votre email>`).
   - **Unités** : métrique ou impérial (conversion automatique).
   - **Langue** : `fr` ou `en` pour les libellés des capteurs.
3. Ouvrez **Options** pour affiner :
   - **TTL des sessions en mémoire** (plage **60–86400 s**).
   - **Taille max du cache** (plage **10–1000** sessions).

> Aucun YAML requis. Tout se fait depuis l’UI.

---

## 🔐 Authentification & sécurité

L’endpoint **exige par défaut l’authentification Home Assistant** (`Authorization: Bearer <TOKEN>`). L’app Torque Pro **ne sait pas ajouter un header HTTP personnalisé** : il faut donc l’un des montages ci‑dessous.

### Option A — Reverse proxy (conseillée)
Faites transiter les uploads via un proxy qui **injecte** le header `Authorization`. Exemple **Nginx** :

```nginx
# remplacez <HA_HOST:PORT> et <YOUR_LONG_LIVED_TOKEN>
location /api/torque_pro {
    proxy_pass http://<HA_HOST:PORT>/api/torque_pro;
    proxy_set_header Authorization "Bearer <YOUR_LONG_LIVED_TOKEN>";
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header Host $host;
    # (facultatif) limitez par IP/firewall si possible
}
```

Exemple **Caddy** :

```caddyfile
:443 {
  reverse_proxy <HA_HOST:PORT> {
    header_up Authorization "Bearer <YOUR_LONG_LIVED_TOKEN>"
  }
}
```

### Option B — (Non recommandé) Désactiver l’auth côté vue
Dans `api.py`, la vue définit :

```python
requires_auth = True  # set to False only if your app cannot send token
```

Passer à `False` **expose** publiquement l’endpoint si votre instance est accessible d’Internet. À éviter sauf réseau local cloisonné.

---

## 📱 Réglages “Torque Pro” (Android)

Dans l’app **Torque Pro** :  
**Settings → Data Logging & Upload → Web server URL**

- **URL** : l’URL publique de votre proxy ou de Home Assistant, p.ex.  
  `https://exemple.fr/api/torque_pro`
- **Méthode** : GET ou POST (les deux sont supportés).
- **Paramètres envoyés** : Torque ajoute automatiquement les paires `k<code>=<valeur>` pour les PIDs.  
  **Ajoutez** aussi :
  - `session` : un identifiant de session (ex. `${session}`).
  - `eml` : votre e‑mail (doit **correspondre** à la configuration HA si le filtre est actif).
  - (facultatif) `id` (vehicle id), `vehicle`/`profileName` (nom profil), `vin`, `lang`, `imperial`.
  - (fallback GPS) `lat`, `lon`, `alt`, `acc` si votre profil n’envoie pas les PIDs GPS.

> L’intégration tolère de nombreuses variantes de clés envoyées par Torque et nettoie automatiquement les valeurs.

---

## 🧪 Test rapide (sans Torque)

```bash
curl -X POST "https://<votre_domaine>/api/torque_pro"   -H "Authorization: Bearer <YOUR_LONG_LIVED_TOKEN>"   -d "session=test-123"   -d "eml=vous@example.com"   -d "id=veh-001"   -d "vehicle=Ma Voiture"   -d "k0d=88.0" \            # Speed (OBD)
  -d "kff1006=48.8566" \     # GPS Lat
  -d "kff1005=2.3522" \      # GPS Lon
  -d "kff1010=35" \          # GPS Altitude (m)
  -d "kff1239=6.5"           # GPS Accuracy (m)
```

Si tout est OK, vous verrez apparaître un **device** pour le véhicule et les entités correspondantes (capteurs + `device_tracker`).

---

## 🧩 Entités créées

- **Device** par véhicule (identifiant stable).
- **Sensors** : créés *à la volée* pour chaque PID “créable” détecté (libellé FR/EN, unité, précision d’affichage).  
  Quelques exemples fréquents : RPM, vitesse OBD/GPS, température LDR, MAF, MAP, pression baro, tension batterie, consommation, etc.
- **Device tracker** : latitude/longitude/accuracy/altitude/vitesse GPS + `gps_time` si présent.

> Les capteurs purement GPS (lat/lon) **ne** sont pas dupliqués en sensors : ils nourrissent le *device tracker*.

---

## 🧰 Options & comportement

- **TTL & cache mémoire** : les sessions reçues sont conservées en LRU avec un TTL configurable (plage **60–86400 s**) et une taille max (**10–1000**).  
- **Disponibilité** : les entités restent disponibles tant que le coordinateur conserve des données récentes.  
- **Unités** : conversions automatiques (km/h ↔ mph, kPa/bar ↔ psi, m ↔ ft, °C ↔ °F, etc.).  
- **Langue** : traduction des libellés en FR si connue, sinon fallback anglais.

---

## 🛠️ Dépannage

- **Aucune donnée** : vérifiez le **token** ou le proxy (Option A), et que Torque envoie `session` **et** `eml` (si configuré).  
- **Entités manquantes** : certains PIDs sans unité ne sont pas créés par défaut (hors capteurs textuels du type `...status/state/mode`).  
- **Coordonnées incorrectes** : l’intégration valide les bornes lat/lon. Assurez-vous que Torque envoie soit les PIDs GPS (`ff1005/ff1006/ff1010/ff1239`), soit les paramètres `lat/lon/alt/acc`.

Générez un **rapport de diagnostics** depuis l’UI de Home Assistant (les infos sensibles seront masquées).

---

## 🧾 Licence

Cette distribution est placée sous la **Licence d’Autorisation Écrite Requise — Usage autorisé : Torque Pro ↔ Home Assistant (LAER‑TPHA‑1.0)**.

- **Autorisé sans accord préalable** : utiliser ce composant **uniquement** pour connecter l’app Android *Torque Pro* à **Home Assistant** sur votre propre instance, à des fins **non commerciales**.
- **Tout le reste est interdit sans accord écrit** : reproduction, fork, modification, publication, distribution, intégration dans d’autres projets, hébergement/SaaS, et tout **usage commercial**.

👉 Lisez le fichier [`LICENSE`](./LICENSE) pour le texte complet.  
Pour obtenir une **autorisation écrite** (p.ex. commerciale, redistribution, intégration), contactez : `<ContactEmail>`.

---

## 🙌 Remerciements

- App **Torque Pro** (OBD-II) — Android
- Communauté Home Assistant

---

## 📄 Changelog (extrait)

- **2025.09.3** — Version manifest, nettoyage robustesse API/coordonnées, i18n FR, diagnostics renforcés.
