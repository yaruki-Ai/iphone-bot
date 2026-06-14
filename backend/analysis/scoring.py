"""
scoring.py — Calcul du score d'achat /100 d'une annonce cassée.

Décomposition :
  - Liquidité    /30 : vitesse de revente du modèle (indice marché)
  - Rentabilité  /30 : marge estimée vs prix demandé
  - Réparation   /20 : difficulté de la panne (écran=facile ... carte mère=impossible)
  - Risque       /20 : iCloud / panne inconnue / pour pièces
Fournit aussi le prix d'achat maximum conseillé et le ROI estimé en €.
"""

from backend.config import settings
from backend.scraper.parser import difficulte_reparation

# Coût estimatif des pièces par type de panne (en €), pour le SCORING uniquement.
# Le coût réel reste saisi manuellement dans le stock. Valeurs volontairement
# génériques (pièces compatibles, hors main-d'œuvre).
COUT_PIECES_ESTIME: dict[str | None, float] = {
    None: 0.0,
    "ecran": 45.0,
    "batterie": 15.0,
    "vitre_arriere": 30.0,
    "camera": 35.0,
    "charge": 20.0,
    "faceid": 60.0,
    "ne_sallume_plus": 50.0,
    "inconnue": 40.0,
    "pour_pieces": 0.0,
}

# Points de difficulté de réparation (sur 20).
_POINTS_REPARATION = {
    "facile": 20.0,
    "moyen": 13.0,
    "difficile": 6.0,
    "impossible": 0.0,
    "aucune": 20.0,  # annonce fonctionnelle : pas de réparation à prévoir
}


def cout_pieces_estime(panne: str | None) -> float:
    """Retourne le coût estimatif des pièces pour une panne donnée (€)."""
    return COUT_PIECES_ESTIME.get(panne, 40.0)


def frais_acquisition(plateforme: str | None, prix: float) -> float:
    """
    Frais estimés à l'achat (€), en plus du prix affiché : livraison + protection.
    - Vinted : protection acheteur (~0,70 € + 5 %) + livraison.
    - eBay   : livraison estimée.
    - Leboncoin : 0 (remise en main propre le plus souvent).
    """
    livraison = settings.FRAIS_LIVRAISON
    p = (plateforme or "").lower()
    if p == "vinted":
        return round(0.70 + 0.05 * (prix or 0) + livraison, 2)
    if p == "ebay":
        return round(livraison, 2)
    return 0.0


def _score_liquidite(stats: dict | None) -> float:
    """Liquidité /30 à partir de l'indice de liquidité du modèle (0-100)."""
    if not stats or stats.get("score_liquidite") is None:
        return 15.0  # valeur neutre quand le marché est inconnu
    return round(stats["score_liquidite"] / 100.0 * 30.0, 1)


def _score_rentabilite(prix: float, revente_est: float | None,
                       cout_pieces: float) -> tuple[float, float]:
    """
    Rentabilité /30 + ROI estimé en €.
    La marge en % de la revente est convertie linéairement : 0 % -> 0 pt,
    >= 50 % -> 30 pts.
    """
    if not revente_est or revente_est <= 0 or not prix:
        return 0.0, 0.0
    roi = revente_est - prix - cout_pieces            # marge brute estimée en €
    marge_pct = roi / revente_est * 100.0
    points = max(0.0, min(30.0, marge_pct / 50.0 * 30.0))
    return round(points, 1), round(roi, 2)


def _score_reparation(panne: str | None) -> float:
    """Difficulté de réparation /20."""
    return _POINTS_REPARATION.get(difficulte_reparation(panne), 6.0)


def _score_risque(panne: str | None, icloud_detecte: int) -> float:
    """Risque /20 : on part de 20 et on retire des points selon les signaux."""
    points = 20.0
    if icloud_detecte:
        points -= 12.0
    if panne == "pour_pieces":
        points -= 10.0
    if panne == "inconnue":
        points -= 8.0
    if panne == "ne_sallume_plus":
        points -= 6.0
    return max(0.0, points)


def prix_max_achat(revente_est: float | None, cout_pieces: float,
                   marge_cible_pct: float | None = None) -> float | None:
    """
    Prix d'achat maximum pour atteindre la marge cible.
    prix_max = revente - pièces - (revente * marge_cible%)
    """
    if not revente_est or revente_est <= 0:
        return None
    marge = marge_cible_pct if marge_cible_pct is not None else settings.MARGE_CIBLE_POURCENT
    pm = revente_est - cout_pieces - revente_est * (marge / 100.0)
    return round(max(0.0, pm), 2)


def scorer_annonce(annonce: dict, stats: dict | None,
                   marge_cible_pct: float | None = None) -> dict:
    """
    Calcule le score complet d'une annonce.
    Retourne un dict : score, détail des composantes, roi_estime, prix_max_achat.
    'stats' = ligne marche_stats du modèle (peut être None si marché inconnu).
    """
    panne = annonce.get("panne")
    prix = annonce.get("prix") or 0.0
    icloud = annonce.get("icloud_detecte", 0)

    # Prix de revente estimé = prix médian des fonctionnels du modèle.
    revente_est = stats.get("prix_median") if stats else None
    cout_pieces = cout_pieces_estime(panne)
    frais = frais_acquisition(annonce.get("plateforme"), prix)
    # Coût total à déduire de la revente : pièces + frais d'achat (livraison/protection).
    cout_total = cout_pieces + frais

    s_liq = _score_liquidite(stats)
    s_rent, roi = _score_rentabilite(prix, revente_est, cout_total)
    s_rep = _score_reparation(panne)
    s_risk = _score_risque(panne, icloud)

    total = round(s_liq + s_rent + s_rep + s_risk)
    total = max(0, min(100, total))

    return {
        "score": total,
        "score_liquidite": s_liq,
        "score_rentabilite": s_rent,
        "score_reparation": s_rep,
        "score_risque": s_risk,
        "roi_estime": roi,
        "frais_acquisition": frais,
        "prix_max_achat": prix_max_achat(revente_est, cout_total, marge_cible_pct),
        "revente_estimee": revente_est,
    }
