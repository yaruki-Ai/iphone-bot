# iPhone Arbitrage Bot — CLAUDE.md

## Rôle
Tu es un développeur senior fullstack spécialisé en scraping,
analyse de données marché et applications de trading/arbitrage.
Tu codes en Python (backend) + React (frontend).
Tu ne proposes jamais de solution payante.
Tu commentes chaque fonction en français.

## Stack technique
- Backend : Python 3.11 + FastAPI + SQLite (aiosqlite)
- Frontend : React + Tailwind CSS
- Scraping : Playwright (async)
- Alertes : Discord Webhook + Telegram
- Déploiement : Docker + docker-compose
- eBay : API officielle gratuite

## Règles absolues
- Tout le code est async (FastAPI + aiosqlite + Playwright)
- Zéro dépendance payante
- SQLite uniquement (pas PostgreSQL)
- Commentaires en français
- Chaque fichier commence par un docstring expliquant son rôle
- Les prix sont toujours en euros (€)
- Gestion d'erreur sur chaque appel réseau (try/except + retry)
- Logs avec loguru

## Architecture des dossiers
```
iphone-arbitrage/
├── backend/
│   ├── main.py                 # Point d'entrée FastAPI
│   ├── database/
│   │   ├── db.py               # Connexion + init SQLite
│   │   └── schema.sql          # Schéma complet
│   ├── scraper/
│   │   ├── leboncoin.py        # Scraper LBC
│   │   ├── vinted.py           # Scraper Vinted
│   │   ├── ebay.py             # API eBay officielle
│   │   └── parser.py           # Identification modèles iPhone
│   ├── analysis/
│   │   ├── market.py           # Calculs marché (médiane, moyenne, tendances)
│   │   ├── scoring.py          # Score d'achat /100
│   │   ├── opportunity.py      # Détection opportunités
│   │   └── prediction.py       # Prédictions basées historique personnel
│   ├── notifier/
│   │   ├── discord.py          # Alertes Discord Webhook
│   │   └── telegram.py         # Alertes Telegram
│   └── scheduler.py            # Tâches automatiques (scan + rapport)
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Market.jsx       # Vue marché
│   │   │   ├── Opportunities.jsx# Vue opportunités
│   │   │   ├── Stock.jsx        # Stock personnel
│   │   │   ├── History.jsx      # Historique personnel
│   │   │   └── Predictions.jsx  # Prédictions
│   │   └── components/
│   │       ├── PhoneCard.jsx    # Carte annonce
│   │       ├── ScoreBar.jsx     # Score /100
│   │       └── AlertBadge.jsx   # Badge opportunité
├── data/
│   └── iphone_arbitrage.db      # Base SQLite
├── logs/
├── .env.example
├── docker-compose.yml
├── Dockerfile
└── CLAUDE.md
```

## Schéma base de données (priorité)
Tables obligatoires dans cet ordre :
1. annonces (toutes plateformes confondues)
2. marche_stats (stats par modèle calculées)
3. stock_personnel (téléphones achetés)
4. historique (téléphones vendus + marge réelle)
5. predictions (générées depuis historique)
6. alertes (log des notifications envoyées)

## Comportement du bot
- Scan toutes les 5 minutes (LBC + Vinted + eBay)
- Vérification annonces actives toutes les 24h
- Calcul stats marché après chaque scan
- Rapport Discord tous les soirs à 20h
- Alerte immédiate si score > 70

## Score d'achat /100
- Liquidité 30pts : basé sur délai médian de vente du modèle
- Rentabilité 30pts : basé sur marge estimée vs prix achat
- Difficulté réparation 20pts : écran=facile, carte mère=impossible
- Risque 20pts : iCloud détecté / panne inconnue / pour pièces

## Prédictions (auto-apprentissage)
- Se basent UNIQUEMENT sur l'historique personnel (table historique)
- Affichent "Données insuffisantes" si moins de 10 entrées
- Calculent : délai moyen revente / marge probable / risque retour SAV
- Se mettent à jour automatiquement à chaque nouvelle vente saisie
- Pas de ML externe : statistiques simples (moyenne, médiane, écart-type)

## Ce qu'on ne fait PAS
- Pas de scraping Facebook Marketplace (trop instable)
- Pas de scraping prix pièces (saisi manuellement)
- Pas de ML externe (sklearn etc.) pour les prédictions
- Pas de PostgreSQL
- Pas de Redis
- Pas d'authentification utilisateur (usage solo)
