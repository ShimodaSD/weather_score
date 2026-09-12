"""Visualization-ready Garmin activity endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg.rows import dict_row
from weather_score.application.running_predictions import calculate_running_predictions

try:
    from ..schemas.activity import (
        ActivityDetailResponse,
        ActivityIndexResponse,
        ActivityResponse,
        RunningPredictionsResponse,
    )
    from ..security import require_access_token
    from .connections.database import garmin_pool
except ImportError:
    from routes.connections.database import garmin_pool
    from schemas.activity import (
        ActivityDetailResponse,
        ActivityIndexResponse,
        ActivityResponse,
        RunningPredictionsResponse,
    )
    from security import require_access_token

router = APIRouter(
    prefix="/activities",
    tags=["Activities"],
    dependencies=[Depends(require_access_token)],
)

ACTIVITY_SELECT = """
    SELECT
        a.activity_id::text AS activity_id,
        a.sport AS activity_type,
        a.name,
        a.start_time AS started_at,
        EXTRACT(EPOCH FROM a.elapsed_time)::double precision AS elapsed_seconds,
        EXTRACT(EPOCH FROM a.moving_time)::double precision AS moving_seconds,
        a.distance AS distance_km,
        ROUND(
            (EXTRACT(EPOCH FROM a.moving_time) / NULLIF(a.distance, 0))::numeric,
            2
        )::double precision AS average_pace_seconds_per_km,
        ROUND(
            (a.distance * 3600 / NULLIF(EXTRACT(EPOCH FROM a.moving_time), 0))::numeric,
            2
        )::double precision AS average_speed_kph,
        a.avg_hr AS average_heart_rate_bpm,
        a.max_hr AS maximum_heart_rate_bpm,
        a.calories,
        COALESCE(sa.avg_steps_per_min, a.avg_cadence)::double precision
            AS average_cadence_per_minute,
        a.ascent AS elevation_gain_m,
        a.descent AS elevation_loss_m,
        a.avg_temperature AS average_temperature_c,
        a.training_effect,
        a.anaerobic_training_effect
    FROM garmin_activities.activities AS a
    LEFT JOIN garmin_activities.steps_activities AS sa
        ON sa.activity_id = a.activity_id
"""


async def fetch_activity_index() -> list[dict[str, object]]:
    """Return every activity identifier and label without loading summary joins."""
    async with (
        garmin_pool.connection() as connection,
        connection.cursor(row_factory=dict_row) as cursor,
    ):
        await cursor.execute(
            "SELECT activity_id::text AS activity_id, start_time AS started_at, "
            "sport AS activity_type, name FROM garmin_activities.activities "
            "ORDER BY start_time DESC, activity_id DESC"
        )
        return await cursor.fetchall()


async def fetch_running_prediction_inputs() -> list[dict[str, object]]:
    """Read only distance and moving time needed for running projections."""
    async with (
        garmin_pool.connection() as connection,
        connection.cursor(row_factory=dict_row) as cursor,
    ):
        await cursor.execute(
            "SELECT activity_id::text AS activity_id, start_time AS started_at, "
            "distance::double precision AS distance_km, "
            "EXTRACT(EPOCH FROM moving_time)::double precision AS moving_seconds "
            "FROM garmin_activities.activities WHERE sport = 'running' "
            "AND distance >= 3 AND moving_time > interval '0 seconds'"
        )
        return await cursor.fetchall()


async def fetch_activities(
    activity_type: str | None, limit: int, offset: int
) -> list[dict[str, object]]:
    """Return recent activities ready for charts and summary cards."""
    query = f"""
        {ACTIVITY_SELECT}
        WHERE (%s::text IS NULL OR a.sport = %s)
        ORDER BY a.start_time DESC, a.activity_id DESC
        LIMIT %s OFFSET %s
    """
    async with (
        garmin_pool.connection() as connection,
        connection.cursor(row_factory=dict_row) as cursor,
    ):
        await cursor.execute(query, (activity_type, activity_type, limit, offset))
        return await cursor.fetchall()


async def fetch_activity_summary(activity_id: str) -> dict[str, object] | None:
    """Return the summary fields for one activity without loading its records."""
    async with (
        garmin_pool.connection() as connection,
        connection.cursor(row_factory=dict_row) as cursor,
    ):
        await cursor.execute(
            f"{ACTIVITY_SELECT} WHERE a.activity_id = %s", (activity_id,)
        )
        return await cursor.fetchone()


async def fetch_activity(activity_id: str) -> dict[str, object] | None:
    """Return one activity and its directly related GarminDB rows."""
    query = f"{ACTIVITY_SELECT} WHERE a.activity_id = %s"
    async with (
        garmin_pool.connection() as connection,
        connection.cursor(row_factory=dict_row) as cursor,
    ):
        await cursor.execute(query, (activity_id,))
        activity = await cursor.fetchone()
        if activity is None:
            return None

        for field, table in (
            ("activity", "activities"),
            ("steps_activity", "steps_activities"),
            ("cycle_activity", "cycle_activities"),
            ("climbing_activity", "climbing_activities"),
            ("paddle_activity", "paddle_activities"),
        ):
            await cursor.execute(
                f"SELECT * FROM garmin_activities.{table} WHERE activity_id = %s",
                (activity_id,),
            )
            activity[field] = await cursor.fetchone()

        for field, table, order_by in (
            ("laps", "activity_laps", "lap"),
            ("splits", "activity_splits", "split"),
            ("records", "activity_records", "record"),
            ("activity_devices", "activities_devices", "device_serial_number"),
        ):
            await cursor.execute(
                f"SELECT * FROM garmin_activities.{table} "
                f"WHERE activity_id = %s ORDER BY {order_by}",
                (activity_id,),
            )
            activity[field] = await cursor.fetchall()

        await cursor.execute(
            "SELECT d.* FROM garmin.devices AS d "
            "JOIN garmin_activities.activities_devices AS ad "
            "ON ad.device_serial_number = d.serial_number "
            "WHERE ad.activity_id = %s ORDER BY d.serial_number",
            (activity_id,),
        )
        activity["devices"] = await cursor.fetchall()

        await cursor.execute(
            "SELECT * FROM garmin.device_info WHERE file_id = %s "
            "ORDER BY timestamp",
            (activity_id,),
        )
        activity["device_info"] = await cursor.fetchall()

        await cursor.execute(
            "SELECT * FROM garmin.files WHERE id = %s",
            (activity_id,),
        )
        activity["files"] = await cursor.fetchall()
        return activity


@router.get("", response_model=list[ActivityResponse], summary="List activities")
async def list_activities(
    activity_type: Annotated[str | None, Query(min_length=1, max_length=50)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[dict[str, object]]:
    """List recent activities, optionally filtered by activity type."""
    return await fetch_activities(activity_type, limit, offset)


@router.get("/index", response_model=list[ActivityIndexResponse], summary="List activity IDs")
async def list_activity_index() -> list[dict[str, object]]:
    """List all activity IDs and timestamps for dashboard selection."""
    return await fetch_activity_index()


@router.get(
    "/running/predictions",
    response_model=RunningPredictionsResponse,
    summary="Predict running times",
)
async def get_running_predictions() -> dict[str, object]:
    """Predict 5, 10, 21, and 42 km moving times from recorded runs."""
    return calculate_running_predictions(await fetch_running_prediction_inputs())


@router.get(
    "/{activity_id}/summary",
    response_model=ActivityResponse,
    summary="Get an activity summary",
)
async def get_activity_summary(activity_id: str) -> dict[str, object]:
    """Return only the main statistics for one activity."""
    activity = await fetch_activity_summary(activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found.")
    return activity


@router.get(
    "/{activity_id}",
    response_model=ActivityDetailResponse,
    summary="Get an activity",
)
async def get_activity(activity_id: str) -> dict[str, object]:
    """Return one activity and every directly related stored data point."""
    activity = await fetch_activity(activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found.")
    return activity
