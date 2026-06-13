"""
test_live.py — Test bout-en-bout en données RÉELLES (sans simulation).

Vérifie que tout est connecté : scrapers (LBC + Vinted + eBay) -> base ->
stats marché -> scoring -> Discord. Envoie UNE seule alerte (top opportunité)
pour prouver la connexion Discord sans inonder le salon.
    .venv\\Scripts\\python.exe -m tests.test_live
"""

import asyncio

from backend.analysis import market, opportunity
from backend.database.db import fetch_one, init_db
from backend.notifier import discord
from backend.repository import upsert_plusieurs
from backend.scraper import ebay, leboncoin, vinted


async def main() -> None:
    """Scénario de test live."""
    await init_db()

    print("\n--- Scraping live (sources connectées) ---")
    res = await asyncio.gather(
        leboncoin.scraper(pages=1), vinted.scraper(pages=1), ebay.scraper(pages=1),
        return_exceptions=True,
    )
    annonces = []
    for nom, r in zip(("leboncoin", "vinted", "ebay"), res):
        if isinstance(r, Exception):
            print(f"  {nom}: EXCEPTION {r}")
        else:
            print(f"  {nom}: {len(r)} annonces")
            annonces.extend(r)

    print(f"\nTotal collecté : {len(annonces)}")
    if not annonces:
        print("Aucune donnée live (sources bloquées). Le bot reste fonctionnel (cooldown).")
        return

    await upsert_plusieurs(annonces)
    await market.recalculer_tout()
    opps = await opportunity.recalculer_scores()

    total = await fetch_one("SELECT COUNT(*) AS n FROM annonces")
    cassees = await fetch_one("SELECT COUNT(*) AS n FROM annonces WHERE etat='casse'")
    print(f"\nEn base : {total['n']} annonces ({cassees['n']} cassées)")
    print(f"Opportunités (score >= seuil) : {len(opps)}")

    top = await opportunity.top_opportunites(limite=5)
    for o in top:
        print(f"  [{o['score']}/100] {o['modele']} {o['stockage']} {o['panne']} "
              f"-> {o['prix']}€ (ROI {o['roi_estime']}€)")

    # Preuve de connexion Discord : on envoie UNE alerte SI elle dépasse le seuil
    # (comportement de production, pour ne pas polluer le salon avec du sous-seuil).
    from backend.config import settings
    if top and top[0]["score"] >= settings.SEUIL_ALERTE_SCORE:
        envoye = await discord.alerter_opportunite(top[0])
        print(f"\nAlerte Discord (score {top[0]['score']}) envoyée : {envoye}")
    else:
        meilleur = top[0]["score"] if top else 0
        print(f"\nAucune opportunité >= {settings.SEUIL_ALERTE_SCORE} (meilleur score {meilleur}) — pas d'alerte (normal).")

    print("\n=== TEST LIVE OK ===")


if __name__ == "__main__":
    asyncio.run(main())
