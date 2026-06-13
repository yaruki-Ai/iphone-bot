"""
vinted.py — Scraper Vinted via l'API interne (www.vinted.fr/api/v2).

Scraping CLASSIQUE anonyme (aucun token : ils expirent trop souvent) :
  - On récupère les cookies de session en visitant la page d'accueil, puis on
    interroge l'API catalogue. Pas d'authentification.
Roues de secours :
  - User-Agents tournants + en-têtes réalistes + délais aléatoires.
  - En cas de blocage (403/429), mise en COOLDOWN de la source (pause) et
    dégradation propre (le scan continue avec les autres sources + simulation).
"""

import asyncio
import random

import httpx

from backend.logger import log
from backend.scraper import antiban
from backend.scraper.parser import analyser_texte

_BASE = "https://www.vinted.fr"
_API_ITEMS = f"{_BASE}/api/v2/catalog/items"
_SOURCE = "vinted"

# Requêtes de recherche : on couvre les annonces cassées ET fonctionnelles.
_RECHERCHES = ["iphone cassé écran", "iphone pour pièces", "iphone"]


def _entetes() -> dict:
    """En-têtes pour l'API Vinted (UA tournant + en-têtes spécifiques)."""
    h = antiban.entetes(referer=f"{_BASE}/catalog?search_text=iphone")
    h["X-Requested-With"] = "XMLHttpRequest"
    return h


def _normaliser(item: dict) -> dict | None:
    """Convertit un item brut Vinted en dict normalisé pour la base."""
    try:
        titre = item.get("title", "")
        prix = None
        bloc_prix = item.get("price")
        if isinstance(bloc_prix, dict):
            prix = float(bloc_prix.get("amount"))
        elif isinstance(bloc_prix, (int, float, str)):
            prix = float(bloc_prix)
        if prix is None or prix < 10:
            return None  # prix absent ou implausible (accessoire / erreur)
        analyse = analyser_texte(titre, item.get("description", ""))
        if not analyse["modele"]:
            return None
        url = item.get("url") or f"{_BASE}/items/{item.get('id')}"
        return {
            "plateforme": "vinted",
            "plateforme_id": str(item.get("id")),
            "url": url,
            "titre": titre,
            "modele": analyse["modele"],
            "stockage": analyse["stockage"],
            "couleur": None,
            "etat": analyse["etat"],
            "panne": analyse["panne"],
            "prix": prix,
            "ville": None,
            "code_postal": None,
            "description": item.get("description", ""),
            "date_publication": None,
            "icloud_detecte": analyse["icloud_detecte"],
        }
    except (KeyError, ValueError, TypeError) as exc:
        log.debug(f"Item Vinted ignoré (parsing) : {exc}")
        return None


async def scraper(pages: int = 2) -> list[dict]:
    """
    Scrape les annonces iPhone sur Vinted (API interne, anonyme).
    Retourne une liste d'annonces normalisées (vide si bloqué ou en cooldown).
    """
    if antiban.en_cooldown(_SOURCE):
        log.info("Vinted en cooldown (récemment bloqué) — source ignorée ce scan.")
        return []

    resultats: list[dict] = []
    vus: set[str] = set()

    try:
        async with httpx.AsyncClient(timeout=20, headers=_entetes(),
                                     follow_redirects=True) as client:
            # 1) Amorçage des cookies anonymes via la page d'accueil.
            try:
                await client.get(_BASE)
            except httpx.HTTPError as exc:
                log.warning(f"Vinted : amorçage cookies impossible : {exc}")

            # 2) Recherches successives.
            for recherche in _RECHERCHES:
                for page in range(1, pages + 1):
                    params = {
                        "search_text": recherche,
                        "per_page": "48",
                        "page": str(page),
                        "order": "newest_first",
                    }
                    try:
                        rep = await client.get(_API_ITEMS, params=params)
                        if rep.status_code == 200:
                            items = rep.json().get("items", []) or []
                            for it in items:
                                pid = str(it.get("id"))
                                if pid in vus:
                                    continue
                                norm = _normaliser(it)
                                if norm:
                                    vus.add(pid)
                                    resultats.append(norm)
                        elif rep.status_code in (401, 403, 429):
                            log.warning(
                                f"Vinted bloqué (HTTP {rep.status_code}) — "
                                f"mise en cooldown 20 min, dégradation propre."
                            )
                            antiban.declencher_cooldown(_SOURCE, 20)
                            return resultats
                        else:
                            log.warning(f"Vinted HTTP {rep.status_code} ({recherche} p{page}).")
                    except httpx.HTTPError as exc:
                        log.warning(f"Erreur réseau Vinted : {exc}")
                    await asyncio.sleep(random.uniform(2, 5))
        if resultats:
            antiban.reinitialiser(_SOURCE)
    except Exception as exc:
        log.error(f"Scraper Vinted en échec : {exc}")
    log.info(f"Vinted : {len(resultats)} annonces iPhone collectées.")
    return resultats
