"""
discord.py — Alertes et rapports via Discord Webhook (sobre, sans emoji).

Deux canaux distincts :
  - alertes-opportunites : alerte immédiate quand une annonce dépasse le seuil
  - rapport-quotidien    : rapport du soir (top 5 cassés + top 5 fonctionnels)
Chaque envoi est journalisé dans la table 'alertes'. Les alertes d'opportunité
sont dédoublonnées (une seule notification par annonce). Retry réseau intégré.
"""

import asyncio
from typing import Any

import httpx

from backend.config import settings
from backend.database.db import execute, fetch_one, maintenant_iso
from backend.logger import log

# Couleurs des embeds Discord (barre latérale), sobres.
_COULEUR_HAUTE = 0x2E7D5B    # vert profond (excellente opportunité)
_COULEUR_MOYENNE = 0xB8860B  # ambre discret
_COULEUR_RAPPORT = 0x33506B  # bleu ardoise

_LIBELLE_PANNE = {
    "ecran": "Écran cassé", "vitre_arriere": "Vitre arrière", "batterie": "Batterie",
    "faceid": "Face ID", "camera": "Caméra", "charge": "Charge",
    "ne_sallume_plus": "Ne s'allume plus", "pour_pieces": "Pour pièces",
    "inconnue": "Panne inconnue",
}


async def _post_webhook(url: str, payload: dict[str, Any], tentatives: int = 3) -> bool:
    """Envoie un payload à un webhook Discord avec retry et back-off."""
    if not url or not url.startswith("http"):
        log.warning("Webhook Discord non configuré : envoi ignoré.")
        return False
    for i in range(1, tentatives + 1):
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                rep = await client.post(url, json=payload)
            if rep.status_code in (200, 204):
                return True
            if rep.status_code == 429:  # rate limit : on respecte le retry_after
                retry_after = rep.json().get("retry_after", 2)
                await asyncio.sleep(float(retry_after) + 0.5)
                continue
            log.warning(f"Discord a répondu {rep.status_code} : {rep.text[:200]}")
        except (httpx.HTTPError, ValueError) as exc:
            log.warning(f"Erreur d'envoi Discord (tentative {i}/{tentatives}) : {exc}")
        await asyncio.sleep(1.5 * i)
    return False


def _libelle_panne(panne: str | None) -> str:
    """Libellé lisible d'une panne."""
    return _LIBELLE_PANNE.get(panne, "—")


async def _deja_alertee(annonce_id: int) -> bool:
    """Vrai si une alerte d'opportunité a déjà été envoyée pour cette annonce."""
    ligne = await fetch_one(
        "SELECT id FROM alertes WHERE type='opportunite' AND annonce_id=? AND envoye=1",
        (annonce_id,),
    )
    return ligne is not None


async def _journaliser(type_: str, annonce_id: int | None, message: str,
                       score: int | None, envoye: bool, erreur: str | None = None) -> None:
    """Enregistre la notification dans la table 'alertes'."""
    await execute(
        """INSERT INTO alertes (type, annonce_id, canal, message, score, envoye, erreur, created_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        (type_, annonce_id, "discord", message, score, 1 if envoye else 0, erreur, maintenant_iso()),
    )


async def alerter_opportunite(annonce: dict[str, Any]) -> bool:
    """
    Envoie une alerte Discord pour une opportunité (annonce cassée à fort score).
    Dédoublonne via la table 'alertes'. Retourne True si réellement envoyée.
    """
    annonce_id = annonce.get("id")
    if annonce_id and await _deja_alertee(annonce_id):
        return False

    if not settings.discord_alertes_actif:
        await _journaliser("opportunite", annonce_id, "webhook alertes non configuré",
                           annonce.get("score"), False, "webhook manquant")
        return False

    score = annonce.get("score", 0)
    couleur = _COULEUR_HAUTE if score >= 80 else _COULEUR_MOYENNE
    modele = annonce.get("modele") or "iPhone (modèle inconnu)"
    stockage = annonce.get("stockage") or ""
    prix = annonce.get("prix")
    roi = annonce.get("roi_estime")
    prix_max = annonce.get("prix_max_achat")
    revente = annonce.get("revente_estimee")

    # État affiché dans le titre : 'Bon état' (fonctionnel) ou la panne (cassé).
    if annonce.get("etat") == "fonctionnel":
        etat_txt = "Bon état (fonctionnel)"
    else:
        etat_txt = _libelle_panne(annonce.get("panne"))
    batt = annonce.get("batterie_pct")
    batt_txt = f"{batt} %" if batt else "non précisé"

    champs = [
        {"name": "Prix demandé", "value": f"{prix:.0f} €" if prix else "—", "inline": True},
        {"name": "Batterie", "value": batt_txt, "inline": True},
        {"name": "Score", "value": f"{score}/100", "inline": True},
        {"name": "Revente estimée", "value": f"{revente:.0f} €" if revente else "—", "inline": True},
        {"name": "Achat max conseillé", "value": f"{prix_max:.0f} €" if prix_max else "—", "inline": True},
        {"name": "Bénéfice estimé", "value": f"{roi:.0f} €" if roi is not None else "—", "inline": True},
    ]
    embed = {
        "title": f"Opportunité — {modele} {stockage} · {etat_txt}".strip(),
        "description": (annonce.get("titre") or "")[:200],
        "url": annonce.get("url") or None,
        "color": couleur,
        "fields": champs,
        "footer": {"text": f"{(annonce.get('plateforme') or '').capitalize()} · {annonce.get('ville') or 'France'}"},
    }
    # Photo de l'annonce en aperçu (si disponible).
    image_url = annonce.get("image_url")
    if image_url and str(image_url).startswith("http"):
        embed["image"] = {"url": image_url}
    payload = {"username": "Arbitrage iPhone", "embeds": [embed]}

    envoye = await _post_webhook(settings.DISCORD_WEBHOOK_ALERTES, payload)
    await _journaliser("opportunite", annonce_id, embed["title"], score, envoye,
                       None if envoye else "échec d'envoi")
    if envoye:
        log.info(f"Alerte Discord envoyée : {modele} {stockage} (score {score}).")
    return envoye


async def envoyer_rapport(top_cassees: list[dict], top_fonctionnels: list[dict]) -> bool:
    """
    Envoie LE récap quotidien : toutes les meilleures opportunités du jour en un
    seul message (pas d'alertes éparpillées). Liste les cassés intéressants
    (avec score, ROI, lien) + quelques bonnes affaires fonctionnelles.
    """
    if not settings.discord_rapport_actif:
        await _journaliser("rapport", None, "webhook rapport non configuré", None, False,
                           "webhook manquant")
        return False

    def _batt(a: dict) -> str:
        """Mention batterie compacte si connue."""
        return f" · batt {a['batterie_pct']} %" if a.get("batterie_pct") else ""

    def ligne_cassee(i: int, a: dict) -> str:
        """Une ligne numérotée d'opportunité cassée."""
        modele = f"{a.get('modele','?')} {a.get('stockage') or ''}".strip()
        return (f"`{i:>2}.` **{modele}** — {_libelle_panne(a.get('panne'))}{_batt(a)}\n"
                f"     {a.get('prix',0):.0f} € · score **{a.get('score',0)}** · "
                f"bénéfice ~{(a.get('roi_estime') or 0):.0f} € · "
                f"[voir l'annonce]({a.get('url','')})")

    def ligne_fonct(a: dict) -> str:
        """Une ligne de bonne affaire fonctionnelle."""
        modele = f"{a.get('modele','?')} {a.get('stockage') or ''}".strip()
        return f"• **{modele}** — {a.get('prix',0):.0f} €{_batt(a)} · [voir]({a.get('url','')})"

    if top_cassees:
        description = "\n".join(ligne_cassee(i + 1, a) for i, a in enumerate(top_cassees))
        titre = f"Récap du jour — {len(top_cassees)} opportunité(s) à étudier"
    else:
        description = "_Aucune opportunité intéressante détectée aujourd'hui._"
        titre = "Récap du jour — Arbitrage iPhone"

    embed = {
        "title": titre,
        "description": description[:4000],
        "color": _COULEUR_RAPPORT,
        "footer": {"text": "Récap automatique de 20h00 · meilleures opportunités rentables du jour"},
    }
    if top_fonctionnels:
        embed["fields"] = [{
            "name": "Bonnes affaires fonctionnelles (revente directe)",
            "value": "\n".join(ligne_fonct(a) for a in top_fonctionnels)[:1024],
            "inline": False,
        }]

    payload = {"username": "Arbitrage iPhone", "embeds": [embed]}
    envoye = await _post_webhook(settings.DISCORD_WEBHOOK_RAPPORT, payload)
    await _journaliser("rapport", None, f"récap quotidien ({len(top_cassees)} opp.)",
                       None, envoye, None if envoye else "échec d'envoi")
    if envoye:
        log.info("Récap quotidien Discord envoyé.")
    return envoye
