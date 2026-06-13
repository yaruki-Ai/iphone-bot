"""
prediction.py — Prédictions basées UNIQUEMENT sur l'historique personnel.

Statistiques simples (moyenne, médiane, écart-type) calculées sur la table
'historique'. Produit une prédiction GLOBALE et une prédiction par modèle.
Règle métier : moins de 10 entrées => 'Données insuffisantes'
(donnees_suffisantes = 0). Pas de ML externe.
"""

import statistics
from collections import defaultdict
from typing import Any

from backend.database.db import execute, fetch_all, maintenant_iso
from backend.logger import log

SEUIL_DONNEES = 10  # nombre minimum d'entrées pour des prédictions fiables


def _stats_groupe(entrees: list[dict[str, Any]]) -> dict[str, Any]:
    """Calcule les indicateurs prédictifs sur un groupe d'entrées d'historique."""
    marges = [e["marge_reelle"] for e in entrees if e.get("marge_reelle") is not None]
    delais = [e["delai_revente_jours"] for e in entrees if e.get("delai_revente_jours") is not None]
    nb_sav = sum(1 for e in entrees if e.get("retour_sav"))
    nb = len(entrees)

    return {
        "nb_entrees": nb,
        "delai_moyen_revente_jours": round(statistics.mean(delais), 1) if delais else None,
        "marge_moyenne": round(statistics.mean(marges), 2) if marges else None,
        "marge_mediane": round(statistics.median(marges), 2) if marges else None,
        "marge_ecart_type": round(statistics.pstdev(marges), 2) if len(marges) > 1 else 0.0,
        "taux_retour_sav": round(nb_sav / nb * 100, 1) if nb else None,
        "donnees_suffisantes": 1 if nb >= SEUIL_DONNEES else 0,
    }


async def _enregistrer(modele: str, s: dict[str, Any]) -> None:
    """Insère ou met à jour une ligne de prédiction (clé : modele)."""
    await execute(
        """INSERT INTO predictions (
               modele, nb_entrees, delai_moyen_revente_jours, marge_moyenne,
               marge_mediane, marge_ecart_type, taux_retour_sav,
               donnees_suffisantes, calcule_le
           ) VALUES (?,?,?,?,?,?,?,?,?)
           ON CONFLICT(modele) DO UPDATE SET
               nb_entrees=excluded.nb_entrees,
               delai_moyen_revente_jours=excluded.delai_moyen_revente_jours,
               marge_moyenne=excluded.marge_moyenne,
               marge_mediane=excluded.marge_mediane,
               marge_ecart_type=excluded.marge_ecart_type,
               taux_retour_sav=excluded.taux_retour_sav,
               donnees_suffisantes=excluded.donnees_suffisantes,
               calcule_le=excluded.calcule_le""",
        (
            modele, s["nb_entrees"], s["delai_moyen_revente_jours"], s["marge_moyenne"],
            s["marge_mediane"], s["marge_ecart_type"], s["taux_retour_sav"],
            s["donnees_suffisantes"], maintenant_iso(),
        ),
    )


async def recalculer_predictions() -> dict[str, Any]:
    """
    Recalcule toutes les prédictions depuis l'historique.
    Appelée automatiquement après chaque nouvelle vente saisie.
    Retourne la prédiction GLOBALE (pour affichage rapide).
    """
    historique = await fetch_all("SELECT * FROM historique")

    if not historique:
        glob = {
            "nb_entrees": 0, "delai_moyen_revente_jours": None, "marge_moyenne": None,
            "marge_mediane": None, "marge_ecart_type": 0.0, "taux_retour_sav": None,
            "donnees_suffisantes": 0,
        }
        await _enregistrer("GLOBAL", glob)
        return {"modele": "GLOBAL", **glob}

    # Prédiction globale (toutes ventes confondues).
    glob = _stats_groupe(historique)
    await _enregistrer("GLOBAL", glob)

    # Prédiction par modèle.
    par_modele: dict[str, list[dict]] = defaultdict(list)
    for e in historique:
        if e.get("modele"):
            par_modele[e["modele"]].append(e)
    for modele, entrees in par_modele.items():
        await _enregistrer(modele, _stats_groupe(entrees))

    log.info(
        f"Prédictions recalculées : {glob['nb_entrees']} ventes "
        f"({'suffisant' if glob['donnees_suffisantes'] else 'insuffisant'})."
    )
    return {"modele": "GLOBAL", **glob}
