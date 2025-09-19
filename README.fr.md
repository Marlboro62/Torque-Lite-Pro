![HA Torque](https://raw.githubusercontent.com/Marlboro62/Torque-Lite-Pro/main/docs/images/logo.png)

[![Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/nothing_one)

# Torque Pro — Intégration Home Assistant 🇫🇷

> **Push temps réel** des données **OBD-II** depuis l’app Android **Torque Pro** vers **Home Assistant**.  
> Crée dynamiquement des capteurs, un *device tracker* GPS par véhicule, conserve les **unités métriques natives**, localise les libellés (EN/FR) et expose un **endpoint HTTP**.

*[English version]* : see [readme.md](./readme.md)

![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Custom%20Component-03a9f4)
![HACS](https://img.shields.io/badge/HACS-Custom-blue.svg)
![Status](https://img.shields.io/badge/iot__class-local__push-brightgreen)
![Version](https://img.shields.io/badge/version-2025.09.3.2-informational)

---

## 🔌 Matériel requis

- **OBD-II Bluetooth (ELM327)**
- Amazon : [OBD2 Bluetooth](https://amzn.to/48bHmPj) *(lien affilié — merci !)*

---

## ✨ Fonctionnalités

- **Récepteur HTTP local** sur **`/api/torque_pro`** (GET/POST/HEAD).  
  Authentification Home Assistant **requise par défaut** (recommandé).
- **Création dynamique d’entités** :
  - *Sensors* pour les PIDs connus (avec **device_class**/**state_class** déduites quand pertinent).
  - **Device tracker GPS par véhicule** (lat/lon/alt/précision/vitesse GPS).
- **Hygiène & robustesse des données** : filtrage NaN/Inf, bornes GPS validées, arrondi **s→min** pour les temps de trajet, synthèse **L/100 ↔ KPL/MPG** quand un seul côté est présent.
- **Langue & libellés** : EN/FR avec repli automatique.
- **IDs stables** : pas de fusion accidentelle entre véhicules/profils.
- **Diagnostics** : détaillés, champs sensibles masqués.

> Domaine : `torque_pro` — Classe IoT : `local_push` — Dépendance : `http`

---

## 📦 Installation

### Via HACS (recommandé)
1. **HACS → Integrations →** ••• **→ Custom repositories** → ajoutez ce dépôt.
2. Recherchez **Torque Pro** et installez.
3. Redémarrez Home Assistant si demandé.

### Installation manuelle
1. Copiez `custom_components/torque_pro/` dans `config/custom_components/`.
2. Redémarrez Home Assistant.

---

## ⚙️ Configuration (UI)

1. **Settings → Devices & Services → Add Integration → “Torque Pro”.**
2. Renseignez :
   - **Email (obligatoire)** : utilisé pour **router** les envois (`eml=<votre email>`).
   - **Langue** : `en` ou `fr` (libellés des capteurs).
   - **Préférences mémoire** : TTL de session (60–86400 s), taille LRU (10–1000).

> Vous pouvez créer **plusieurs entrées** (ex. *Torque Pro Phone 1* / *Torque Pro Phone 2*) et router chaque téléphone via son **`eml=`**.

---

## 📱 Réglages de l’app “Torque Pro” (Android)

**Torque Pro → Settings → Data Logging & Upload → Web server URL**

- **URL** : `https://votre-domaine/api/torque_pro`
- **Méthode** : GET **ou** POST (les deux sont supportées)
- **Paramètres** (dans l’URL, après `?`) :
  - `session=${session}`  ← **obligatoire**
  - `eml=<email>`        ← doit **correspondre** à l’entrée HA qui doit recevoir les données
  - `profileName=${profile}` *(ou `vehicle=${profile}` / `name=${profile}`)*  ← **recommandé** (maintient la séparation par profil/voiture/personne)
  - `id=${vehicleId}`     *(optionnel, encouragé)*
  - `lang=en`             *(optionnel)*
  - **Secours GPS** *(si votre profil n’inclut pas les PIDs GPS)* :  
    `lat=${lat}&lon=${lon}&alt=${altitude}&acc=${gpsacc}`

> **Torque** ajoute **automatiquement** des paires `k<code>=<valeur>` pour les PIDs.  
> Ne **pas** ajouter `imperial=` : l’ingestion demeure **nativement métrique** (HA gère la conversion d’affichage).

### Exemples (multi-entrées)
- **Un téléphone** :  
  `https://XXXXXX.duckdns.org/api/torque_pro?eml=XXXXXXXXXX@gmail.com&lang=en&session=${session}&profileName=${profile}&id=${vehicleId}`
- **Deux téléphones** :  
  `https://XXXXXX.duckdns.org/api/torque_pro?eml=XXXXXXXXXX@gmail.com&lang=en&session=${session}&profileName=${profile}&id=${vehicleId}`

---

## ✅ Bonnes pratiques PIDs

Évitez de tout cocher dans Torque :

1. Trop de PIDs **ralentissent** les lectures ECU et **gonflent** les envois.
2. Vous créerez des **capteurs inutiles** (bruit).
3. Risque de **doublons** : l’intégration synthétise déjà **L/100 ↔ KPL/MPG** si un seul côté est présent.
4. De nombreux PIDs sont **non pris en charge** selon les ECUs (0/N.A.) — décochez-les.

---

## 🧩 Entités créées

- **Device** par véhicule (ID **déterministe**).
- **Sensors (`sensor.*`)** : créés *à la volée* (libellé EN/FR, unité, précision d’affichage suggérée).  
  Exemples : RPM, vitesses OBD/GPS, températures, MAF/MAP, pression barométrique, tension batterie, économie de carburant, etc.
- **Device tracker (`device_tracker.*`)** : lat/lon/alt/précision/vitesse GPS.

> Les lat/lon GPS alimentent le **device_tracker** et ne sont pas dupliqués en capteurs.

---

## 🔐 Sécurité (important)

Torque **ne peut pas** envoyer d’en-tête `Authorization`. Pour une exposition publique sécurisée :

- Utilisez un **reverse proxy** (Nginx/Traefik) qui **injecte** `Authorization: Bearer <token>`.
- Ou restreignez l’accès via **VPN** (WireGuard/Tailscale) / réseau local.
- **Évitez** d’exposer l’endpoint ouvert sur Internet.

> Par défaut, l’endpoint requiert l’auth HA. N’exposez jamais des tokens en clair.

---

## ⚙️ Comportement & options

- **Mémoire LRU/TTL** : sessions conservées avec TTL configurable (60–86400 s) et taille max (10–1000).
- **Disponibilité** : les entités restent disponibles tant que des données récentes existent (ou dernier état restauré / 0 pour certains compteurs).
- **Unités / affichage** :
  - **Ingestion métrique native** (pas de conversions destructives).
  - **Synthèse L/100 ↔ KPL/MPG** si un seul côté est présent.
  - **Arrondi s→min** pour le temps de trajet.
  - **Précision d’affichage suggérée** par unité (vitesse, pression, etc.).
- **ID stable par véhicule/profil** (évite la fusion inter-profils/téléphones) :
  - basé sur `slug(profileName)` + `id[:4]` + petit *salt* dérivé de l’email (si présent).
- **Multi-entrée** : `eml=` **route** vers l’entrée appropriée.

---

## 🛠️ Dépannage

- **“IGNORED / No matching route”** dans les logs → le paramètre `eml=` ne correspond **à aucune entrée configurée**.
- **404 Not Found** → aucune entrée active pour l’intégration (vue HTTP inactive).
- **Pas de données** → vérifiez `session=${session}` et la connectivité OBD/réseau.

### Logs de debug (optionnel)
```yaml
logger:
  logs:
    custom_components.torque_pro.api: debug
    custom_components.torque_pro.coordinator: debug
```
Vous verrez `Resolved profile → …` avec l’ID calculé.

---

## 📄 Licence

Cette distribution est régie par la **Written Authorization Required License (LAER-TPHA-1.0)** — *Usage permis :* **Torque Pro ↔ Home Assistant**.

**En bref** : usage **personnel, non commercial**. Tout autre usage nécessite une **autorisation écrite**.

### ✅ Autorisé sans approbation préalable
- Installer et utiliser **sur votre propre instance Home Assistant**, à des fins **non commerciales**.

### ❌ Interdit sans autorisation écrite
- Reproduction, forks ou travaux dérivés publiés,
- Modification, publication ou **distribution** du code/binaire,
- Intégration dans d’autres projets/produits,
- Hébergement, **SaaS**, marketplaces, images/packs,
- Tout usage **commercial** (direct ou indirect).

Voir [`LICENSE`](./LICENSE).  
Demander une autorisation : [ouvrir un ticket “License request”](../../issues/new?assignees=&labels=license%2Clegal&template=license_request.yml&title=License%20request%3A%20).

> *“Torque”, “Torque Lite” et “Torque Pro” sont des marques de leurs propriétaires respectifs.*

---

## 🙌 Remerciements

- Application **Torque Pro** (Android — OBD-II)
- Communauté **Home Assistant**

---

## ☕ Soutenir

Si ce projet vous plaît, vous pouvez me soutenir ici :  
[![Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/nothing_one)

---

## 📄 Journal des changements (extrait)

- **2025.09.3** — Versionnage du manifeste, nettoyage de robustesse API/coordinator, i18n FR, diagnostics renforcés.  
- **2025.09.3.1** — Routage multi-entrées par email, ingestion métrique native (annotation des préférences d’unité), préservation des *unique_id* hérités, vue HTTP persistante (inactive 404), correction du parsing de version d’app.  
- **2025.09.3.2** — ID de profil véhicule déterministe (slug(profileName)+id[:4]+email-salt) pour éviter la fusion inter-appareils ; temps de trajet arrondis (s→min) et précision GPS négative ignorée ; normalisation/mémoire du nom de profil améliorée ; diagnostics enrichis (profile.Id, unit_preference, version de l’app) ; refonte de la plateforme capteurs : *unique_id* stables + migration, précision suggérée & classes device/state, valeur par défaut zéro pour compteurs trajet/distance/temps, filtrage des non-finis, mapping d’icônes amélioré.
