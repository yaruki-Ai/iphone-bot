"""
ebay.py — Scraper eBay (scraping classique de eBay.fr, sans API).

L'API officielle eBay refuse les comptes neufs : on scrape donc la page de
résultats (https://www.ebay.fr/sch/i.html). Prix en €.

eBay renvoie 403 sur une requête minimaliste : on envoie un jeu d'en-têtes
navigateur complet et on visite d'abord la page d'accueil pour récupérer des
cookies. Le HTML utilise des cartes « s-card » (s-card__title / s-card__price).

Roues de secours : User-Agents tournants, cooldown automatique si blocage,
dégradation propre (retour [] sans planter le scan).
"""

import asyncio
import random
import re

import httpx
from bs4 import BeautifulSoup

from backend.logger import log
from backend.scraper import antiban
from backend.scraper.parser import analyser_texte

_SOURCE = "ebay"
_HOME = "https://www.ebay.fr/"
_URL = "https://www.ebay.fr/sch/i.html"


def _entetes() -> dict:
    """En-têtes navigateur complets (eBay 403 sinon). UA tournant via antiban."""
    return {
        "User-Agent": antiban.user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Connection": "keep-alive",
    }


def _prix_depuis_texte(txt: str) -> float | None:
    """Extrait un prix en euros (ex: '199,90 EUR', '15,00 à 30,00 €')."""
    if not txt:
        return None
    premier = re.split(r"\s+à\s+|\s+to\s+", txt)[0]
    premier = premier.replace("\xa0", " ").replace("EUR", "").replace("€", "")
    premier = premier.replace(" ", "").replace(",", ".")
    m = re.search(r"\d+(\.\d+)?", premier)
    return float(m.group(0)) if m else None


def _id_depuis_url(url: str) -> str | None:
    """Extrait l'identifiant d'article depuis l'URL eBay (/itm/123456...)."""
    if not url:
        return None
    m = re.search(r"/itm/(?:[^/]+/)?(\d{6,})", url)
    return m.group(1) if m else None


def _carte_depuis_titre(titre_el):
    """Remonte du titre vers la carte contenant prix + lien."""
    courant = titre_el
    for _ in range(6):
        courant = courant.parent
        if courant is None:
            return None
        if courant.select_one(".s-card__price") and courant.select_one('a[href*="/itm/"]'):
            return courant
    return None


def _normaliser(titre_el) -> dict | None:
    """Convertit une carte eBay (à partir de son titre) en dict normalisé."""
    try:
        titre = titre_el.get_text(" ", strip=True)
        if not titre or "Shop on eBay" in titre or "Annonce sponsorisée" == titre:
            return None
        carte = _carte_depuis_titre(titre_el)
        if not carte:
            return None
        prix_el = carte.select_one(".s-card__price")
        lien_el = carte.select_one('a[href*="/itm/"]')
        prix = _prix_depuis_texte(prix_el.get_text(" ", strip=True)) if prix_el else None
        url = lien_el.get("href") if lien_el else None
        pid = _id_depuis_url(url)
        if not pid:
            return None
        if prix is None or prix < 10:
            return None  # prix absent ou enchère démarrant très bas (eBay)
        analyse = analyser_texte(titre)
        if not analyse["modele"]:
            return None
        return {
            "plateforme": "ebay",
            "plateforme_id": pid,
            "url": url.split("?")[0] if url else None,
            "titre": titre,
            "modele": analyse["modele"],
            "stockage": analyse["stockage"],
            "couleur": None,
            "etat": analyse["etat"],
            "panne": analyse["panne"],
            "prix": prix,
            "ville": None,
            "code_postal": None,
            "description": titre,
            "date_publication": None,
            "icloud_detecte": analyse["icloud_detecte"],
        }
    except (AttributeError, ValueError, TypeError) as exc:
        log.debug(f"Item eBay ignoré (parsing) : {exc}")
        return None


async def scraper(pages: int = 1) -> list[dict]:
    """
    Scrape les annonces iPhone sur eBay.fr (HTML, cartes s-card).
    Retourne une liste normalisée (vide si bloqué ou en cooldown).
    """
    if antiban.en_cooldown(_SOURCE):
        log.info("eBay en cooldown (récemment bloqué) — source ignorée ce scan.")
        return []

    resultats: list[dict] = []
    vus: set[str] = set()

    try:
        async with httpx.AsyncClient(timeout=25, headers=_entetes(),
                                     follow_redirects=True) as client:
            # Visite de la page d'accueil pour récupérer les cookies (anti-403).
            try:
                await client.get(_HOME)
            except httpx.HTTPError as exc:
                log.warning(f"eBay : amorçage cookies impossible : {exc}")

            for page in range(1, pages + 1):
                params = {"_nkw": "iphone", "_sop": "10", "_ipg": "60", "_pgn": str(page)}
                try:
                    rep = await client.get(_URL, params=params)
                    if rep.status_code in (403, 429):
                        log.warning(f"eBay bloqué (HTTP {rep.status_code}) — cooldown 20 min.")
                        antiban.declencher_cooldown(_SOURCE, 20)
                        return resultats
                    if rep.status_code != 200:
                        log.warning(f"eBay HTTP {rep.status_code} page {page}.")
                        continue
                    soup = BeautifulSoup(rep.text, "html.parser")
                    for titre_el in soup.select(".s-card__title"):
                        norm = _normaliser(titre_el)
                        if norm and norm["plateforme_id"] not in vus:
                            vus.add(norm["plateforme_id"])
                            resultats.append(norm)
                except httpx.HTTPError as exc:
                    log.warning(f"Erreur réseau eBay : {exc}")
                await asyncio.sleep(random.uniform(2, 5))
        if resultats:
            antiban.reinitialiser(_SOURCE)
    except Exception as exc:
        log.error(f"Scraper eBay en échec : {exc}")
    log.info(f"eBay : {len(resultats)} annonces iPhone collectées.")
    return resultats
