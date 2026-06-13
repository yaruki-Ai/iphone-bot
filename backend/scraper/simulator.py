"""
simulator.py — Générateur de données de démonstration réalistes.

Permet de faire fonctionner et démontrer tout le dashboard (marché, opportunités,
scores, prédictions) SANS accès live aux plateformes ni clés API. Activé via
SIMULATION_MODE dans .env.

Deux usages :
  - amorcer_si_vide() : remplit la base une première fois (annonces actives +
    annonces vendues passées, pour alimenter délais de rotation et tendances).
  - generer_scan() : renvoie quelques nouvelles annonces à chaque scan simulé.
"""

import random
from datetime import datetime, timedelta, timezone

from backend.database.db import execute, fetch_one, maintenant_iso
from backend.logger import log
from backend.scraper.parser import analyser_texte

# Catalogue de référence : (modèle, stockage, prix fonctionnel indicatif en €).
_CATALOGUE = [
    ("iPhone 11", "64 Go", 190), ("iPhone 11", "128 Go", 230),
    ("iPhone 12", "64 Go", 250), ("iPhone 12", "128 Go", 300),
    ("iPhone 12 Pro", "128 Go", 360), ("iPhone 13", "128 Go", 400),
    ("iPhone 13", "256 Go", 470), ("iPhone 13 Pro", "128 Go", 560),
    ("iPhone 14", "128 Go", 540), ("iPhone 14 Pro", "128 Go", 720),
    ("iPhone 15", "128 Go", 720), ("iPhone SE 2022", "64 Go", 180),
    ("iPhone XR", "64 Go", 150), ("iPhone XS", "64 Go", 170),
]

# Pannes et leur décote indicative (prix cassé = prix fonctionnel * facteur).
_PANNES_DECOTE = {
    "ecran": 0.55, "vitre_arriere": 0.62, "batterie": 0.68, "faceid": 0.45,
    "camera": 0.58, "charge": 0.5, "ne_sallume_plus": 0.32,
    "pour_pieces": 0.25, "inconnue": 0.4,
}
_TEXTE_PANNE = {
    "ecran": "écran cassé", "vitre_arriere": "vitre arrière cassée",
    "batterie": "batterie HS à changer", "faceid": "Face ID HS",
    "camera": "caméra défectueuse", "charge": "ne charge plus",
    "ne_sallume_plus": "ne s'allume plus", "pour_pieces": "pour pièces",
    "inconnue": "en panne, panne inconnue",
}
_VILLES = [("Paris", "75011"), ("Lyon", "69003"), ("Marseille", "13008"),
           ("Lille", "59000"), ("Bordeaux", "33000"), ("Toulouse", "31000"),
           ("Nantes", "44000"), ("Nice", "06000"), ("Rennes", "35000")]
_COULEURS = ["Noir", "Blanc", "Bleu", "Vert", "Rouge", "Violet", "Minuit"]
_PLATEFORMES = ["leboncoin", "vinted", "ebay"]


def _prix_bruite(ref: float, amplitude: float = 0.15) -> float:
    """Applique un bruit aléatoire à un prix de référence."""
    return round(ref * (1 + random.uniform(-amplitude, amplitude)), 0)


def _construire_annonce(plateforme: str, pid: str, modele: str, stockage: str,
                        casse: bool) -> dict:
    """Construit une annonce normalisée (cassée ou fonctionnelle) prête à insérer."""
    ref = next((p for m, s, p in _CATALOGUE if m == modele and s == stockage), 300)
    couleur = random.choice(_COULEURS)
    ville, cp = random.choice(_VILLES)

    if casse:
        panne = random.choice(list(_PANNES_DECOTE.keys()))
        prix = _prix_bruite(ref * _PANNES_DECOTE[panne], 0.2)
        icloud = " bloqué iCloud" if random.random() < 0.12 else ""
        titre = f"{modele} {stockage} {couleur} - {_TEXTE_PANNE[panne]}{icloud}"
    else:
        prix = _prix_bruite(ref, 0.12)
        titre = f"{modele} {stockage} {couleur} très bon état, fonctionnel"

    analyse = analyser_texte(titre)
    # On force le modèle/stockage du catalogue (le parser sert à panne/état/icloud).
    return {
        "plateforme": plateforme,
        "plateforme_id": pid,
        "url": f"https://exemple-{plateforme}.fr/annonce/{pid}",
        "titre": titre,
        "modele": modele,
        "stockage": stockage,
        "couleur": couleur,
        "etat": analyse["etat"],
        "panne": analyse["panne"],
        "prix": float(max(20, prix)),
        "ville": ville,
        "code_postal": cp,
        "description": titre,
        "date_publication": maintenant_iso(),
        "icloud_detecte": analyse["icloud_detecte"],
    }


async def _inserer_direct(a: dict, premiere: datetime, active: int,
                          disparition: datetime | None = None) -> None:
    """Insère une annonce de démo avec des dates passées (bypass upsert)."""
    rotation = None
    derniere = premiere
    if disparition is not None:
        rotation = round((disparition - premiere).total_seconds() / 3600.0, 1)
        derniere = disparition
    now = maintenant_iso()
    await execute(
        """INSERT OR IGNORE INTO annonces (
               plateforme, plateforme_id, url, titre, modele, stockage, couleur,
               etat, panne, prix, ville, code_postal, description, date_publication,
               premiere_detection, derniere_detection, active, date_disparition,
               temps_rotation_heures, icloud_detecte, created_at, updated_at
           ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            a["plateforme"], a["plateforme_id"], a["url"], a["titre"], a["modele"],
            a["stockage"], a["couleur"], a["etat"], a["panne"], a["prix"], a["ville"],
            a["code_postal"], a["description"], premiere.isoformat(),
            premiere.isoformat(), derniere.isoformat(), active,
            disparition.isoformat() if disparition else None, rotation,
            a["icloud_detecte"], now, now,
        ),
    )


async def amorcer_si_vide() -> int:
    """
    Remplit la base avec un jeu de démonstration si elle est vide.
    Crée des annonces actives + des annonces déjà vendues (dates passées) pour
    alimenter les délais de rotation et les tendances de prix. Idempotent.
    """
    deja = await fetch_one("SELECT COUNT(*) AS n FROM annonces")
    if deja and deja["n"] > 0:
        return 0

    now = datetime.now(timezone.utc)
    compteur = 0

    # 1) Annonces VENDUES dans le passé (pour les délais de vente et tendances).
    for i in range(45):
        modele, stockage, _ = random.choice(_CATALOGUE)
        plateforme = random.choice(_PLATEFORMES)
        casse = random.random() < 0.45
        a = _construire_annonce(plateforme, f"seed-vendu-{i}", modele, stockage, casse)
        jours_avant = random.randint(2, 45)
        premiere = now - timedelta(days=jours_avant, hours=random.randint(0, 23))
        rotation_h = random.uniform(24, 24 * 18)  # 1 à 18 jours de rotation
        disparition = premiere + timedelta(hours=rotation_h)
        if disparition > now:
            disparition = now - timedelta(hours=2)
        await _inserer_direct(a, premiere, active=0, disparition=disparition)
        compteur += 1

    # 2) Annonces ACTIVES actuelles (mix cassé / fonctionnel).
    for i in range(40):
        modele, stockage, _ = random.choice(_CATALOGUE)
        plateforme = random.choice(_PLATEFORMES)
        casse = random.random() < 0.5
        a = _construire_annonce(plateforme, f"seed-actif-{i}", modele, stockage, casse)
        premiere = now - timedelta(hours=random.randint(1, 24 * 6))
        await _inserer_direct(a, premiere, active=1)
        compteur += 1

    log.info(f"Données de démonstration générées : {compteur} annonces.")
    return compteur


async def generer_scan(nb: int = 10) -> list[dict]:
    """
    Génère quelques nouvelles annonces actives pour simuler un scan live.
    Renvoie des dicts normalisés (passés ensuite par upsert_annonce).
    """
    annonces = []
    for _ in range(nb):
        modele, stockage, _ = random.choice(_CATALOGUE)
        plateforme = random.choice(_PLATEFORMES)
        casse = random.random() < 0.5
        # Identifiant tournant pour faire réapparaître/rafraîchir des annonces.
        pid = f"sim-{plateforme}-{random.randint(1, 120)}"
        annonces.append(_construire_annonce(plateforme, pid, modele, stockage, casse))
    return annonces
