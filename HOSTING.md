# Héberger le bot gratuitement 24/7 (alertes Discord même PC éteint)

Le dashboard se consulte en local (l'`.exe`). Mais pour recevoir les alertes
Discord en continu, il faut que le **scan tourne en permanence**. Voici la
solution gratuite recommandée, plus un plan B plus fiable.

---

## Solution recommandée : GitHub Actions (gratuit, sans carte bancaire)

GitHub exécute automatiquement le scan toutes les ~20 min et envoie les alertes
Discord, sans serveur ni PC allumé. Tout est déjà prêt dans le projet
(`.github/workflows/`). Étapes :

### 1. Créer un dépôt GitHub **public**
- Crée un compte sur https://github.com (gratuit).
- Nouveau dépôt → nom `iphone-bot` → **Public** (les minutes Actions sont
  illimitées en public ; aucun secret n'est dans le code, ils sont stockés à part).

### 2. Pousser le projet
Dans le dossier du projet (PowerShell) :
```bash
git init
git add .
git commit -m "Bot arbitrage iPhone"
git branch -M main
git remote add origin https://github.com/TON_PSEUDO/iphone-bot.git
git push -u origin main
```
> Le fichier `.env` (qui contient tes identifiants) est **ignoré par git** : il
> n'est jamais envoyé sur GitHub. C'est voulu.

### 3. Ajouter les secrets
Sur GitHub : **Settings → Secrets and variables → Actions → New repository secret**.
Crée ces 4 secrets (copie les valeurs depuis ton `.env`) :
- `DISCORD_WEBHOOK_ALERTES`
- `DISCORD_WEBHOOK_RAPPORT`
- `LBC_EMAIL`
- `LBC_PASSWORD`

### 4. Activer et tester
- Onglet **Actions** → active les workflows.
- Ouvre **« Scan iPhone (alertes Discord) »** → bouton **Run workflow**.
- Regarde les logs du run : tu dois voir « Vinted : N annonces », « eBay : N
  annonces ». Vérifie ton salon Discord.
- Si OK : il tourne ensuite **tout seul toutes les 20 min**, et le rapport part
  à 20h (heure d'été).

### ⚠️ Point à vérifier au 1er test
Depuis les serveurs GitHub (IP « datacenter »), Vinted/eBay peuvent bloquer plus
souvent que depuis ta connexion maison. Le 1er run nous dira si ça passe :
- **Si Vinted/eBay renvoient des annonces** → parfait, terminé.
- **S'ils renvoient 0 (bloqués)** → passe au plan B ci-dessous.

---

## Plan B (le plus fiable) : un petit appareil allumé chez toi

Un vieux PC, un mini-PC ou un Raspberry Pi laissé branché 24/7 utilise ton
**IP maison** → les scrapers ne se font jamais bloquer (le plus robuste).
- Le plus simple : copier le dossier `dist/` (avec l'`.exe` et le `.env`) sur
  l'appareil, et le mettre en **démarrage automatique** de Windows
  (touche Windows + R → `shell:startup` → y placer un raccourci vers l'`.exe`).
- Ou avec Docker (`docker compose up -d`) sur un Raspberry Pi / mini-PC.

L'appareil reste allumé, les alertes Discord arrivent en continu. Coût : ~rien
(électricité d'un petit appareil).

---

## Récapitulatif
| Besoin | Où |
|---|---|
| Dashboard (voir le marché, stock, prédictions) | `.exe` en local, quand tu veux |
| Alertes Discord 24/7 | GitHub Actions (gratuit) **ou** appareil allumé chez toi |
