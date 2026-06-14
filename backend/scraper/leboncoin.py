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
import json
import random
import re

import httpx

from backend.config import settings
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


def _ads_depuis_next_data(html: str) -> list[dict]:
    """Extrait les annonces du JSON __NEXT_DATA__ d'une page de recherche LBC."""
    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S
    )
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []
    resultats, vus = [], set()

    def parcourir(obj):
        """Parcourt récursivement le JSON pour trouver les annonces (list_id + subject)."""
        if isinstance(obj, dict):
            if "list_id" in obj and "subject" in obj:
                norm = _normaliser(obj)
                if norm and norm["plateforme_id"] not in vus:
                    vus.add(norm["plateforme_id"])
                    resultats.append(norm)
            for v in obj.values():
                parcourir(v)
        elif isinstance(obj, list):
            for v in obj:
                parcourir(v)

    parcourir(data)
    return resultats


async def _scraper_via_api() -> list[dict]:
    """
    Récupère LBC via une API anti-bot (ScraperAPI) qui passe DataDome.
    Activé seulement si LBC_SCRAPER_API_KEY est renseignée. Sans ban.
    """
    cle = settings.LBC_SCRAPER_API_KEY
    cible = "https://www.leboncoin.fr/recherche?category=17&text=iphone&sort=time"
    params = {"api_key": cle, "url": cible, "render": "true", "country_code": "fr"}
    try:
        async with httpx.AsyncClient(timeout=75) as client:
            rep = await client.get("https://api.scraperapi.com/", params=params)
        if rep.status_code == 200:
            ads = _ads_depuis_next_data(rep.text)
            log.info(f"Leboncoin (API anti-bot) : {len(ads)} annonces collectées.")
            return ads
        log.warning(f"Leboncoin API anti-bot HTTP {rep.status_code}.")
    except httpx.HTTPError as exc:
        log.error(f"Leboncoin API anti-bot en échec : {exc}")
    return []


async def scraper(pages: int = 2) -> list[dict]:
    """
    Scrape les annonces iPhone récentes sur Leboncoin.
    - Si une clé API anti-bot est configurée : on l'utilise (passe DataDome, sans ban).
    - Sinon : tentative anonyme (souvent bloquée par DataDome → cooldown).
    Retourne une liste d'annonces normalisées (vide si bloqué ou en cooldown).
    """
    # Voie payante anti-bot : la seule fiable pour LBC (active si clé fournie).
    if settings.LBC_SCRAPER_API_KEY:
        return await _scraper_via_api()

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
