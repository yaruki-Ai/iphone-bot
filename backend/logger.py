"""
logger.py — Configuration centralisée des logs avec loguru.

Tous les modules importent `log` depuis ce fichier. Les logs partent à la fois
vers la console et vers un fichier tournant dans /logs/ (rotation + rétention).
"""

import sys

from loguru import logger as log

from backend.config import settings

# On retire le handler par défaut pour tout reconfigurer proprement.
log.remove()

# Sortie console (lisible, colorée).
log.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | "
    "<cyan>{name}</cyan> - <level>{message}</level>",
    colorize=True,
)

# Sortie fichier (rotation à 10 Mo, conservation 14 jours, compression).
log.add(
    settings.DOSSIER_LOGS / "bot_{time:YYYY-MM-DD}.log",
    level="DEBUG",
    rotation="10 MB",
    retention="14 days",
    compression="zip",
    encoding="utf-8",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
)

__all__ = ["log"]
