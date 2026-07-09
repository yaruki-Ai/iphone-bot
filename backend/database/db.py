"""
db.py — Couche d'accès à la base (double moteur).

- Si settings.DATABASE_URL est défini  -> PostgreSQL (Supabase), utilisé par le
  cloud (scans + alertes Discord). Vraie base : pas de doublons, pas de "fichier
  dans git" qui gonfle.
- Sinon                                 -> SQLite local (app du client, inchangée).

Même interface dans les deux cas : fetch_all / fetch_one / execute / executemany.
Les requêtes utilisent des '?' ; en mode Postgres ils sont convertis en $1,$2,…
"""

from datetime import datetime, timezone
from typing import Any, Optional

from backend.config import settings
from backend.logger import log

# Mode Postgres si une URL de base est fournie (cloud) ; sinon SQLite (local).
_PG = bool(settings.DATABASE_URL)


def maintenant_iso() -> str:
    """Horodatage courant en ISO 8601 (UTC), utilisé partout."""
    return datetime.now(timezone.utc).isoformat()


# ===========================================================================
#  MODE POSTGRESQL (Supabase) — cloud
# ===========================================================================
if _PG:
    import asyncpg

    _pool: "asyncpg.Pool | None" = None

    def _to_pg(query: str) -> str:
        """Convertit les placeholders '?' (SQLite) en '$1,$2,…' (Postgres)."""
        out, i = [], 0
        for ch in query:
            if ch == "?":
                i += 1
                out.append(f"${i}")
            else:
                out.append(ch)
        return "".join(out)

    async def _get_pool() -> "asyncpg.Pool":
        """Crée (une fois) le pool de connexions Postgres."""
        global _pool
        if _pool is None:
            # statement_cache_size=0 : compatible avec le pooler Supabase (pgbouncer).
            _pool = await asyncpg.create_pool(
                settings.DATABASE_URL, min_size=1, max_size=5, statement_cache_size=0
            )
        return _pool

    async def init_db() -> None:
        """Vérifie la connexion (le schéma est déjà géré côté Supabase)."""
        try:
            pool = await _get_pool()
            async with pool.acquire() as conn:
                await conn.execute("SELECT 1;")
            log.info("Connexion PostgreSQL (Supabase) OK.")
        except Exception as exc:
            log.error(f"Connexion PostgreSQL impossible : {exc}")
            raise

    async def fetch_all(query: str, params: tuple = ()) -> list[dict[str, Any]]:
        """SELECT -> liste de dictionnaires."""
        try:
            pool = await _get_pool()
            rows = await pool.fetch(_to_pg(query), *params)
            return [dict(r) for r in rows]
        except Exception as exc:
            log.error(f"fetch_all (PG) : {exc} | {query[:120]}")
            return []

    async def fetch_one(query: str, params: tuple = ()) -> Optional[dict[str, Any]]:
        """SELECT -> première ligne (dict) ou None."""
        try:
            pool = await _get_pool()
            row = await pool.fetchrow(_to_pg(query), *params)
            return dict(row) if row else None
        except Exception as exc:
            log.error(f"fetch_one (PG) : {exc} | {query[:120]}")
            return None

    async def execute(query: str, params: tuple = ()) -> Optional[int]:
        """INSERT/UPDATE/DELETE. Retourne None (pas de lastrowid en Postgres)."""
        try:
            pool = await _get_pool()
            await pool.execute(_to_pg(query), *params)
            return 0
        except Exception as exc:
            log.error(f"execute (PG) : {exc} | {query[:120]}")
            return None

    async def executemany(query: str, seq_params: list[tuple]) -> int:
        """Exécution en lot."""
        if not seq_params:
            return 0
        try:
            pool = await _get_pool()
            await pool.executemany(_to_pg(query), seq_params)
            return len(seq_params)
        except Exception as exc:
            log.error(f"executemany (PG) : {exc} | {query[:120]}")
            return 0

    async def checkpoint() -> None:
        """Rien à faire en Postgres (pas de WAL local à vider)."""
        return None


# ===========================================================================
#  MODE SQLITE — app locale du client (inchangé)
# ===========================================================================
else:
    import aiosqlite

    async def _ouvrir() -> "aiosqlite.Connection":
        """Ouvre une connexion SQLite configurée (Row + clés étrangères + anti-verrou)."""
        conn = await aiosqlite.connect(settings.CHEMIN_DB)
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA busy_timeout = 5000;")
        await conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    async def init_db() -> None:
        """Crée la base et toutes les tables depuis schema.sql (idempotent)."""
        try:
            schema_sql = settings.CHEMIN_SCHEMA.read_text(encoding="utf-8")
        except OSError as exc:
            log.error(f"Impossible de lire le schéma SQL : {exc}")
            raise
        try:
            async with aiosqlite.connect(settings.CHEMIN_DB) as conn:
                await conn.executescript(schema_sql)
                for colonne, definition in (("batterie_pct", "INTEGER"), ("image_url", "TEXT")):
                    try:
                        await conn.execute(f"ALTER TABLE annonces ADD COLUMN {colonne} {definition}")
                    except aiosqlite.Error:
                        pass
                await conn.commit()
            log.info(f"Base SQLite initialisée : {settings.CHEMIN_DB}")
        except aiosqlite.Error as exc:
            log.error(f"Erreur d'initialisation de la base : {exc}")
            raise

    async def fetch_all(query: str, params: tuple = ()) -> list[dict[str, Any]]:
        """SELECT -> liste de dictionnaires."""
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
        """SELECT -> première ligne (dict) ou None."""
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
        """INSERT/UPDATE/DELETE -> lastrowid (ou None si échec)."""
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
        """Exécution en lot ; retourne le nombre de lignes traitées."""
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

    async def checkpoint() -> None:
        """Vide le WAL SQLite dans le fichier principal (sauvegarde propre)."""
        try:
            conn = await _ouvrir()
            await conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            await conn.close()
        except aiosqlite.Error as exc:
            log.warning(f"Checkpoint WAL impossible : {exc}")
