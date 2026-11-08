"""Map Garmin activity data to fields used by the existing activity API."""

from datetime import UTC, datetime, time, timedelta
from typing import Any

from .fit_activity import LAP_FIELDS


def _duration(seconds: object) -> time | None:
    if not isinstance(seconds, int | float) or isinstance(seconds, bool):
        return None
    if not 0 <= seconds < 86400:
        raise ValueError(
            "Activity duration cannot be represented by the existing database"
        )
    value = timedelta(seconds=int(seconds))
    return (datetime.min.replace(tzinfo=UTC) + value).time()


def map_activity_summary(
    summary: dict[str, Any],
    session: dict[str, Any],
    details: dict[str, Any] | None = None,
) -> dict[str, object]:
    """Merge the activity summary with FIT session fields using metric units."""
    activity_id = summary.get("activityId")
    if (
        not isinstance(activity_id, int)
        or isinstance(activity_id, bool)
        or activity_id <= 0
    ):
        raise ValueError("Invalid Garmin activity ID")
    start = summary.get("startTimeLocal")
    if not isinstance(start, str):
        raise TypeError("Missing local activity start time")
    start_time = datetime.fromisoformat(start)
    if start_time.tzinfo is not None:
        raise ValueError("Activity local start time must not include a timezone")
    fields = {
        "activity_id": str(activity_id),
        "name": summary.get("activityName"),
        "description": summary.get("description"),
        "start_time": start_time,
        "elapsed_time": _duration(summary.get("elapsedDuration")),
        "moving_time": _duration(summary.get("movingDuration")),
        "distance": summary.get("distance") / 1000
        if summary.get("distance") is not None
        else None,
        "avg_hr": summary.get("averageHR"),
        "max_hr": summary.get("maxHR"),
        "calories": summary.get("calories"),
        "training_effect": summary.get("aerobicTrainingEffect"),
        "anaerobic_training_effect": summary.get("anaerobicTrainingEffect"),
        "laps": summary.get("lapCount"),
        "type": (summary.get("eventType") or {}).get("typeKey"),
    }
    for column, fit_field in LAP_FIELDS.items():
        value = session.get(fit_field)
        if column in ("elapsed_time", "moving_time") and fields[column] is not None:
            continue
        if value is not None and value != 0:
            fields[column] = value
    detail_summary = (details or {}).get("summaryDTO", {})
    metadata = (details or {}).get("metadataDTO", {})
    fields["course_id"] = metadata.get("associatedCourseId")
    fields["device_serial_number"] = metadata.get("deviceId")
    fields["training_load"] = detail_summary.get("activityTrainingLoad")
    for column, key, levels in (
        (
            "self_eval_feel",
            "directWorkoutFeel",
            (
                (100, "Very Strong"),
                (75, "Strong"),
                (50, "Normal"),
                (25, "Weak"),
                (0, "Very Weak"),
            ),
        ),
        (
            "self_eval_effort",
            "directWorkoutRpe",
            (
                (100, "Maximum"),
                (90, "Extremely Hard"),
                (70, "Very Hard"),
                (50, "Hard"),
                (40, "Somewhat Hard"),
                (30, "Moderate"),
                (20, "Light"),
                (10, "Very Light"),
                (0, "None"),
            ),
        ),
    ):
        value = detail_summary.get(key)
        fields[column] = next(
            (
                label
                for threshold, label in levels
                if value is not None and value >= threshold
            ),
            None,
        )
    for column, key in (("avg_speed", "averageSpeed"), ("max_speed", "maxSpeed")):
        if detail_summary.get(key) is not None:
            fields[column] = detail_summary[key] * 3.6
    if detail_summary.get("averageTemperature") is not None:
        fields["avg_temperature"] = detail_summary["averageTemperature"]
    for column, key in (
        ("training_effect", "total_training_effect"),
        ("anaerobic_training_effect", "total_anaerobic_training_effect"),
    ):
        if session.get(key) is not None:
            fields[column] = session[key]
    for column in ("sport", "sub_sport"):
        value = session.get(column)
        fields[column] = getattr(value, "name", value)
    activity_type = summary.get("activityType") or {}
    if (
        fields["sport"] == "training"
        and activity_type.get("typeKey") == "strength_training"
    ):
        fields["sport"] = "fitness_equipment"
    if fields["elapsed_time"] is None or fields["moving_time"] is None:
        raise ValueError("Activity is missing a required duration")
    duration = fields["elapsed_time"]
    fields["stop_time"] = start_time + timedelta(
        hours=duration.hour,
        minutes=duration.minute,
        seconds=duration.second,
        microseconds=duration.microsecond,
    )
    return fields
