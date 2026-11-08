"""Select expired Garmin records without removing configuration metadata."""

from psycopg import sql

ACTIVITY_TABLES = (
    "activities_devices",
    "activity_laps",
    "activity_records",
    "activity_splits",
    "climbing_activities",
    "cycle_activities",
    "paddle_activities",
    "steps_activities",
)

DATED_TABLES = {
    "garmin": {
        "daily_summary": ("day", "1 day"),
        "device_info": ("timestamp", None),
        "hrv": ("day", "1 day"),
        "resting_hr": ("day", "1 day"),
        "sleep": ("day", "1 day"),
        "sleep_events": ("timestamp", None),
        "stress": ("timestamp", None),
        "weight": ("day", "1 day"),
    },
    "garmin_monitoring": {
        name: ("timestamp", None)
        for name in (
            "monitoring",
            "monitoring_climb",
            "monitoring_hr",
            "monitoring_hrv_status",
            "monitoring_hrv_value",
            "monitoring_info",
            "monitoring_intensity",
            "monitoring_pulse_ox",
            "monitoring_rr",
        )
    },
    **{
        schema: {
            "days_summary": ("day", "1 day"),
            "weeks_summary": ("first_day", "1 week"),
            "months_summary": ("first_day", "1 month"),
            "years_summary": ("first_day", "1 year"),
        }
        for schema in ("garmin_summary", "summary")
    },
}
DATED_TABLES["garmin_summary"]["intensity_hr"] = ("timestamp", None)


def dated_delete(schema: str, table: str) -> sql.Composed:
    """Build a parameterized delete for a known date or complete summary period."""
    column, period = DATED_TABLES[schema][table]
    end = sql.Identifier(column)
    if period:
        end = sql.SQL("{} + {}::interval").format(end, sql.Literal(period))
    return sql.SQL("DELETE FROM {}.{} WHERE {} < %s").format(
        sql.Identifier(schema), sql.Identifier(table), end
    )
