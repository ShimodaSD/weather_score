"""Import a single decoded activity into the existing PostgreSQL schema."""

from datetime import time, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fitfile import File, conversions
from fitfile.exceptions import FitFileError
from psycopg import sql

from .application.training_stress import calculate_activity_tss
from .fit_activity import decode_fit, decode_fit_sessions
from .fit_integrity import validate_fit
from .fit_multisport import decode_multisport
from .garmin_activity_summary import map_activity_summary


def _insert_many(
    connection: Any, schema: str, table: str, rows: list[dict[str, object]]
) -> None:
    if not rows:
        return
    columns = tuple(rows[0])
    if any(tuple(row) != columns for row in rows):
        raise ValueError("Inconsistent columns in import batch")
    query = sql.SQL("INSERT INTO {}.{} ({}) VALUES ({}) ON CONFLICT DO NOTHING").format(
        sql.Identifier(schema),
        sql.Identifier(table),
        sql.SQL(", ").join(map(sql.Identifier, columns)),
        sql.SQL(", ").join(sql.Placeholder() for _ in columns),
    )
    with connection.cursor() as cursor:
        cursor.executemany(
            query, [tuple(row[column] for column in columns) for row in rows]
        )


def _insert(connection: Any, schema: str, table: str, row: dict[str, object]) -> None:
    _insert_many(connection, schema, table, [row])


def _upsert_many(
    connection: Any,
    schema: str,
    table: str,
    rows: list[dict[str, object]],
    keys: tuple[str, ...],
    updates: tuple[str, ...] | None = None,
) -> None:
    if not rows:
        return
    columns = tuple(rows[0])
    if any(tuple(row) != columns for row in rows):
        raise ValueError("Inconsistent columns in import batch")
    updates = (
        updates if updates is not None else tuple(c for c in columns if c not in keys)
    )
    if not updates:
        _insert_many(connection, schema, table, rows)
        return
    query = sql.SQL(
        "INSERT INTO {}.{} AS current ({}) VALUES ({}) ON CONFLICT ({}) DO UPDATE SET {}"
    ).format(
        sql.Identifier(schema),
        sql.Identifier(table),
        sql.SQL(", ").join(map(sql.Identifier, columns)),
        sql.SQL(", ").join(sql.Placeholder() for _ in columns),
        sql.SQL(", ").join(map(sql.Identifier, keys)),
        sql.SQL(", ").join(
            sql.SQL("{} = COALESCE(EXCLUDED.{}, current.{})").format(
                *([sql.Identifier(column)] * 3)
            )
            for column in updates
        ),
    )
    with connection.cursor() as cursor:
        cursor.executemany(
            query, [tuple(row[column] for column in columns) for row in rows]
        )


def _upsert(
    connection: Any,
    schema: str,
    table: str,
    row: dict[str, object],
    keys: tuple[str, ...],
    updates: tuple[str, ...] | None = None,
) -> None:
    _upsert_many(connection, schema, table, [row], keys, updates)


def _upsert_device(connection: Any, row: dict[str, object]) -> None:
    columns = tuple(row)
    updates = [column for column in columns if column != "serial_number"]
    query = sql.SQL(
        "INSERT INTO garmin.devices AS current ({}) VALUES ({}) ON CONFLICT (serial_number) DO UPDATE SET {} WHERE current.timestamp IS NULL OR EXCLUDED.timestamp >= current.timestamp"
    ).format(
        sql.SQL(", ").join(map(sql.Identifier, columns)),
        sql.SQL(", ").join(sql.Placeholder() for _ in columns),
        sql.SQL(", ").join(
            sql.SQL("{} = COALESCE(EXCLUDED.{}, current.{})").format(
                *([sql.Identifier(column)] * 3)
            )
            for column in updates
        ),
    )
    connection.execute(query, tuple(row[column] for column in columns))


def _name(value: Any) -> str | None:
    if value is None:
        return None
    name = getattr(value, "name", value)
    return str(name)


def _local_time(fit: File, value: Any) -> Any:
    return fit.utc_datetime_to_local(value) if value is not None else None


def _invalidate_changed_grade(
    connection: Any, activity_id: str, records: list[dict[str, object]]
) -> None:
    connection.execute(
        "SELECT pg_advisory_xact_lock(hashtextextended('weather-grade:' || %s, 0))",
        (activity_id,),
    )
    previous = {
        row[0]: row[1:]
        for row in connection.execute(
            "SELECT record, timestamp, position_lat, position_long, distance "
            "FROM garmin_activities.activity_records WHERE activity_id = %s",
            (activity_id,),
        ).fetchall()
    }
    fields = ("timestamp", "position_lat", "position_long", "distance")
    changed = any(
        record["record"] not in previous
        or any(
            record.get(field) is not None and record[field] != old
            for field, old in zip(fields, previous[record["record"]], strict=True)
        )
        for record in records
    )
    if not changed:
        return
    if not connection.execute(
        "SELECT to_regclass('public.activity_grades')"
    ).fetchone()[0]:
        raise ValueError("Cannot safely update route records without grade storage")
    grade = connection.execute(
        "SELECT status FROM public.activity_grades WHERE activity_id = %s FOR UPDATE",
        (activity_id,),
    ).fetchone()
    if grade and grade[0] == "processing":
        raise ValueError(
            "Cannot update route records while the activity is being graded"
        )
    if grade:
        connection.execute(
            "UPDATE public.activity_grades SET status = 'failed', score = NULL, "
            "segments = '[]'::jsonb, error = 'Activity route changed. Regrade this activity.', "
            "updated_at = now(), completed_at = now() WHERE activity_id = %s",
            (activity_id,),
        )


def _apply_zones(
    fit: File, activity: dict[str, object], laps: list[dict[str, object]]
) -> None:
    for message in fit.hr_zones_timer:
        fields = message.fields
        kind = _name(fields.get("hr_zones_timer_type"))
        if kind == "session":
            target = activity
        elif kind == "lap":
            index = fields.get("record_num")
            if not isinstance(index, int) or not 0 <= index < len(laps):
                raise ValueError("Heart-rate zone data refers to an unknown lap")
            target = laps[index]
        else:
            continue
        times = fields.get("hr_zones_time")
        if not isinstance(times, list) or len(times) < 6:
            raise ValueError("Incomplete heart-rate zone data")
        target["hr_zones_method"] = _name(fields.get("hr_zones_method"))
        for zone in range(1, 6):
            if times[zone] is not None:
                target[f"hrz_{zone}_time"] = times[zone]
        limits = fields.get("hr_zones")
        if limits:
            if len(limits) < 5:
                raise ValueError("Incomplete heart-rate zone thresholds")
            for zone in range(1, 6):
                target[f"hrz_{zone}_hr"] = limits[zone - 1]


def _devices(
    fit: File, activity_id: str
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    file_fields = fit.file_id[0].fields
    main_serial = file_fields.get("serial_number") or None
    main_manufacturer = _name(file_fields.get("manufacturer"))
    main_product = _name(file_fields.get("product"))
    devices: dict[int, dict[str, object]] = {}
    info: list[dict[str, object]] = []
    if main_serial:
        devices[main_serial] = {
            "serial_number": main_serial,
            "timestamp": _local_time(fit, file_fields.get("time_created")),
            "manufacturer": main_manufacturer,
            "product": main_product,
        }
    for message in fit.device_info:
        fields = message.fields
        device_type = fields.get("device_type")
        serial = fields.get("serial_number") or None
        if (
            not serial
            and _name(fields.get("source_type")) == "local"
            and main_serial
            and device_type is not None
        ):
            serial = int(f"{main_serial}{device_type.value:06d}")
        if not serial:
            continue
        if serial >= 2**63:
            raise ValueError("Device serial number exceeds PostgreSQL bigint")
        timestamp = _local_time(fit, fields.get("timestamp"))
        if timestamp is None:
            raise ValueError("Device information is missing a timestamp")
        manufacturer = _name(fields.get("manufacturer"))
        if manufacturer is None:
            manufacturer = main_manufacturer
        product = _name(fields.get("product"))
        if product is None:
            product = main_product
        devices[serial] = {
            "serial_number": serial,
            "timestamp": timestamp,
            "device_type": _name(device_type),
            "manufacturer": manufacturer,
            "product": product,
            "hardware_version": fields.get("hardware_version"),
        }
        info.append(
            {
                "timestamp": timestamp,
                "file_id": activity_id,
                "serial_number": serial,
                "software_version": fields.get("software_version"),
                "cum_operating_time": fields.get("cum_operating_time"),
                "battery_status": _name(fields.get("battery_status")),
                "battery_voltage": fields.get("battery_voltage"),
            }
        )
    return list(devices.values()), info


def _sport_data(
    activity: dict[str, object],
    session: dict[str, Any],
    summary: dict[str, Any],
    details: dict[str, Any],
    fit: File,
) -> tuple[str, dict[str, object]] | None:
    sport = activity.get("sport")
    if sport in {"running", "walking", "hiking"}:
        detail = details.get("summaryDTO") or {}
        result = {
            "activity_id": activity["activity_id"],
            "steps": session.get("total_steps") or summary.get("steps"),
            "avg_steps_per_min": summary.get("averageRunningCadenceInStepsPerMinute")
            or session.get("avg_steps_per_min"),
            "max_steps_per_min": summary.get("maxRunningCadenceInStepsPerMinute")
            or session.get("max_steps_per_min"),
            "avg_step_length": summary.get("avgStrideLength")
            or (
                session.get("avg_step_length") / 10
                if session.get("avg_step_length") is not None
                else None
            ),
            "avg_vertical_ratio": session.get("avg_vertical_ratio"),
            "avg_vertical_oscillation": summary.get("avgVerticalOscillation")
            or (
                session.get("avg_vertical_oscillation") / 10
                if session.get("avg_vertical_oscillation") is not None
                else None
            ),
            "avg_gct_balance": session.get("avg_stance_time_balance"),
            "avg_ground_contact_time": session.get("avg_stance_time") or time.min,
            "avg_stance_time_percent": session.get("avg_stance_time_percent"),
            "vo2_max": summary.get("vO2MaxValue"),
        }
        for key, speed in (
            ("avg_pace", detail.get("averageSpeed")),
            ("avg_moving_pace", detail.get("averageMovingSpeed")),
            ("max_pace", detail.get("maxSpeed")),
        ):
            result[key] = (
                conversions.perhour_speed_to_pace(conversions.mps_to_mph(speed))
                or time.min
            )
        return "steps_activities", result
    if sport == "cycling":
        return "cycle_activities", {
            "activity_id": activity["activity_id"],
            "strokes": session.get("total_strokes") or summary.get("strokes"),
            "vo2_max": summary.get("vO2MaxValue"),
        }
    if sport in {"paddling", "rowing", "stand_up_paddleboarding"}:
        return "paddle_activities", {
            "activity_id": activity["activity_id"],
            "strokes": session.get("total_strokes") or summary.get("strokes"),
            "avg_stroke_distance": session.get("avg_stroke_distance"),
        }
    if sport == "rock_climbing":
        return "climbing_activities", {
            "activity_id": activity["activity_id"],
            "total_routes": len([m for m in fit.split if m.fields.get("grade")]),
        }
    return None


def import_activity(
    connection: Any,
    summary: dict[str, Any],
    details: dict[str, Any],
    path: Path,
    *,
    threshold_heart_rate_bpm: int = 157,
) -> None:
    """Insert or refresh an activity atomically, preserving missing values."""
    if details.get("activityId") != summary.get("activityId"):
        raise ValueError("Activity summary and details IDs differ")
    expected_id = str(summary.get("activityId"))
    if path.stem not in (expected_id, f"{expected_id}_ACTIVITY"):
        raise ValueError("FIT filename does not match the activity ID")
    if (
        isinstance(threshold_heart_rate_bpm, bool)
        or not 30 <= threshold_heart_rate_bpm <= 250
    ):
        raise ValueError("Heart-rate threshold must be between 30 and 250 bpm")
    if path.stat().st_size > 128 * 1024 * 1024:
        raise ValueError("FIT file exceeds 128 MiB")
    validate_fit(path.read_bytes())
    try:
        fit = File(str(path))
    except FitFileError:
        fit = decode_multisport(path, summary.get("startTimeLocal"))
    else:
        if len(fit.session) > 1:
            fit = decode_multisport(path, summary.get("startTimeLocal"))
    if not fit.session:
        raise ValueError("FIT file has no activity session")
    if fit.split and any(
        _name(session.fields.get("sport")) == "rock_climbing" for session in fit.session
    ):
        raise ValueError("Climbing splits cannot yet be imported safely")
    if len(fit.session) > 1:
        _import_multisport(
            connection, summary, details, path, fit, threshold_heart_rate_bpm
        )
        return
    _import_session(
        connection,
        summary,
        details,
        path,
        fit,
        decode_fit(fit),
        threshold_heart_rate_bpm,
        expected_id,
    )


def _import_session(
    connection: Any,
    summary: dict[str, Any],
    details: dict[str, Any],
    path: Path,
    fit: Any,
    decoded: dict[str, Any],
    threshold_heart_rate_bpm: int,
    activity_id: str,
) -> None:
    activity = map_activity_summary(summary, fit.session[0].fields, details)
    activity["activity_id"] = activity_id
    elapsed = activity["elapsed_time"]
    seconds = (
        elapsed.hour * 3600
        + elapsed.minute * 60
        + elapsed.second
        + elapsed.microsecond / 1_000_000
    )
    try:
        activity["tss"] = calculate_activity_tss(
            activity.get("sport"),
            threshold_heart_rate_bpm=threshold_heart_rate_bpm,
            average_heart_rate_bpm=activity.get("avg_hr"),
            elapsed_seconds=seconds,
        )["tss"]
    except TypeError, ValueError:
        activity["tss"] = None
    file_id = str(summary["activityId"])
    devices, device_info = _devices(fit, file_id)
    sport_data = _sport_data(activity, fit.session[0].fields, summary, details, fit)
    _apply_zones(fit, activity, decoded["laps"])
    activity_updates = tuple(column for column in activity if column != "activity_id")
    for zone in range(1, 6):
        activity.setdefault(f"hrz_{zone}_time", time.min)
    with connection.transaction():
        columns = tuple(activity)
        updated = connection.execute(
            sql.SQL(
                "INSERT INTO garmin_activities.activities AS current ({}) VALUES ({}) "
                "ON CONFLICT (activity_id) DO UPDATE SET {} "
                "WHERE current.sport IS NULL OR EXCLUDED.sport IS NULL OR current.sport = EXCLUDED.sport "
                "RETURNING activity_id"
            ).format(
                sql.SQL(", ").join(map(sql.Identifier, columns)),
                sql.SQL(", ").join(sql.Placeholder() for _ in columns),
                sql.SQL(", ").join(
                    sql.SQL("{} = COALESCE(EXCLUDED.{}, current.{})").format(
                        *([sql.Identifier(column)] * 3)
                    )
                    for column in activity_updates
                ),
            ),
            tuple(activity[column] for column in columns),
        ).fetchone()
        if updated is None:
            raise ValueError(
                "Activity sport changed; existing sport-specific data requires review"
            )
        for table, index, incoming in (
            ("activity_records", "record", decoded["records"]),
            ("activity_laps", "lap", decoded["laps"]),
        ):
            maximum = connection.execute(
                sql.SQL(
                    "SELECT max({}) FROM garmin_activities.{} WHERE activity_id = %s"
                ).format(sql.Identifier(index), sql.Identifier(table)),
                (activity_id,),
            ).fetchone()[0]
            if maximum is not None and maximum >= len(incoming):
                raise ValueError(
                    f"Incoming FIT has fewer {table}; existing data was preserved"
                )
        if sport_data is not None:
            table, row = sport_data
            updates = tuple(
                column
                for column, value in row.items()
                if column != "activity_id"
                and value is not None
                and not (
                    column
                    in (
                        "avg_pace",
                        "avg_moving_pace",
                        "max_pace",
                        "avg_ground_contact_time",
                    )
                    and value == time.min
                )
            )
            _upsert(
                connection, "garmin_activities", table, row, ("activity_id",), updates
            )
        _invalidate_changed_grade(connection, activity_id, decoded["records"])
        _upsert_many(
            connection,
            "garmin_activities",
            "activity_records",
            [{"activity_id": activity_id, **record} for record in decoded["records"]],
            ("activity_id", "record"),
        )
        for lap in decoded["laps"]:
            lap = {"activity_id": activity_id, **lap}
            lap_updates = tuple(
                column
                for column, value in lap.items()
                if column not in ("activity_id", "lap") and value is not None
            )
            for key in (
                "elapsed_time",
                "moving_time",
                *(f"hrz_{zone}_time" for zone in range(1, 6)),
            ):
                if lap.get(key) is None:
                    lap[key] = time.min
            _upsert(
                connection,
                "garmin_activities",
                "activity_laps",
                lap,
                ("activity_id", "lap"),
                lap_updates,
            )
        for device in devices:
            _upsert_device(connection, device)
        _upsert(
            connection,
            "garmin",
            "files",
            {
                "id": file_id,
                "name": path.name,
                "type": "fit_activity",
                "serial_number": fit.file_id[0].fields.get("serial_number") or None,
            },
            ("id",),
        )
        for info in device_info:
            info_updates = tuple(
                column
                for column in info
                if column not in ("timestamp", "serial_number", "file_id")
                and info[column] is not None
            )
            info["cum_operating_time"] = info["cum_operating_time"] or time.min
            _upsert(
                connection,
                "garmin",
                "device_info",
                info,
                ("timestamp", "serial_number"),
                info_updates,
            )
            _insert(
                connection,
                "garmin_activities",
                "activities_devices",
                {
                    "activity_id": activity_id,
                    "device_serial_number": info["serial_number"],
                },
            )


def _import_multisport(
    connection: Any,
    summary: dict[str, Any],
    details: dict[str, Any],
    path: Path,
    fit: File,
    threshold: int,
) -> None:
    decoded_sessions = decode_fit_sessions(fit)
    counts = [session.fields["num_laps"] for session in fit.session]
    first_laps = [sum(counts[:i]) for i in range(len(counts))]
    zones = [[] for _ in counts]
    for message in fit.hr_zones_timer:
        fields = dict(message.fields)
        kind = _name(fields.get("hr_zones_timer_type"))
        number = fields.get("record_num")
        if kind == "session":
            if not isinstance(number, int) or not 0 <= number < len(counts):
                raise ValueError("Heart-rate zone data refers to an unknown session")
            zones[number].append(SimpleNamespace(fields=fields))
        elif kind == "lap":
            if not isinstance(number, int):
                raise ValueError("Heart-rate zone data refers to an unknown lap")
            index = next(
                (
                    i
                    for i, first in enumerate(first_laps)
                    if first <= number < first + counts[i]
                ),
                None,
            )
            if index is None:
                raise ValueError("Heart-rate zone data refers to an unknown lap")
            fields["record_num"] = number - first_laps[index]
            zones[index].append(SimpleNamespace(fields=fields))
    parent = map_activity_summary(summary, {"sport": "multisport"}, details)
    parent_updates = tuple(column for column in parent if column != "activity_id")
    for zone in range(1, 6):
        parent.setdefault(f"hrz_{zone}_time", time.min)
    base_id = str(summary["activityId"])
    with connection.transaction():
        old = connection.execute(
            "SELECT sport FROM garmin_activities.activities WHERE activity_id = %s FOR UPDATE",
            (base_id,),
        ).fetchone()
        if old and old[0] not in (None, "multisport"):
            raise ValueError(
                "Activity sport changed; existing sport-specific data requires review"
            )
        _upsert(
            connection,
            "garmin_activities",
            "activities",
            parent,
            ("activity_id",),
            parent_updates,
        )
        for index, (session, decoded) in enumerate(
            zip(fit.session, decoded_sessions, strict=True)
        ):
            fields = dict(session.fields)
            start = fields["start_time"]
            duration = fields["total_elapsed_time"]
            fields["timestamp"] = start + timedelta(
                hours=duration.hour,
                minutes=duration.minute,
                seconds=duration.second,
                microseconds=duration.microsecond,
            )
            local_start = _local_time(fit, start)
            child_summary = {
                "activityId": summary["activityId"],
                "activityName": summary.get("activityName"),
                "startTimeLocal": local_start.isoformat(),
            }
            child_fit = SimpleNamespace(
                session=[SimpleNamespace(fields=fields)],
                file_id=fit.file_id,
                device_info=fit.device_info,
                hr_zones_timer=zones[index],
                split=fit.split,
                utc_datetime_to_local=fit.utc_datetime_to_local,
            )
            _import_session(
                connection,
                child_summary,
                {},
                path,
                child_fit,
                decoded,
                threshold,
                f"{base_id}_{index + 1}",
            )
