"""
job.py — Exécution ponctuelle pour cron / GitHub Actions (sans serveur web).

Lance UNE action puis quitte (ne démarre ni l'API ni le scheduler) :
    python -m backend.job scan      # scrape + score + alertes Discord
    python -m backend.job rapport   # rapport quotidien Discord (20h)
    python -m backend.job verif      # vérifie les annonces actives (rotation 24h)

Utilisé pour héberger les alertes 24/7 gratuitement (ex : GitHub Actions),
même quand le PC est éteint. La base SQLite est « checkpointée » avant la sortie
pour pouvoir être committée proprement entre deux exécutions.
"""

import asyncio
import sys

from backend.database.db import checkpoint, init_db
from backend.logger import log
from backend.scraper.runner import (
    generer_rapport_quotidien,
    scan_complet,
    verifier_annonces_actives,
)


async def main(action: str) -> None:
    """Exécute l'action demandée puis termine."""
    await init_db()
    if action == "scan":
        await scan_complet()
    elif action == "rapport":
        await generer_rapport_quotidien()
    elif action == "verif":
        await verifier_annonces_actives()
    else:
        print("Usage : python -m backend.job [scan|rapport|verif]")
        return
    await checkpoint()
    log.info(f"Job '{action}' terminé.")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "scan"))
