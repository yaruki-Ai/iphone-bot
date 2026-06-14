"""
config.py — Chargement centralisé de la configuration du bot.

Lit les variables d'environnement depuis le fichier .env (via python-dotenv),
expose un objet `settings` unique utilisé par tout le backend, et calcule les
chemins importants (base SQLite, logs, build du frontend). Gère aussi le cas
PyInstaller (chemins figés dans l'exécutable).
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def _racine_projet() -> Path:
    """Retourne la racine du projet, que l'on tourne en script ou en .exe PyInstaller."""
    if getattr(sys, "frozen", False):
        # Cas exécutable PyInstaller : tout est extrait dans sys._MEIPASS.
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    # Cas développement : racine = dossier parent de /backend.
    return Path(__file__).resolve().parent.parent


RACINE = _racine_projet()

# En mode .exe, on garde la base et les logs À CÔTÉ de l'exécutable (persistants),
# pas dans le dossier temporaire _MEIPASS qui est effacé à la fermeture.
if getattr(sys, "frozen", False):
    RACINE_DONNEES = Path(sys.executable).resolve().parent
else:
    RACINE_DONNEES = RACINE

# Chargement du .env (cherché à côté de l'exe en priorité, sinon racine projet).
for chemin_env in (RACINE_DONNEES / ".env", RACINE / ".env"):
    if chemin_env.exists():
        load_dotenv(chemin_env)
        break


def _bool(valeur: str, defaut: bool = False) -> bool:
    """Convertit une variable d'environnement texte en booléen de façon tolérante."""
    if valeur is None:
        return defaut
    return valeur.strip().lower() in ("1", "true", "yes", "oui", "on")


def _float(valeur: str, defaut: float) -> float:
    """Convertit une variable d'environnement en float avec valeur de repli."""
    try:
        return float(valeur)
    except (TypeError, ValueError):
        return defaut


def _int(valeur: str, defaut: int) -> int:
    """Convertit une variable d'environnement en int avec valeur de repli."""
    try:
        return int(valeur)
    except (TypeError, ValueError):
        return defaut


class Settings:
    """Conteneur de configuration : centralise tous les paramètres du bot."""

    def __init__(self) -> None:
        # --- Chemins ---
        self.RACINE: Path = RACINE
        self.DOSSIER_DATA: Path = RACINE_DONNEES / "data"
        self.DOSSIER_LOGS: Path = RACINE_DONNEES / "logs"
        self.CHEMIN_DB: Path = self.DOSSIER_DATA / "iphone_arbitrage.db"
        self.CHEMIN_SCHEMA: Path = RACINE / "backend" / "database" / "schema.sql"
        self.DOSSIER_FRONT: Path = RACINE / "frontend" / "dist"

        # --- Application ---
        self.APP_HOST: str = os.getenv("APP_HOST", "127.0.0.1")
        self.APP_PORT: int = _int(os.getenv("APP_PORT"), 8000)
        self.SIMULATION_MODE: bool = _bool(os.getenv("SIMULATION_MODE"), True)
        self.SCAN_INTERVAL_MINUTES: int = _int(os.getenv("SCAN_INTERVAL_MINUTES"), 12)
        self.SEUIL_ALERTE_SCORE: int = _int(os.getenv("SEUIL_ALERTE_SCORE"), 70)
        self.MARGE_CIBLE_POURCENT: float = _float(os.getenv("MARGE_CIBLE_POURCENT"), 30.0)
        # Frais de livraison estimés à l'achat (€), inclus dans la marge/ROI.
        self.FRAIS_LIVRAISON: float = _float(os.getenv("FRAIS_LIVRAISON"), 5.0)
        # Alertes Discord immédiates à chaque scan : désactivées par défaut.
        # On privilégie UN récap quotidien (cf. ci-dessous) pour éviter le spam.
        self.ALERTES_IMMEDIATES: bool = _bool(os.getenv("ALERTES_IMMEDIATES"), False)
        # Récap quotidien : score minimum retenu et nombre max d'annonces listées.
        self.SEUIL_RAPPORT: int = _int(os.getenv("SEUIL_RAPPORT"), 50)
        self.RAPPORT_TOP_N: int = _int(os.getenv("RAPPORT_TOP_N"), 15)

        # --- eBay : scraping classique de eBay.fr (aucune clé API requise) ---

        # --- Discord ---
        self.DISCORD_WEBHOOK_ALERTES: str = os.getenv("DISCORD_WEBHOOK_ALERTES", "").strip()
        self.DISCORD_WEBHOOK_RAPPORT: str = os.getenv("DISCORD_WEBHOOK_RAPPORT", "").strip()

        # --- Leboncoin ---
        self.LBC_EMAIL: str = os.getenv("LBC_EMAIL", "").strip()
        self.LBC_PASSWORD: str = os.getenv("LBC_PASSWORD", "").strip()
        # Clé d'une API anti-bot (ScraperAPI/ZenRows…) pour passer DataDome.
        # Si vide : LBC reste bloqué (gratuit). Si renseignée : LBC fonctionne.
        self.LBC_SCRAPER_API_KEY: str = os.getenv("LBC_SCRAPER_API_KEY", "").strip()

        # Création des dossiers nécessaires dès le démarrage.
        self.DOSSIER_DATA.mkdir(parents=True, exist_ok=True)
        self.DOSSIER_LOGS.mkdir(parents=True, exist_ok=True)

    # --- Indicateurs de disponibilité des services (dégradation propre) ---
    @property
    def ebay_actif(self) -> bool:
        """eBay est en scraping classique : toujours disponible (aucune clé requise)."""
        return True

    @property
    def discord_alertes_actif(self) -> bool:
        """Vrai si le webhook Discord des alertes est configuré."""
        return self.DISCORD_WEBHOOK_ALERTES.startswith("http")

    @property
    def discord_rapport_actif(self) -> bool:
        """Vrai si le webhook Discord du rapport est configuré."""
        return self.DISCORD_WEBHOOK_RAPPORT.startswith("http")


# Instance unique partagée par tout le backend.
settings = Settings()
