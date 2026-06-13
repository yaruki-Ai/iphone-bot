"""
antiban.py — Roues de secours contre le blocage / bannissement des scrapers.

Fournit :
  - une rotation de User-Agents réalistes (évite la signature robotique) ;
  - des en-têtes HTTP randomisés ;
  - un registre de "cooldown" : une source bloquée (403/429) est mise en pause
    quelques minutes pour ne pas insister et risquer un bannissement IP.
Le tout est partagé par les scrapers Leboncoin et Vinted.
"""

import random
import time

# Pool de User-Agents desktop récents et crédibles (Chrome/Firefox/Edge, Win/Mac).
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]

_ACCEPT_LANGS = ["fr-FR,fr;q=0.9", "fr-FR,fr;q=0.9,en-US;q=0.8", "fr,fr-FR;q=0.9,en;q=0.7"]

# Registre des sources en cooldown : { "leboncoin": timestamp_de_fin }.
_cooldowns: dict[str, float] = {}


def user_agent() -> str:
    """Retourne un User-Agent aléatoire du pool."""
    return random.choice(_USER_AGENTS)


def entetes(referer: str = "") -> dict[str, str]:
    """Construit un jeu d'en-têtes HTTP réalistes et randomisés."""
    h = {
        "User-Agent": user_agent(),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": random.choice(_ACCEPT_LANGS),
        "Cache-Control": "no-cache",
    }
    if referer:
        h["Referer"] = referer
    return h


def en_cooldown(source: str) -> bool:
    """Vrai si la source est encore en pause (récemment bloquée)."""
    fin = _cooldowns.get(source, 0)
    return time.time() < fin


def declencher_cooldown(source: str, minutes: float = 20.0) -> None:
    """Met une source en pause après un blocage, pour éviter un bannissement."""
    _cooldowns[source] = time.time() + minutes * 60.0


def reinitialiser(source: str) -> None:
    """Annule le cooldown d'une source (après un succès)."""
    _cooldowns.pop(source, None)
