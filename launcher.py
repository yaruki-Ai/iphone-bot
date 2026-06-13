"""
launcher.py — Point d'entrée du programme packagé en .exe (PyInstaller).

Démarre le serveur FastAPI (qui sert l'API + le frontend buildé) et ouvre
automatiquement le navigateur sur le dashboard. Le double-clic sur l'exécutable
lance tout : aucune installation requise côté client.
"""

import sys

import uvicorn

from backend.config import settings
from backend.logger import log
from backend.main import app


def main() -> None:
    """Lance le serveur sur l'hôte/port configurés."""
    log.info("=== iPhone Arbitrage Bot ===")
    log.info(f"Dashboard : http://{settings.APP_HOST}:{settings.APP_PORT}")
    log.info("Fermez cette fenêtre pour arrêter le bot.")
    try:
        uvicorn.run(app, host=settings.APP_HOST, port=settings.APP_PORT, log_level="info")
    except KeyboardInterrupt:
        log.info("Arrêt demandé par l'utilisateur.")
        sys.exit(0)


if __name__ == "__main__":
    main()
