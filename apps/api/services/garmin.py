"""Copy GarminDB activities from SQLite into PostgreSQL."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sqlite3
from pathlib import Path

try:
    from ..schemas.activity import GarminSyncProgress
except ImportError:
    from schemas.activity import GarminSyncProgress

lazy from fastapi import HTTPException
lazy from psycopg import Error as PsycopgError
lazy from psycopg.types.json import Jsonb
lazy from psycopg_pool import PoolClosed, PoolTimeout

BATCH_SIZE = 1000
logger = logging.getLogger(__name__)
_garmindb_sync_lock = asyncio.Lock()
_sync_progress = GarminSyncProgress()


def get_sync_progress() -> GarminSyncProgress:
    """Return a snapshot without exposing upstream logs or credentials."""
    return _sync_progress.model_copy()


def _open_activities(
    database_path: Path,
) -> tuple[sqlite3.Connection, sqlite3.Cursor]:
    """Open a read-only cursor over GarminDB activities."""
    if not database_path.is_file():
        raise FileNotFoundError(database_path)
    connection = sqlite3.connect(
        f"file:{database_path}?mode=ro",
        uri=True,
        check_same_thread=False,
    )
    connection.row_factory = sqlite3.Row
    try:
        return connection, connection.execute("SELECT * FROM activities")
    except sqlite3.Error:
        connection.close()
        raise


def _activity_id(activity: dict[str, object]) -> str:
    """Return the stable identifier used by supported GarminDB schemas."""
    for key in ("activity_id", "id", "activityId"):
        if value := activity.get(key):
            return str(value)
    raise ValueError("GarminDB activity has no activity identifier")


def _postgres_row(activity: sqlite3.Row) -> tuple[str, Jsonb]:
    """Convert one SQLite activity into PostgreSQL parameters."""
    data = dict(activity)
    return _activity_id(data), Jsonb(data)


async def run_garmindb_sync() -> None:
    """Run the repository's incremental GarminDB download and import command."""
    if _garmindb_sync_lock.locked():
        raise HTTPException(status_code=409, detail="Garmin sync is already running.")
    async with _garmindb_sync_lock:
        global _sync_progress
        _sync_progress = GarminSyncProgress(phase="checking")
        root = Path(__file__).parents[3]
        try:
            process = await asyncio.create_subprocess_exec(
                "make",
                "garmin-sync",
                cwd=root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
        except OSError as error:
            _sync_progress.phase = "failed"
            raise HTTPException(
                status_code=503, detail="Garmin sync could not be started."
            ) from error
        output = ""

        async def read_output() -> None:
            nonlocal output
            global _sync_progress
            assert process.stdout is not None
            while line := await process.stdout.readline():
                decoded = line.decode(errors="replace")
                output = (output + decoded)[-2000:]
                if "garmin-progress: " in decoded:
                    payload = decoded.split("garmin-progress: ", 1)[1]
                    try:
                        progress = GarminSyncProgress.model_validate(json.loads(payload))
                        if (
                            progress.phase in {"downloading", "importing"}
                            and progress.total_files is not None
                            and progress.downloaded_files <= progress.total_files
                        ):
                            _sync_progress = progress
                    except ValueError:
                        pass
            await process.wait()

        try:
            await asyncio.wait_for(read_output(), timeout=600)
        except TimeoutError as error:
            process.kill()
            await process.communicate()
            _sync_progress.phase = "failed"
            raise HTTPException(
                status_code=504, detail="Garmin sync timed out."
            ) from error
        if process.returncode:
            _sync_progress.phase = "failed"
            logger.error(
                "GarminDB command failed: %s", output
            )
            raise HTTPException(status_code=502, detail="Garmin sync failed.")
        _sync_progress.phase = "complete"


async def sync_activities() -> int:
    """Upsert all configured GarminDB activities into PostgreSQL."""
    try:
        from ..database import pool
    except ImportError:
        from database import pool

    configured_path = os.getenv("GARMINDB_PATH")
    if not configured_path:
        logger.error("GarminDB sync rejected: GARMINDB_PATH is not configured")
        raise HTTPException(status_code=500, detail="GARMINDB_PATH is not configured.")
    source_connection = None
    synced = 0
    batch = 0
    phase = "opening GarminDB"
    try:
        source_connection, source_cursor = await asyncio.to_thread(
            _open_activities, Path(configured_path).expanduser()
        )
        phase = "connecting to PostgreSQL"
        async with pool.connection() as connection, connection.cursor() as cursor:
            phase = "creating the PostgreSQL table"
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS garmin_activities (
                    activity_id text PRIMARY KEY,
                    data jsonb NOT NULL,
                    synced_at timestamptz NOT NULL DEFAULT now()
                )
                """
            )
            phase = "reading GarminDB"
            while activities := await asyncio.to_thread(
                source_cursor.fetchmany, BATCH_SIZE
            ):
                batch += 1
                phase = f"preparing batch {batch}"
                rows = [_postgres_row(activity) for activity in activities]
                phase = f"writing batch {batch} to PostgreSQL"
                await cursor.executemany(
                    """
                    INSERT INTO garmin_activities (activity_id, data)
                    VALUES (%s, %s)
                    ON CONFLICT (activity_id) DO UPDATE
                    SET data = EXCLUDED.data, synced_at = now()
                    WHERE garmin_activities.data IS DISTINCT FROM EXCLUDED.data
                    """,
                    rows,
                )
                synced += len(rows)
                logger.debug(
                    "GarminDB sync batch complete: batch=%d rows=%d synced=%d",
                    batch,
                    len(rows),
                    synced,
                )
                phase = "reading GarminDB"
    except (FileNotFoundError, sqlite3.Error, ValueError) as error:
        logger.exception(
            "GarminDB sync source failure: phase=%s batch=%d synced=%d path=%s",
            phase,
            batch,
            synced,
            configured_path,
        )
        raise HTTPException(
            status_code=422,
            detail=f"GarminDB sync failed while {phase}: {error}",
        ) from error
    except (PsycopgError, PoolClosed, PoolTimeout) as error:
        logger.exception(
            "GarminDB sync PostgreSQL failure: phase=%s batch=%d synced=%d",
            phase,
            batch,
            synced,
        )
        raise HTTPException(
            status_code=503,
            detail=f"PostgreSQL is unavailable while {phase}.",
        ) from error
    finally:
        if source_connection is not None:
            await asyncio.to_thread(source_connection.close)
    logger.info("GarminDB sync complete: batches=%d synced=%d", batch, synced)
    return synced
