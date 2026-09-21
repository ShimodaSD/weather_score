"""Asynchronous Garmin route grading and PostgreSQL persistence."""

import asyncio
import logging
from dataclasses import asdict

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from weather_score.application.activity_grade import (
    build_activity_segments,
    calculate_headwind_component,
    calculate_outdoor_wbgt,
)
from weather_score.application.run_grade import calculate_run_grade
from weather_score.weather.providers.weather_api import fetch_historical_conditions

try:
    from ..database import pool
    from ..routes.connections.database import garmin_pool
except ImportError:
    from database import pool
    from routes.connections.database import garmin_pool

logger = logging.getLogger(__name__)

CREATE_ACTIVITY_GRADES = """
    CREATE TABLE IF NOT EXISTS activity_grades (
        activity_id text PRIMARY KEY,
        status text NOT NULL CHECK (status IN ('processing', 'complete', 'failed')),
        score double precision CHECK (score BETWEEN 0 AND 100),
        segments jsonb NOT NULL DEFAULT '[]'::jsonb,
        error text,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        completed_at timestamptz,
        calculation_version integer NOT NULL DEFAULT 4
    )
"""

ALTER_ACTIVITY_GRADES = """
    ALTER TABLE activity_grades
    ADD COLUMN IF NOT EXISTS calculation_version integer NOT NULL DEFAULT 1
"""

UPGRADE_ACTIVITY_GRADES = """
    UPDATE activity_grades SET
        status = 'failed', score = NULL, segments = '[]'::jsonb,
        error = 'Historical wind calculation changed. Regrade this activity.',
        updated_at = now(), completed_at = now(), calculation_version = 4
    WHERE calculation_version < 4
"""


async def queue_activity_grade(activity_id: str) -> dict[str, object]:
    """Create or reset the persisted processing state for an activity."""
    async with (
        pool.connection() as connection,
        connection.cursor(row_factory=dict_row) as cursor,
    ):
        await cursor.execute(CREATE_ACTIVITY_GRADES)
        await cursor.execute(ALTER_ACTIVITY_GRADES)
        await cursor.execute(UPGRADE_ACTIVITY_GRADES)
        await cursor.execute(
            """
            INSERT INTO activity_grades (activity_id, status, calculation_version)
            VALUES (%s, 'processing', 4)
            ON CONFLICT (activity_id) DO UPDATE SET
                status = 'processing', score = NULL, segments = '[]'::jsonb,
                error = NULL, updated_at = now(), completed_at = NULL
                , calculation_version = 4
            RETURNING *
            """,
            (activity_id,),
        )
        return await cursor.fetchone()


async def fetch_activity_grades() -> list[dict[str, object]]:
    """Return persisted activity grades with newest work first."""
    async with (
        pool.connection() as connection,
        connection.cursor(row_factory=dict_row) as cursor,
    ):
        await cursor.execute(CREATE_ACTIVITY_GRADES)
        await cursor.execute(ALTER_ACTIVITY_GRADES)
        await cursor.execute(UPGRADE_ACTIVITY_GRADES)
        await cursor.execute("SELECT * FROM activity_grades ORDER BY updated_at DESC")
        return await cursor.fetchall()


async def process_activity_grade(activity_id: str) -> None:
    """Grade each complete 200 metre route segment and persist the result."""
    try:
        records = await _fetch_activity_records(activity_id)
        segments = build_activity_segments(records)
        semaphore = asyncio.Semaphore(5)

        async def grade_segment(segment):
            async with semaphore:
                conditions = await fetch_historical_conditions(
                    segment.latitude,
                    segment.longitude,
                    segment.recorded_at,
                )
            headwind_kph = calculate_headwind_component(
                conditions.wind_kph,
                conditions.wind_degree,
                segment.route_bearing_degrees,
            )
            wbgt_c = calculate_outdoor_wbgt(
                conditions.temperature_c,
                conditions.humidity_percent,
                conditions.wind_kph,
                conditions.uv_index,
                conditions.cloud_percent,
            )
            grade = calculate_run_grade(
                average_pace_minutes_per_km=segment.pace_minutes_per_km,
                headwind_kph=headwind_kph,
                wet_bulb_globe_temperature_c=wbgt_c,
            )
            data = asdict(segment)
            data["recorded_at"] = segment.recorded_at.isoformat()
            return (
                data
                | asdict(grade)
                | {
                    "gust_kph": conditions.gust_kph,
                    "wind_kph": conditions.wind_kph,
                    "wind_degree": conditions.wind_degree,
                    "headwind_kph": headwind_kph,
                    "temperature_c": conditions.temperature_c,
                    "wbgt_c": wbgt_c,
                    "weather_at": conditions.weather_at.isoformat(),
                }
            )

        grades = await asyncio.gather(*(grade_segment(segment) for segment in segments))
        total_distance = sum(segment["distance_m"] for segment in grades)
        score = round(
            sum(segment["score"] * segment["distance_m"] for segment in grades)
            / total_distance,
            2,
        )
        await _complete_activity_grade(activity_id, score, grades)
    except Exception as error:
        logger.exception("Activity grade failed: activity_id=%s", activity_id)
        await _fail_activity_grade(
            activity_id, str(error)[:500] or "Activity grading failed."
        )


async def _fetch_activity_records(activity_id: str) -> list[dict[str, object]]:
    async with (
        garmin_pool.connection() as connection,
        connection.cursor(row_factory=dict_row) as cursor,
    ):
        await cursor.execute(
            """
            SELECT timestamp, position_lat, position_long, distance
            FROM garmin_activities.activity_records
            WHERE activity_id = %s
            ORDER BY distance, record
            """,
            (activity_id,),
        )
        return await cursor.fetchall()


async def _complete_activity_grade(
    activity_id: str, score: float, segments: list[dict[str, object]]
) -> None:
    async with pool.connection() as connection, connection.cursor() as cursor:
        await cursor.execute(
            """
            UPDATE activity_grades SET status = 'complete', score = %s,
                segments = %s, error = NULL, updated_at = now(), completed_at = now()
            WHERE activity_id = %s
            """,
            (score, Jsonb(segments), activity_id),
        )


async def _fail_activity_grade(activity_id: str, error: str) -> None:
    async with pool.connection() as connection, connection.cursor() as cursor:
        await cursor.execute(
            """
            UPDATE activity_grades SET status = 'failed', score = NULL,
                segments = '[]'::jsonb, error = %s, updated_at = now(), completed_at = now()
            WHERE activity_id = %s
            """,
            (error, activity_id),
        )
