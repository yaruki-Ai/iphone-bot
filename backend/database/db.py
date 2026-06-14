"""
db.py — Couche d'accès à la base SQLite (asynchrone via aiosqlite).

Fournit l'initialisation du schéma et des helpers génériques (fetch_all,
fetch_one, execute, executemany). Chaque appel ouvre puis ferme une connexion :
simple et sûr pour un usage solo, avec le mode WAL pour les lecteurs concurrents.
"""

from datetime import datetime, timezone
from typing import Any, Optional

import aiosqlite

from backend.config import settings
from backend.logger import log


def maintenant_iso() -> str:
    """Retourne l'horodatage courant en ISO 8601 (UTC), utilisé partout."""
    return datetime.now(timezone.utc).isoformat()


async def _ouvrir() -> aiosqlite.Connection:
    """Ouvre une connexion configurée (Row factory + clés étrangères + anti-verrou)."""
    conn = await aiosqlite.connect(settings.CHEMIN_DB)
    conn.row_factory = aiosqlite.Row
    # busy_timeout : si la base est verrouillée par un autre writer (scheduler +
    # API + jobs concurrents), SQLite réessaie pendant 5 s au lieu d'échouer
    # immédiatement sur "database is locked". Indispensable vu l'accès concurrent.
    await conn.execute("PRAGMA busy_timeout = 5000;")
    await conn.execute("PRAGMA foreign_keys = ON;")
    return conn


async def init_db() -> None:
    """Crée la base et toutes les tables à partir de schema.sql (idempotent)."""
    try:
        schema_sql = settings.CHEMIN_SCHEMA.read_text(encoding="utf-8")
    except OSError as exc:
        log.error(f"Impossible de lire le schéma SQL : {exc}")
        raise

    try:
        async with aiosqlite.connect(settings.CHEMIN_DB) as conn:
            await conn.executescript(schema_sql)
            # Migration douce : ajoute les colonnes manquantes aux bases existantes.
            for colonne, definition in (("batterie_pct", "INTEGER"),):
                try:
                    await conn.execute(f"ALTER TABLE annonces ADD COLUMN {colonne} {definition}")
                except aiosqlite.Error:
                    pass  # colonne déjà présente
            await conn.commit()
        log.info(f"Base SQLite initialisée : {settings.CHEMIN_DB}")
    except aiosqlite.Error as exc:
        log.error(f"Erreur d'initialisation de la base : {exc}")
        raise


async def fetch_all(query: str, params: tuple = ()) -> list[dict[str, Any]]:
    """Exécute une requête SELECT et retourne une liste de dictionnaires."""
    try:
        conn = await _ouvrir()
        try:
            async with conn.execute(query, params) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]
        finally:
            await conn.close()
    except aiosqlite.Error as exc:
        log.error(f"fetch_all a échoué : {exc} | requête : {query[:120]}")
        return []


async def fetch_one(query: str, params: tuple = ()) -> Optional[dict[str, Any]]:
    """Exécute une requête SELECT et retourne la première ligne (ou None)."""
    try:
        conn = await _ouvrir()
        try:
            async with conn.execute(query, params) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None
        finally:
            await conn.close()
    except aiosqlite.Error as exc:
        log.error(f"fetch_one a échoué : {exc} | requête : {query[:120]}")
        return None


async def execute(query: str, params: tuple = ()) -> Optional[int]:
    """Exécute INSERT/UPDATE/DELETE et retourne le lastrowid (ou None si échec)."""
    try:
        conn = await _ouvrir()
        try:
            cur = await conn.execute(query, params)
            await conn.commit()
            return cur.lastrowid
        finally:
            await conn.close()
    except aiosqlite.Error as exc:
        log.error(f"execute a échoué : {exc} | requête : {query[:120]}")
        return None


async def executemany(query: str, seq_params: list[tuple]) -> int:
    """Exécute une requête en lot ; retourne le nombre de lignes traitées."""
    if not seq_params:
        return 0
    try:
        conn = await _ouvrir()
        try:
            await conn.executemany(query, seq_params)
            await conn.commit()
            return len(seq_params)
        finally:
            await conn.close()
    except aiosqlite.Error as exc:
        log.error(f"executemany a échoué : {exc} | requête : {query[:120]}")
        return 0
