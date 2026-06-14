"""
opportunity.py — Détection des opportunités d'achat.

Recalcule le score de chaque annonce cassée active (à partir des stats marché),
persiste le score et le prix d'achat maximum dans la table 'annonces', puis
identifie les opportunités : annonces dont le prix est sous le seuil conseillé
et/ou dont le score dépasse le seuil d'alerte.
"""

from typing import Any

from backend.analysis.scoring import scorer_annonce
from backend.config import settings
from backend.database.db import execute, fetch_all
from backend.logger import log


async def _index_stats() -> dict[tuple[str, str | None], dict[str, Any]]:
    """Charge marche_stats en mémoire, indexé par (modele, stockage)."""
    lignes = await fetch_all("SELECT * FROM marche_stats")
    return {(l["modele"], l["stockage"]): l for l in lignes}


async def recalculer_scores() -> list[dict[str, Any]]:
    """
    Recalcule et enregistre le score de toutes les annonces cassées actives.
    Retourne la liste des annonces dont le score >= seuil d'alerte (candidates
    à une notification ; le dédoublonnage des alertes est géré par le notifier).
    """
    stats_idx = await _index_stats()
    # On score les annonces cassées (à réparer) ET fonctionnelles (bonnes affaires).
    actives = await fetch_all(
        "SELECT * FROM annonces WHERE active = 1 AND etat IN ('casse', 'fonctionnel')"
    )
    opportunites: list[dict[str, Any]] = []

    for annonce in actives:
        stats = stats_idx.get((annonce["modele"], annonce["stockage"]))
        resultat = scorer_annonce(annonce, stats)
        await execute(
            """UPDATE annonces SET
                   score = ?, score_liquidite = ?, score_rentabilite = ?,
                   score_reparation = ?, score_risque = ?,
                   prix_max_achat = ?, roi_estime = ?, updated_at = ?
               WHERE id = ?""",
            (
                resultat["score"], resultat["score_liquidite"],
                resultat["score_rentabilite"], resultat["score_reparation"],
                resultat["score_risque"], resultat["prix_max_achat"],
                resultat["roi_estime"], annonce["derniere_detection"], annonce["id"],
            ),
        )
        # Fusion annonce + résultat pour le notifier.
        enrichie = {**annonce, **resultat}
        if resultat["score"] >= settings.SEUIL_ALERTE_SCORE:
            opportunites.append(enrichie)

    log.info(
        f"Scores recalculés sur {len(actives)} annonces — "
        f"{len(opportunites)} au-dessus du seuil {settings.SEUIL_ALERTE_SCORE}."
    )
    return opportunites


async def top_opportunites(limite: int = 100, score_min: int = 0,
                           prix_min: float = 0, prix_max: float = 0,
                           rentables_seulement: bool = True,
                           etat: str | None = None) -> list[dict[str, Any]]:
    """
    Retourne les opportunités actives scorées (cassées ET/OU fonctionnelles).
    Par défaut : toutes les annonces RENTABLES (ROI > 0), sans filtre de score.
    'etat' optionnel : 'casse', 'fonctionnel', ou None (les deux).
    """
    conditions = ["active = 1", "etat IN ('casse','fonctionnel')",
                  "score IS NOT NULL", "score >= ?"]
    params: list[Any] = [score_min]
    if etat in ("casse", "fonctionnel"):
        conditions.append("etat = ?")
        params.append(etat)
    if rentables_seulement:
        conditions.append("roi_estime > 0")
    if prix_min and prix_min > 0:
        conditions.append("prix >= ?")
        params.append(prix_min)
    if prix_max and prix_max > 0:
        conditions.append("prix <= ?")
        params.append(prix_max)
    params.append(limite)
    where = " AND ".join(conditions)
    return await fetch_all(
        f"SELECT * FROM annonces WHERE {where} ORDER BY score DESC, roi_estime DESC LIMIT ?",
        tuple(params),
    )
