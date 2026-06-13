"""
backup.py — Sauvegarde automatique de la base de données locale.

Protège les données du client (stock, historique, prédictions) contre une
corruption ou une fausse manip. Crée une copie horodatée et cohérente de la
base (via l'API backup de SQLite, sûre même en mode WAL) dans data/backups/,
et ne conserve que les N dernières.

Appelée au démarrage de l'application et une fois par jour par le scheduler.
"""

import sqlite3
from datetime import datetime

from backend.config import settings
from backend.logger import log

NB_SAUVEGARDES_GARDEES = 10


def creer_sauvegarde() -> str | None:
    """
    Crée une sauvegarde horodatée de la base et purge les plus anciennes.
    Retourne le chemin de la sauvegarde créée (ou None si rien à sauvegarder).
    """
    if not settings.CHEMIN_DB.exists():
        return None

    dossier = settings.DOSSIER_DATA / "backups"
    dossier.mkdir(parents=True, exist_ok=True)
    horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = dossier / f"iphone_arbitrage_{horodatage}.db"

    try:
        # API backup de SQLite : copie cohérente même si la base est en cours d'usage.
        source = sqlite3.connect(str(settings.CHEMIN_DB))
        cible = sqlite3.connect(str(destination))
        with cible:
            source.backup(cible)
        cible.close()
        source.close()
    except sqlite3.Error as exc:
        log.error(f"Sauvegarde impossible : {exc}")
        return None

    # Purge : on ne garde que les N plus récentes.
    sauvegardes = sorted(dossier.glob("iphone_arbitrage_*.db"))
    for ancienne in sauvegardes[:-NB_SAUVEGARDES_GARDEES]:
        try:
            ancienne.unlink()
        except OSError:
            pass

    log.info(f"Sauvegarde créée : {destination.name}")
    return str(destination)
