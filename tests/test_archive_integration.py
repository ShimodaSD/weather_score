"""Exercise deletion only inside a named disposable local archive database."""

import os
from datetime import datetime

import psycopg
import pytest
from dotenv import dotenv_values

from scripts.archive_old_data import delete_expired, tables


@pytest.mark.skipif(
    not os.environ.get("ARCHIVE_TEST_DB"), reason="needs a disposable local archive"
)
def test_retention_keeps_processing_and_overlapping_data():
    name = os.environ["ARCHIVE_TEST_DB"]
    assert name.startswith("weather_archive_")
    settings = dotenv_values("/app/.env")
    with psycopg.connect(
        host="postgres",
        user="postgres",
        password=settings["DB_PASSWORD"],
        dbname=name,
        sslmode="disable",
    ) as connection:
        try:
            for activity_id, date in (
                ("__test_old__", "2020-01-01"),
                ("__test_busy__", "2020-01-01"),
                ("__test_recent__", "2026-01-01"),
            ):
                connection.execute(
                    "INSERT INTO garmin_activities.activities "
                    "SELECT (jsonb_populate_record(NULL::garmin_activities.activities, "
                    "to_jsonb(t) || jsonb_build_object('activity_id', %s::text, 'start_time', %s::text))).* "
                    "FROM garmin_activities.activities t LIMIT 1",
                    (activity_id, date),
                )
            connection.execute(
                "INSERT INTO public.activity_grades (activity_id,status) "
                "VALUES ('__test_old__','complete'), ('__test_busy__','processing')"
            )
            connection.execute(
                "INSERT INTO public.activity_grades (activity_id,status,created_at) "
                "VALUES ('__test_orphan_old__','failed','2020-01-01'), "
                "('__test_orphan_busy__','processing','2020-01-01'), "
                "('__test_orphan_recent__','failed','2026-01-01')"
            )
            connection.execute(
                "INSERT INTO garmin_activities.activity_records "
                "SELECT (jsonb_populate_record(NULL::garmin_activities.activity_records, "
                "to_jsonb(t) || jsonb_build_object('activity_id', '__test_old__'))).* "
                "FROM garmin_activities.activity_records t LIMIT 1"
            )
            connection.execute(
                "INSERT INTO garmin_summary.months_summary "
                "(first_day, intensity_time, moderate_activity_time, vigorous_activity_time, "
                "intensity_time_goal, sleep_avg, sleep_min, sleep_max, rem_sleep_avg, rem_sleep_min, rem_sleep_max) "
                "VALUES (%s, '00:00', '00:00', '00:00', '00:00', '00:00', '00:00', '00:00', '00:00', '00:00', '00:00'), "
                "(%s, '00:00', '00:00', '00:00', '00:00', '00:00', '00:00', '00:00', '00:00', '00:00', '00:00')",
                ("1900-01-01", "2025-11-01"),
            )
            delete_expired(
                connection,
                datetime.fromisoformat("2025-11-07T00:00:00"),
                tables(connection),
            )
            remaining = connection.execute(
                "SELECT activity_id FROM garmin_activities.activities "
                "WHERE activity_id = ANY(%s) ORDER BY activity_id",
                (["__test_old__", "__test_busy__", "__test_recent__"],),
            ).fetchall()
            assert remaining == [("__test_busy__",), ("__test_recent__",)]
            assert (
                connection.execute(
                    "SELECT count(*) FROM public.activity_grades WHERE activity_id = '__test_old__'"
                ).fetchone()[0]
                == 0
            )
            orphan_grades = connection.execute(
                "SELECT activity_id FROM public.activity_grades WHERE activity_id = ANY(%s) ORDER BY activity_id",
                (
                    [
                        "__test_orphan_old__",
                        "__test_orphan_busy__",
                        "__test_orphan_recent__",
                    ],
                ),
            ).fetchall()
            assert orphan_grades == [
                ("__test_orphan_busy__",),
                ("__test_orphan_recent__",),
            ]
            assert (
                connection.execute(
                    "SELECT count(*) FROM garmin_activities.activity_records WHERE activity_id = '__test_old__'"
                ).fetchone()[0]
                == 0
            )
            summaries = connection.execute(
                "SELECT first_day::date FROM garmin_summary.months_summary "
                "WHERE first_day = ANY(%s::timestamp[]) ORDER BY first_day",
                (["1900-01-01", "2025-11-01"],),
            ).fetchall()
            assert [row[0].isoformat() for row in summaries] == ["2025-11-01"]
        finally:
            connection.rollback()
