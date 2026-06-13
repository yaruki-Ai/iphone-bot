"""
scheduler.py — Planification des tâches automatiques (APScheduler async).

Tâches :
  - Scan complet toutes les SCAN_INTERVAL_MINUTES (défaut 12 min)
  - Vérification des annonces actives toutes les 24h (rotation = vendu)
  - Rapport Discord tous les soirs à 20h00
Le scheduler est démarré/arrêté par le cycle de vie de l'application FastAPI.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from backend.backup import creer_sauvegarde
from backend.config import settings
from backend.logger import log
from backend.scraper.runner import (
    generer_rapport_quotidien,
    scan_complet,
    verifier_annonces_actives,
)

# Instance unique de scheduler partagée par l'application.
scheduler = AsyncIOScheduler(timezone="Europe/Paris")


async def _job_scan() -> None:
    """Job périodique : lance un scan complet en capturant toute exception."""
    try:
        await scan_complet()
    except Exception as exc:  # un job ne doit jamais tuer le scheduler
        log.error(f"Job scan en erreur : {exc}")


async def _job_verification() -> None:
    """Job quotidien : vérifie les annonces encore actives."""
    try:
        await verifier_annonces_actives()
    except Exception as exc:
        log.error(f"Job vérification en erreur : {exc}")


async def _job_rapport() -> None:
    """Job du soir : envoie le rapport Discord à 20h."""
    try:
        await generer_rapport_quotidien()
    except Exception as exc:
        log.error(f"Job rapport en erreur : {exc}")


async def _job_sauvegarde() -> None:
    """Job quotidien : sauvegarde automatique de la base."""
    try:
        creer_sauvegarde()
    except Exception as exc:
        log.error(f"Job sauvegarde en erreur : {exc}")


def demarrer() -> None:
    """Enregistre les jobs et démarre le scheduler (idempotent)."""
    if scheduler.running:
        return

    scheduler.add_job(
        _job_scan,
        IntervalTrigger(minutes=settings.SCAN_INTERVAL_MINUTES),
        id="scan", replace_existing=True, max_instances=1, coalesce=True,
    )
    scheduler.add_job(
        _job_verification,
        IntervalTrigger(hours=24),
        id="verification", replace_existing=True, max_instances=1, coalesce=True,
    )
    scheduler.add_job(
        _job_rapport,
        CronTrigger(hour=20, minute=0),
        id="rapport", replace_existing=True, max_instances=1, coalesce=True,
    )
    scheduler.add_job(
        _job_sauvegarde,
        CronTrigger(hour=3, minute=0),
        id="sauvegarde", replace_existing=True, max_instances=1, coalesce=True,
    )
    scheduler.start()
    log.info(
        f"Scheduler démarré : scan/{settings.SCAN_INTERVAL_MINUTES}min, "
        f"vérif/24h, rapport 20h00."
    )


def arreter() -> None:
    """Arrête proprement le scheduler à la fermeture de l'application."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        log.info("Scheduler arrêté.")
