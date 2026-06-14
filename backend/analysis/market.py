"""
market.py — Calculs de statistiques de marché par modèle d'iPhone.

Pour chaque couple (modèle, stockage), calcule à partir des annonces en base :
  - prix min / moyen / médian / premium (sur les annonces FONCTIONNELLES)
  - délais de vente moyen et médian (sur les annonces disparues = vendues)
  - volume d'annonces cassées vs fonctionnelles actives
  - évolution des prix sur 7 et 30 jours
  - un indice de liquidité du modèle (0-100)
Statistiques simples uniquement (moyenne, médiane, percentile), pas de ML.
"""

import statistics
from datetime import datetime, timedelta, timezone

from backend.database.db import execute, fetch_all, maintenant_iso
from backend.logger import log
from backend.repository import tous_les_modeles


def _percentile(valeurs: list[float], p: float) -> float | None:
    """Retourne le percentile p (0-100) d'une liste, par interpolation linéaire."""
    if not valeurs:
        return None
    vals = sorted(valeurs)
    if len(vals) == 1:
        return vals[0]
    rang = (p / 100.0) * (len(vals) - 1)
    bas = int(rang)
    haut = min(bas + 1, len(vals) - 1)
    frac = rang - bas
    return vals[bas] + (vals[haut] - vals[bas]) * frac


def _mediane(valeurs: list[float]) -> float | None:
    """Médiane sécurisée (None si liste vide)."""
    return statistics.median(valeurs) if valeurs else None


def _evolution(prix_recents: list[float], prix_anciens: list[float]) -> float | None:
    """Variation en % entre deux médianes de prix (None si données insuffisantes)."""
    mr, ma = _mediane(prix_recents), _mediane(prix_anciens)
    if not mr or not ma:
        return None
    return round((mr - ma) / ma * 100, 2)


def _score_liquidite(delai_median_h: float | None, nb_fonctionnelles: int) -> float:
    """
    Indice de liquidité du modèle (0-100).
    Basé en priorité sur la vitesse de revente médiane ; à défaut, sur le volume
    d'annonces fonctionnelles actives (proxy de demande).
    """
    if delai_median_h:
        jours = delai_median_h / 24.0
        # 1 jour ≈ 100, ~13 jours ≈ 0 (pente de 8 points par jour).
        return round(max(0.0, min(100.0, 100 - (jours - 1) * 8)), 1)
    # Pas d'historique de vente : on estime via le volume (plafonné à 60).
    return round(min(60.0, nb_fonctionnelles * 5.0), 1)


async def calculer_stats_modele(modele: str, stockage: str | None) -> dict | None:
    """Calcule et enregistre les stats de marché d'un (modèle, stockage)."""
    cond_stockage = "AND stockage = ?" if stockage else "AND stockage IS NULL"
    params = (modele, stockage) if stockage else (modele,)

    annonces = await fetch_all(
        f"SELECT prix, etat, active, premiere_detection, temps_rotation_heures "
        f"FROM annonces WHERE modele = ? {cond_stockage}",
        params,
    )
    if not annonces:
        return None

    now = datetime.now(timezone.utc)
    prix_fonctionnels = [
        a["prix"] for a in annonces
        if a["etat"] == "fonctionnel" and a["prix"] and a["prix"] > 0
    ]
    rotations = [
        a["temps_rotation_heures"] for a in annonces
        if a["temps_rotation_heures"] and a["temps_rotation_heures"] > 0
    ]
    nb_cassees = sum(1 for a in annonces if a["etat"] == "casse" and a["active"] == 1)
    nb_fonctionnelles = sum(1 for a in annonces if a["etat"] == "fonctionnel" and a["active"] == 1)

    # Évolution des prix : médiane des fonctionnels détectés sur deux fenêtres.
    def prix_fenetre(j_debut: int, j_fin: int) -> list[float]:
        """Prix des annonces fonctionnelles détectées entre j_debut et j_fin jours."""
        debut = now - timedelta(days=j_debut)
        fin = now - timedelta(days=j_fin)
        res = []
        for a in annonces:
            if a["etat"] != "fonctionnel" or not a["prix"]:
                continue
            try:
                d = datetime.fromisoformat(a["premiere_detection"])
            except (ValueError, TypeError):
                continue
            # 'debut' est la borne la plus ancienne, 'fin' la plus récente.
            if debut <= d <= fin:
                res.append(a["prix"])
        return res

    evo_7j = _evolution(prix_fenetre(7, 0), prix_fenetre(14, 7))
    evo_30j = _evolution(prix_fenetre(30, 0), prix_fenetre(60, 30))

    delai_moyen = round(statistics.mean(rotations), 1) if rotations else None
    delai_median = round(_mediane(rotations), 1) if rotations else None

    stats = {
        "modele": modele,
        "stockage": stockage,
        "prix_min": min(prix_fonctionnels) if prix_fonctionnels else None,
        "prix_moyen": round(statistics.mean(prix_fonctionnels), 2) if prix_fonctionnels else None,
        "prix_median": _mediane(prix_fonctionnels),
        "prix_premium": _percentile(prix_fonctionnels, 90) if prix_fonctionnels else None,
        "delai_moyen_vente_heures": delai_moyen,
        "delai_median_vente_heures": delai_median,
        "nb_annonces_cassees": nb_cassees,
        "nb_annonces_fonctionnelles": nb_fonctionnelles,
        "evolution_prix_7j": evo_7j,
        "evolution_prix_30j": evo_30j,
        "score_liquidite": _score_liquidite(delai_median, nb_fonctionnelles),
        "calcule_le": maintenant_iso(),
    }

    await execute(
        """INSERT INTO marche_stats (
               modele, stockage, prix_min, prix_moyen, prix_median, prix_premium,
               delai_moyen_vente_heures, delai_median_vente_heures,
               nb_annonces_cassees, nb_annonces_fonctionnelles,
               evolution_prix_7j, evolution_prix_30j, score_liquidite, calcule_le
           ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(modele, stockage) DO UPDATE SET
               prix_min=excluded.prix_min, prix_moyen=excluded.prix_moyen,
               prix_median=excluded.prix_median, prix_premium=excluded.prix_premium,
               delai_moyen_vente_heures=excluded.delai_moyen_vente_heures,
               delai_median_vente_heures=excluded.delai_median_vente_heures,
               nb_annonces_cassees=excluded.nb_annonces_cassees,
               nb_annonces_fonctionnelles=excluded.nb_annonces_fonctionnelles,
               evolution_prix_7j=excluded.evolution_prix_7j,
               evolution_prix_30j=excluded.evolution_prix_30j,
               score_liquidite=excluded.score_liquidite,
               calcule_le=excluded.calcule_le""",
        (
            stats["modele"], stats["stockage"], stats["prix_min"], stats["prix_moyen"],
            stats["prix_median"], stats["prix_premium"], stats["delai_moyen_vente_heures"],
            stats["delai_median_vente_heures"], stats["nb_annonces_cassees"],
            stats["nb_annonces_fonctionnelles"], stats["evolution_prix_7j"],
            stats["evolution_prix_30j"], stats["score_liquidite"], stats["calcule_le"],
        ),
    )
    return stats


async def recalculer_tout() -> int:
    """Recalcule les stats de marché pour tous les modèles présents en base."""
    # On repart d'une table propre : évite les doublons (notamment quand le
    # stockage est NULL, où la contrainte UNIQUE ne déclenche pas l'upsert).
    await execute("DELETE FROM marche_stats")
    modeles = await tous_les_modeles()
    nb = 0
    for m in modeles:
        try:
            res = await calculer_stats_modele(m["modele"], m["stockage"])
            if res:
                nb += 1
        except Exception as exc:  # robustesse : un modèle en erreur n'arrête pas le reste
            log.error(f"Stats marché échouées pour {m['modele']} {m['stockage']} : {exc}")
    log.info(f"Stats marché recalculées pour {nb} modèles.")
    return nb
