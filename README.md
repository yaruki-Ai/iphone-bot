# 📱 iPhone Arbitrage Bot

Outil personnel d'arbitrage iPhone : surveille les annonces (Leboncoin, Vinted,
eBay), analyse le marché par modèle, calcule un **score d'achat /100**, détecte
les **opportunités**, suit votre **stock** et votre **historique**, et **prédit
vos marges** à partir de vos ventes réelles. Alertes **Discord** en temps réel.

> 100 % gratuit · SQLite · backend Python async · frontend React · livrable en
> **un seul `.exe`** que le client double-clique (aucune installation).

---

## 🚀 Démarrage rapide (client)

1. Récupérez le dossier `dist/` contenant **`iPhoneArbitrageBot.exe`** et le fichier **`.env`**.
2. Ouvrez `.env` et complétez vos clés (voir [Configuration](#-configuration)).
3. **Double-cliquez sur `iPhoneArbitrageBot.exe`.**
4. Le dashboard s'ouvre tout seul dans le navigateur sur `http://127.0.0.1:8000`.

Pour arrêter : fermez la fenêtre noire (console).
La base de données (`data/`) et les logs (`logs/`) se créent à côté de l'exe.

---

## 🛠️ Construire l'exe (développeur)

Prérequis : **Python 3.11+** et **Node.js 18+** installés.

```bat
BUILD_EXE.bat
```

Ce script crée l'environnement, installe les dépendances, build le frontend et
génère `dist\iPhoneArbitrageBot.exe`. 

Pour lancer **depuis les sources** (sans exe) : `START.bat`.

---

## ⚙️ Configuration

Tout se passe dans le fichier `.env` (modèle dans `.env.example`).

| Variable | Rôle | Obligatoire |
|---|---|---|
| `DISCORD_WEBHOOK_ALERTES` | Salon des alertes (score > 70) | Recommandé |
| `DISCORD_WEBHOOK_RAPPORT` | Salon du rapport du soir (20h) | Recommandé |
| `EBAY_APP_ID` / `EBAY_CERT_ID` | API officielle eBay (prix marché) | Optionnel |
| `LBC_EMAIL` / `LBC_PASSWORD` | Compte Leboncoin dédié | Optionnel |
| `VINTED_SESSION_COOKIE` | Cookie Vinted (sinon anonyme) | Optionnel |
| `SIMULATION_MODE` | `true` = remplit des données de démo | — |
| `SCAN_INTERVAL_MINUTES` | Fréquence de scan (défaut 12) | — |
| `SEUIL_ALERTE_SCORE` | Score déclenchant une alerte (défaut 70) | — |
| `MARGE_CIBLE_POURCENT` | Marge visée pour le prix max d'achat (défaut 30) | — |

Le bot **fonctionne même avec des champs vides** : chaque service indisponible
est ignoré proprement (dégradation gracieuse).

---

## 🧠 Fonctionnement

- **Scan automatique** toutes les ~12 min (LBC + Vinted + eBay).
- **Vérification** des annonces toutes les 24 h : une annonce disparue est
  considérée vendue → calcul du **temps de rotation**.
- **Stats marché** par modèle : prix min/moyen/médian/premium, délais de vente,
  volume cassés vs fonctionnels, évolution 7 j / 30 j, indice de liquidité.
- **Score d'achat /100** : Liquidité (30) + Rentabilité (30) + Réparation (20)
  + Risque (20). Alerte Discord immédiate si > seuil.
- **Prédictions** : moyenne / médiane / écart-type sur votre historique réel
  (≥ 10 ventes requises, sinon « Données insuffisantes »). Pas d'IA externe.

### Les 5 pages
1. **Marché** — modèles les plus liquides / rentables + tendances de prix.
2. **Opportunités** — annonces cassées scorées + prix max conseillé + ROI.
3. **Stock** — téléphones achetés / en réparation (ajout, vente, suppression).
4. **Historique** — ventes passées + marge réelle + totaux.
5. **Prédictions** — statistiques issues de votre historique.

---

## 🛡️ Précautions anti-bannissement

- Scrapers via les **API JSON internes** (httpx), pas de navigateur lourd.
- **Délais aléatoires** entre requêtes, **pages limitées**, **back-off** si blocage.
- **eBay** = API officielle (zéro risque). **Vinted** = anonyme. **Leboncoin** =
  anonyme (votre identité n'est jamais exposée).
- Si une source est bloquée (ex. DataDome sur Leboncoin), le bot **continue**
  avec les autres sources sans planter.

---

## 📁 Architecture

```
backend/   API FastAPI, scrapers, analyse, notifier, scheduler
frontend/  Dashboard React + Tailwind (buildé dans frontend/dist)
data/      Base SQLite (générée)
logs/      Journaux loguru (générés)
dist/      Exécutable final (après build)
```

---

## 🧪 Tests

```bat
.venv\Scripts\python.exe -m tests.smoke_test     REM logique backend (hors réseau)
.venv\Scripts\python.exe -m tests.test_discord   REM connexion des webhooks Discord
```

---

## ❓ Dépannage

- **Le navigateur ne s'ouvre pas** : allez manuellement sur `http://127.0.0.1:8000`.
- **Port 8000 occupé** : changez `APP_PORT` dans `.env`.
- **Pas d'annonces réelles** : Leboncoin peut être temporairement bloqué ;
  Vinted fonctionne en anonyme ; eBay nécessite les clés. Le `SIMULATION_MODE`
  garantit un dashboard rempli pour la démo.
- **Pas d'alertes Discord** : vérifiez les URL de webhook dans `.env`.
```
