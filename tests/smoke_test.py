"""
smoke_test.py — Test de fumée du backend (hors réseau).

Vérifie : init base, parser iPhone, amorçage démo, calculs marché/scoring,
prédictions, et quelques requêtes. À lancer depuis la racine du projet :
    .venv\\Scripts\\python.exe -m tests.smoke_test
"""

import asyncio

from backend.analysis import market, opportunity, prediction
from backend.database.db import fetch_all, fetch_one, init_db
from backend.scraper import simulator
from backend.scraper.parser import analyser_texte


def test_parser() -> None:
    """Teste l'identification de quelques annonces typiques."""
    cas = [
        ("iPhone 13 Pro Max 256 Go écran cassé", "iPhone 13 Pro Max", "256 Go", "casse", "ecran"),
        ("iphone 11 128go très bon état", "iPhone 11", "128 Go", "fonctionnel", None),
        ("iPhone XS Max bloqué iCloud pour pièces", "iPhone XS Max", None, "casse", "pour_pieces"),
        ("iphone SE 2022 64 gb ne s'allume plus", "iPhone SE 2022", "64 Go", "casse", "ne_sallume_plus"),
        ("iPhone 12 Pro 128 Go batterie HS", "iPhone 12 Pro", "128 Go", "casse", "batterie"),
    ]
    print("\n--- Test parser ---")
    for texte, modele, stockage, etat, panne in cas:
        r = analyser_texte(texte)
        ok = (r["modele"] == modele and r["stockage"] == stockage
              and r["etat"] == etat and r["panne"] == panne)
        marque = "OK " if ok else "ERR"
        print(f"[{marque}] {texte[:45]:45} -> {r['modele']} | {r['stockage']} | {r['etat']} | {r['panne']}")
        assert ok, f"Parser KO pour : {texte} -> {r}"
    # iCloud
    assert analyser_texte("iphone 11 bloqué icloud")["icloud_detecte"] == 1

    # Accessoires / pièces détachées : doivent être rejetés (modele = None).
    accessoires = [
        "Écran iPhone 12 Pro Max",
        "Protection écran QDOS Glass iPhone 15 Plus",
        "caméra arrière iPhone 14 Pro Max comme neuf",
        "Coque silicone iPhone 13",
        "Vitre arrière iPhone 11 noire",
        "Chargeur rapide pour iPhone",
        "Batterie iPhone 12 neuve",
        "Originale Apple iPhone 16 Pro Clear Case mit MagSafe transparent",
        "Quad Lock iPhone 11 Pro",
    ]
    for a in accessoires:
        r = analyser_texte(a)
        marque = "OK " if r["modele"] is None else "ERR"
        print(f"[{marque}] ACCESSOIRE rejeté : {a[:45]:45} -> modele={r['modele']}")
        assert r["modele"] is None, f"Accessoire non rejeté : {a} -> {r}"

    # Accessoire dont le TITRE ne dit rien, mais la DESCRIPTION trahit (coque).
    r = analyser_texte("iPhone 11 Pro", "Je vends une coque Quad Lock compatible iPhone 11 Pro")
    print(f"[{'OK ' if r['modele'] is None else 'ERR'}] ACCESSOIRE via description -> modele={r['modele']}")
    assert r["modele"] is None, f"Coque (description) non rejetée : {r}"

    # Vrais iPhones cassés : doivent rester acceptés (panne détectée).
    assert analyser_texte("iPhone 13 Pro Max écran cassé")["modele"] == "iPhone 13 Pro Max"
    assert analyser_texte("iPhone 11 vitre arrière cassée")["panne"] == "vitre_arriere"

    # Reconditionnés / fonctionnels : NE doivent PAS être classés cassés.
    fonctionnels = [
        "Apple iPhone SE 2022 128GB 5G Noir Nouvelle Batterie 100%",
        "iPhone 8 64Go Noir Batterie 100% NEUF DÉBALLÉ Débloqué Garantie",
        "iPhone 12 Pro 128 Go débloqué très bon état",
        "Apple iPhone XS 256GB Gris reconditionné comme neuf",
    ]
    for f in fonctionnels:
        r = analyser_texte(f)
        ok = r["etat"] == "fonctionnel" and r["panne"] is None and r["icloud_detecte"] == 0
        marque = "OK " if ok else "ERR"
        print(f"[{marque}] FONCTIONNEL : {f[:48]:48} -> etat={r['etat']} panne={r['panne']} icloud={r['icloud_detecte']}")
        assert ok, f"Reconditionné mal classé : {f} -> {r}"
    print("Parser : tous les cas passent (accessoires rejetés, reconditionnés OK, iPhones gardés).")


async def main() -> None:
    """Scénario complet de test backend."""
    test_parser()

    print("\n--- Init base + amorçage démo ---")
    await init_db()
    nb = await simulator.amorcer_si_vide()
    print(f"Annonces de démo insérées : {nb}")

    total = await fetch_one("SELECT COUNT(*) AS n FROM annonces")
    actives = await fetch_one("SELECT COUNT(*) AS n FROM annonces WHERE active=1")
    vendues = await fetch_one("SELECT COUNT(*) AS n FROM annonces WHERE active=0")
    print(f"Total annonces : {total['n']} | actives : {actives['n']} | vendues : {vendues['n']}")

    print("\n--- Calcul stats marché ---")
    nb_modeles = await market.recalculer_tout()
    print(f"Modèles avec stats : {nb_modeles}")
    sample = await fetch_all(
        "SELECT modele, stockage, prix_median, delai_median_vente_heures, score_liquidite "
        "FROM marche_stats ORDER BY score_liquidite DESC LIMIT 5")
    for s in sample:
        print(f"  {s['modele']} {s['stockage']}: médian={s['prix_median']}€ "
              f"délai_méd={s['delai_median_vente_heures']}h liq={s['score_liquidite']}")

    print("\n--- Scoring / opportunités ---")
    opps = await opportunity.recalculer_scores()
    print(f"Opportunités (>= seuil) : {len(opps)}")
    top = await opportunity.top_opportunites(limite=5)
    for o in top:
        print(f"  [{o['score']}/100] {o['modele']} {o['stockage']} {o['panne']} "
              f"-> {o['prix']}€ (max conseillé {o['prix_max_achat']}€, ROI {o['roi_estime']}€)")

    print("\n--- Prédictions (sans historique) ---")
    pred = await prediction.recalculer_predictions()
    print(f"Global : {pred['nb_entrees']} entrées, suffisant={pred['donnees_suffisantes']}")

    print("\n=== SMOKE TEST OK ===")


if __name__ == "__main__":
    asyncio.run(main())
