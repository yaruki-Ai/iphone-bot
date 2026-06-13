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
    cassees = await fetch_all(
        "SELECT * FROM annonces WHERE active = 1 AND etat = 'casse'"
    )
    opportunites: list[dict[str, Any]] = []

    for annonce in cassees:
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
        f"Scores recalculés sur {len(cassees)} annonces cassées — "
        f"{len(opportunites)} au-dessus du seuil {settings.SEUIL_ALERTE_SCORE}."
    )
    return opportunites


async def top_opportunites(limite: int = 50, score_min: int = 0) -> list[dict[str, Any]]:
    """Retourne les meilleures opportunités actives (annonces cassées scorées)."""
    return await fetch_all(
        """SELECT * FROM annonces
           WHERE active = 1 AND etat = 'casse' AND score IS NOT NULL AND score >= ?
           ORDER BY score DESC, roi_estime DESC
           LIMIT ?""",
        (score_min, limite),
    )
