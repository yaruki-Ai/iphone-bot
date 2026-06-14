"""
runner.py — Orchestration d'un scan complet.

Enchaîne : collecte (LBC + Vinted + eBay, en parallèle) -> complément simulation
si besoin -> enregistrement en base -> recalcul des stats marché -> recalcul des
scores -> envoi des alertes Discord/Telegram des nouvelles opportunités.
Fournit aussi la vérification 24h et la génération du rapport quotidien.
"""

import asyncio

from backend.analysis import market, opportunity
from backend.config import settings
from backend.database.db import fetch_all
from backend.logger import log
from backend.notifier import discord
from backend.repository import marquer_disparues, purger_anciennes, upsert_plusieurs
from backend.scraper import ebay, leboncoin, simulator, vinted


async def scan_complet() -> dict:
    """Exécute un cycle de scan complet et retourne un résumé chiffré."""
    log.info("=== Début du scan ===")
    annonces: list[dict] = []

    # Collecte live des trois sources en parallèle (chacune dégrade proprement).
    resultats = await asyncio.gather(
        leboncoin.scraper(), vinted.scraper(), ebay.scraper(),
        return_exceptions=True,
    )
    for source, res in zip(("leboncoin", "vinted", "ebay"), resultats):
        if isinstance(res, Exception):
            log.error(f"Source {source} en exception : {res}")
        elif res:
            annonces.extend(res)

    nb_live = len(annonces)

    # Complément simulation si activé et collecte live insuffisante (démo / dev).
    if settings.SIMULATION_MODE and nb_live < 10:
        simulees = await simulator.generer_scan(12)
        annonces.extend(simulees)
        log.info(f"Mode simulation : {len(simulees)} annonces de démonstration ajoutées.")

    # Enregistrement (dédoublonné) puis analyses.
    nb_enregistrees = await upsert_plusieurs(annonces)
    await market.recalculer_tout()
    opportunites = await opportunity.recalculer_scores()

    # Alertes immédiates : seulement si explicitement activées (sinon récap 20h).
    nb_alertes = 0
    if settings.ALERTES_IMMEDIATES:
        for opp in opportunites:
            if await discord.alerter_opportunite(opp):
                nb_alertes += 1

    resume = {
        "collectees_live": nb_live,
        "enregistrees": nb_enregistrees,
        "opportunites": len(opportunites),
        "alertes_envoyees": nb_alertes,
    }
    log.info(f"=== Fin du scan === {resume}")
    return resume


async def verifier_annonces_actives() -> int:
    """Vérifie les annonces actives : celles disparues depuis >24h = vendues."""
    log.info("Vérification des annonces actives (rotation 24h)…")
    nb = await marquer_disparues(seuil_heures=24.0)
    # Nettoyage des annonces vendues trop anciennes (> 90 jours).
    await purger_anciennes(jours=90)
    # Les délais de vente ayant changé, on rafraîchit les stats marché.
    await market.recalculer_tout()
    return nb


async def _top_cassees(limite: int = 15) -> list[dict]:
    """Meilleures opportunités cassées RENTABLES du jour (ROI > 0), par score."""
    return await fetch_all(
        """SELECT * FROM annonces
           WHERE active = 1 AND etat = 'casse' AND score IS NOT NULL AND roi_estime > 0
           ORDER BY score DESC, roi_estime DESC LIMIT ?""",
        (limite,),
    )


async def _top_fonctionnels(limite: int = 5) -> list[dict]:
    """
    Top 'bonnes affaires' fonctionnelles : prix le plus bas par rapport au
    prix médian du modèle (jointure avec marche_stats).
    """
    return await fetch_all(
        """SELECT a.*, m.prix_median,
                  (a.prix * 1.0 / NULLIF(m.prix_median, 0)) AS ratio
           FROM annonces a
           JOIN marche_stats m ON a.modele = m.modele
                AND (a.stockage = m.stockage OR (a.stockage IS NULL AND m.stockage IS NULL))
           WHERE a.active = 1 AND a.etat = 'fonctionnel' AND a.prix > 0
                 AND m.prix_median IS NOT NULL
           ORDER BY ratio ASC LIMIT ?""",
        (limite,),
    )


async def generer_rapport_quotidien() -> bool:
    """Construit et envoie le rapport Discord du soir (top 5 + top 5)."""
    log.info("Génération du rapport quotidien…")
    top_cassees = await _top_cassees(settings.RAPPORT_TOP_N)
    top_fonct = await _top_fonctionnels(5)
    return await discord.envoyer_rapport(top_cassees, top_fonct)
