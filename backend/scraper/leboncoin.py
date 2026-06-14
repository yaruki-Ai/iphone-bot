"""
leboncoin.py — Scraper Leboncoin via l'API interne (api.leboncoin.fr).

Stratégie + roues de secours :
  - Appel anonyme de l'API de recherche (pas de compte => identité protégée).
  - User-Agents tournants + en-têtes réalistes + délais aléatoires (anti-signature).
  - DataDome peut renvoyer 403 : on met alors la source en COOLDOWN (pause) pour
    ne pas insister et risquer un bannissement IP, et on dégrade proprement.
  - Si la source est bloquée, le scan continue avec Vinted/eBay + la simulation.

Aucune donnée n'est inventée : si l'API est bloquée, la fonction renvoie [].
"""

import asyncio
import random

import httpx

from backend.logger import log
from backend.scraper import antiban
from backend.scraper.parser import analyser_texte

_API_URL = "https://api.leboncoin.fr/finder/search"
_SOURCE = "leboncoin"


def _entetes() -> dict:
    """En-têtes pour l'API LBC (UA tournant + en-têtes spécifiques)."""
    h = antiban.entetes(referer="https://www.leboncoin.fr/recherche?text=iphone")
    h["Content-Type"] = "application/json"
    h["Origin"] = "https://www.leboncoin.fr"
    return h


def _corps_recherche(page: int, par_page: int = 35) -> dict:
    """Construit le corps JSON de la requête de recherche (catégorie téléphonie)."""
    return {
        "filters": {
            "category": {"id": "17"},          # 17 = Téléphonie
            "enums": {"ad_type": ["offer"]},
            "keywords": {"text": "iphone"},
            "location": {},
        },
        "limit": par_page,
        "limit_alu": 0,
        "offset": (page - 1) * par_page,
        "sort_by": "time",
        "sort_order": "desc",
    }


def _normaliser(ad: dict) -> dict | None:
    """Convertit une annonce brute LBC en dict normalisé pour la base."""
    try:
        titre = ad.get("subject", "")
        body = ad.get("body", "")
        prix = None
        if isinstance(ad.get("price"), list) and ad["price"]:
            prix = float(ad["price"][0])
        elif isinstance(ad.get("price"), (int, float)):
            prix = float(ad["price"])
        loc = ad.get("location", {}) or {}
        if prix is None or prix < 10:
            return None  # prix absent ou implausible
        analyse = analyser_texte(titre, body)
        if not analyse["modele"]:
            return None  # on ignore ce qui n'est pas un iPhone identifiable
        return {
            "plateforme": "leboncoin",
            "plateforme_id": str(ad.get("list_id")),
            "url": ad.get("url"),
            "titre": titre,
            "modele": analyse["modele"],
            "stockage": analyse["stockage"],
            "couleur": None,
            "etat": analyse["etat"],
            "panne": analyse["panne"],
            "prix": prix,
            "ville": loc.get("city"),
            "code_postal": loc.get("zipcode"),
            "description": body,
            "date_publication": ad.get("index_date") or ad.get("first_publication_date"),
            "icloud_detecte": analyse["icloud_detecte"],
            "batterie_pct": analyse["batterie_pct"],
        }
    except (KeyError, ValueError, TypeError) as exc:
        log.debug(f"Annonce LBC ignorée (parsing) : {exc}")
        return None


async def scraper(pages: int = 2) -> list[dict]:
    """
    Scrape les annonces iPhone récentes sur Leboncoin (API interne, anonyme).
    Retourne une liste d'annonces normalisées (vide si bloqué ou en cooldown).
    """
    if antiban.en_cooldown(_SOURCE):
        log.info("Leboncoin en cooldown (récemment bloqué) — source ignorée ce scan.")
        return []

    resultats: list[dict] = []
    try:
        async with httpx.AsyncClient(timeout=20, headers=_entetes()) as client:
            for page in range(1, pages + 1):
                bloque = False
                for tentative in range(1, 3):  # 2 tentatives par page
                    try:
                        rep = await client.post(_API_URL, json=_corps_recherche(page))
                        if rep.status_code == 200:
                            ads = rep.json().get("ads", []) or []
                            for ad in ads:
                                norm = _normaliser(ad)
                                if norm:
                                    resultats.append(norm)
                            break
                        if rep.status_code in (401, 403, 429):
                            log.warning(
                                f"Leboncoin bloqué (HTTP {rep.status_code}) — "
                                f"mise en cooldown 20 min, dégradation propre."
                            )
                            antiban.declencher_cooldown(_SOURCE, 20)
                            bloque = True
                            break
                        log.warning(f"Leboncoin HTTP {rep.status_code} page {page}.")
                    except httpx.HTTPError as exc:
                        log.warning(f"Erreur réseau LBC (tentative {tentative}) : {exc}")
                        await asyncio.sleep(1.5 * tentative)
                if bloque:
                    return resultats
                # Délai aléatoire anti-ban entre les pages.
                await asyncio.sleep(random.uniform(3, 7))
        if resultats:
            antiban.reinitialiser(_SOURCE)  # succès : on lève tout cooldown résiduel
    except Exception as exc:  # filet de sécurité global
        log.error(f"Scraper Leboncoin en échec : {exc}")
    log.info(f"Leboncoin : {len(resultats)} annonces iPhone collectées.")
    return resultats
