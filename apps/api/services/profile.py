"""Persist the configured account's athlete profile."""

from psycopg.rows import dict_row

try:
    from ..database import pool
except ImportError:
    from database import pool


CREATE_PROFILE = """
    CREATE TABLE IF NOT EXISTS athlete_profile (
        id smallint PRIMARY KEY DEFAULT 1 CHECK (id = 1),
        name text CHECK (name IS NULL OR (length(trim(name)) BETWEEN 1 AND 100)),
        threshold_heart_rate_bpm smallint NOT NULL DEFAULT 157
            CHECK (threshold_heart_rate_bpm BETWEEN 30 AND 250),
        updated_at timestamptz NOT NULL DEFAULT now()
    )
"""


async def fetch_profile() -> dict[str, object]:
    """Read the single athlete profile, initializing the default if needed."""
    async with (
        pool.connection() as connection,
        connection.cursor(row_factory=dict_row) as cursor,
    ):
        await cursor.execute(CREATE_PROFILE)
        await cursor.execute(
            "INSERT INTO athlete_profile (id) VALUES (1) ON CONFLICT (id) DO NOTHING"
        )
        await cursor.execute(
            "SELECT name, threshold_heart_rate_bpm FROM athlete_profile WHERE id = 1"
        )
        return await cursor.fetchone()


async def save_profile(name: str, threshold_heart_rate_bpm: int) -> dict[str, object]:
    """Atomically save both profile fields for the configured account."""
    async with (
        pool.connection() as connection,
        connection.cursor(row_factory=dict_row) as cursor,
    ):
        await cursor.execute(CREATE_PROFILE)
        await cursor.execute(
            """
            INSERT INTO athlete_profile (id, name, threshold_heart_rate_bpm)
            VALUES (1, %s, %s)
            ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name,
                threshold_heart_rate_bpm = EXCLUDED.threshold_heart_rate_bpm,
                updated_at = now()
            RETURNING name, threshold_heart_rate_bpm
            """,
            (name, threshold_heart_rate_bpm),
        )
        return await cursor.fetchone()
