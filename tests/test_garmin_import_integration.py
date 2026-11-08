"""Test the importer against an explicitly selected disposable PostgreSQL database."""

import json
import os
import shutil
import sqlite3
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from types import SimpleNamespace

import psycopg
import pytest

import weather_score.garmin_activity_import as importer
from scripts import sync_garmindb
from weather_score.application.training_stress import calculate_activity_tss
from weather_score.garmin_activity_import import _upsert_device, import_activity


@pytest.mark.skipif(
    not os.environ.get("FIT_DIRECT_TEST_DB"),
    reason="requires a disposable direct-sync database",
)
def test_direct_sync_uses_saved_profile_and_is_repeatable(tmp_path, monkeypatch):
    import weather_score.garmin as personal_api

    database = os.environ["FIT_DIRECT_TEST_DB"]
    assert database.startswith("weather_import_trial_direct_")
    reference = Path(os.environ["FIT_IMPORT_TEST_REFERENCE"]) / "activities"
    with sqlite3.connect(
        f"{(reference.parent / 'garmin_activities.db').resolve().as_uri()}?mode=ro",
        uri=True,
    ) as source_db:
        rows = source_db.execute(
            "SELECT activity_id, sport, avg_hr, elapsed_time FROM activities WHERE sport IN ('running', 'cycling') AND avg_hr BETWEEN 30 AND 250"
        ).fetchall()
    for candidate, sport, hr, elapsed in rows:
        duration = time.fromisoformat(elapsed)
        seconds = duration.hour * 3600 + duration.minute * 60 + duration.second
        values = [
            calculate_activity_tss(
                sport,
                threshold_heart_rate_bpm=threshold,
                average_heart_rate_bpm=hr,
                elapsed_seconds=seconds,
            )["tss"]
            for threshold in (157, 170)
        ]
        if values[0] != values[1]:
            break
    else:
        pytest.fail(
            "Reference has no activity that distinguishes the profile threshold"
        )
    source = reference / f"activity_{candidate}.json"
    summary = json.loads(source.read_text())
    activity_id = str(summary["activityId"])
    directory = tmp_path / "HealthData/FitFiles/Activities"
    directory.mkdir(parents=True)
    for path in (source, reference / f"activity_details_{activity_id}.json"):
        shutil.copy(path, directory / path.name)
    fit = next(
        path
        for path in (
            reference / f"{activity_id}.fit",
            reference / f"{activity_id}_ACTIVITY.fit",
        )
        if path.exists()
    )
    shutil.copy(fit, directory / fit.name)
    monkeypatch.setattr(personal_api, "fetch_activities", lambda path, **kwargs: None)
    for key, value in {
        "DB_NAME": database,
        "DB_NAME_GARMIN": database,
        "DB_SHARED_GARMIN": "1",
        "DB_HOST": os.environ["FIT_IMPORT_TEST_HOST"],
        "DB_PORT": os.environ["PGPORT"],
        "DB_USER": "postgres",
        "DB_PASSWORD": os.environ["FIT_IMPORT_TEST_PASSWORD"],
    }.items():
        monkeypatch.setenv(key, value)
    with psycopg.connect(
        **sync_garmindb._get_postgres_parameters(database)
    ) as connection:
        connection.execute(
            "INSERT INTO public.athlete_profile (id, threshold_heart_rate_bpm) VALUES (1, 170) ON CONFLICT (id) DO UPDATE SET threshold_heart_rate_bpm = 170"
        )
    target = tmp_path / "HealthData/DBs/garmin_activities.db"
    sync_garmindb._sync_direct(target, database)
    sync_garmindb._sync_direct(target, database)
    with psycopg.connect(
        **sync_garmindb._get_postgres_parameters(database)
    ) as connection:
        sport, hr, seconds, tss = connection.execute(
            "SELECT sport, avg_hr, EXTRACT(EPOCH FROM elapsed_time)::double precision, tss FROM garmin_activities.activities WHERE activity_id = %s",
            (activity_id,),
        ).fetchone()
        expected = calculate_activity_tss(
            sport,
            threshold_heart_rate_bpm=170,
            average_heart_rate_bpm=hr,
            elapsed_seconds=seconds,
        )["tss"]
        assert tss == expected
        assert (
            tss
            != calculate_activity_tss(
                sport,
                threshold_heart_rate_bpm=157,
                average_heart_rate_bpm=hr,
                elapsed_seconds=seconds,
            )["tss"]
        )
        assert (
            connection.execute(
                "SELECT count(*) FROM garmin_activities.activities"
            ).fetchone()[0]
            == 1
        )


@pytest.mark.skipif(
    not os.environ.get("FIT_IMPORT_TEST_DB"), reason="requires a disposable database"
)
def test_changed_route_invalidates_grade_and_processing_blocks_update(monkeypatch):
    database = os.environ["FIT_IMPORT_TEST_DB"]
    assert database.startswith("weather_import_trial")
    reference = Path(os.environ["FIT_IMPORT_TEST_REFERENCE"]) / "activities"
    summary = json.loads(next(reference.glob("activity_[0-9]*.json")).read_text())
    activity_id = str(summary["activityId"])
    details = json.loads(
        (reference / f"activity_details_{activity_id}.json").read_text()
    )
    fit = next(
        path
        for path in (
            reference / f"{activity_id}.fit",
            reference / f"{activity_id}_ACTIVITY.fit",
        )
        if path.exists()
    )
    decode = importer.decode_fit
    with (
        psycopg.connect(
            host=os.environ["FIT_IMPORT_TEST_HOST"],
            dbname=database,
            user="postgres",
            password=os.environ["FIT_IMPORT_TEST_PASSWORD"],
            sslmode="disable",
        ) as connection,
        pytest.raises(RuntimeError, match="rollback"),
        connection.transaction(),
    ):
        import_activity(connection, summary, details, fit)
        connection.execute(
            "INSERT INTO public.activity_grades (activity_id, status, score) VALUES (%s, 'complete', 80)",
            (activity_id,),
        )
        import_activity(connection, summary, details, fit)
        assert connection.execute(
            "SELECT status, score FROM public.activity_grades WHERE activity_id = %s",
            (activity_id,),
        ).fetchone() == ("complete", 80)

        def changed(fit_file):
            result = decode(fit_file)
            result["records"][0]["distance"] = 123.456
            return result

        monkeypatch.setattr(importer, "decode_fit", changed)
        connection.execute(
            "UPDATE public.activity_grades SET status = 'processing' WHERE activity_id = %s",
            (activity_id,),
        )
        with pytest.raises(ValueError, match="being graded"):
            import_activity(connection, summary, details, fit)
        assert connection.execute(
            "SELECT status FROM public.activity_grades WHERE activity_id = %s",
            (activity_id,),
        ).fetchone() == ("processing",)
        connection.execute(
            "UPDATE public.activity_grades SET status = 'complete' WHERE activity_id = %s",
            (activity_id,),
        )
        upsert_many = importer._upsert_many

        def fail_records(connection, schema, table, *args, **kwargs):
            if table == "activity_records":
                raise RuntimeError("simulated record failure")
            return upsert_many(connection, schema, table, *args, **kwargs)

        with monkeypatch.context() as context:
            context.setattr(importer, "_upsert_many", fail_records)
            with pytest.raises(RuntimeError, match="simulated record failure"):
                import_activity(connection, summary, details, fit)
        assert connection.execute(
            "SELECT status, score FROM public.activity_grades WHERE activity_id = %s",
            (activity_id,),
        ).fetchone() == ("complete", 80)
        import_activity(connection, summary, details, fit)
        assert connection.execute(
            "SELECT status, score, error FROM public.activity_grades WHERE activity_id = %s",
            (activity_id,),
        ).fetchone() == (
            "failed",
            None,
            "Activity route changed. Regrade this activity.",
        )
        connection.execute(
            "ALTER TABLE public.activity_grades RENAME TO activity_grades_test_hidden"
        )

        def changed_again(fit_file):
            result = decode(fit_file)
            result["records"][0]["distance"] = 234.567
            return result

        monkeypatch.setattr(importer, "decode_fit", changed_again)
        with pytest.raises(ValueError, match="without grade storage"):
            import_activity(connection, summary, details, fit)
        assert connection.execute(
            "SELECT distance FROM garmin_activities.activity_records WHERE activity_id = %s AND record = 0",
            (activity_id,),
        ).fetchone() == (123.456,)
        raise RuntimeError("rollback")


@pytest.mark.skipif(
    not os.environ.get("FIT_IMPORT_TEST_DB"), reason="requires a disposable database"
)
def test_import_and_grade_queue_share_an_activity_lock():
    database = os.environ["FIT_IMPORT_TEST_DB"]
    assert database.startswith("weather_import_trial")
    options = {
        "host": os.environ["FIT_IMPORT_TEST_HOST"],
        "dbname": database,
        "user": "postgres",
        "password": os.environ["FIT_IMPORT_TEST_PASSWORD"],
        "sslmode": "disable",
    }
    with psycopg.connect(**options) as importer_connection:
        with importer_connection.transaction():
            importer._invalidate_changed_grade(importer_connection, "__test_lock__", [])
            with psycopg.connect(**options) as queue_connection:
                assert not queue_connection.execute(
                    "SELECT pg_try_advisory_xact_lock(hashtextextended('weather-grade:' || %s, 0))",
                    ("__test_lock__",),
                ).fetchone()[0]
        with psycopg.connect(**options) as queue_connection:
            assert queue_connection.execute(
                "SELECT pg_try_advisory_xact_lock(hashtextextended('weather-grade:' || %s, 0))",
                ("__test_lock__",),
            ).fetchone()[0]


@pytest.mark.skipif(
    not os.environ.get("FIT_IMPORT_TEST_DB"), reason="requires a disposable database"
)
def test_import_is_atomic_and_repeatable():
    database = os.environ["FIT_IMPORT_TEST_DB"]
    assert database.startswith("weather_import_trial")
    reference = Path(os.environ["FIT_IMPORT_TEST_REFERENCE"])
    source = next((reference / "activities").glob("activity_[0-9]*.json"))
    summary = json.loads(source.read_text())
    activity_id = str(summary["activityId"])
    details = json.loads(
        (reference / "activities" / f"activity_details_{activity_id}.json").read_text()
    )
    fit = next(
        path
        for path in (
            reference / "activities" / f"{activity_id}.fit",
            reference / "activities" / f"{activity_id}_ACTIVITY.fit",
        )
        if path.exists()
    )
    with psycopg.connect(
        host=os.environ["FIT_IMPORT_TEST_HOST"],
        dbname=database,
        user="postgres",
        password=os.environ["FIT_IMPORT_TEST_PASSWORD"],
        sslmode="disable",
    ) as connection:
        with pytest.raises(RuntimeError, match="rollback"), connection.transaction():
            import_activity(connection, summary, details, fit)
            counts = [
                connection.execute(
                    f"SELECT count(*) FROM garmin_activities.{table} WHERE activity_id = %s",
                    (activity_id,),
                ).fetchone()[0]
                for table in (
                    "activities",
                    "activity_laps",
                    "activity_records",
                    "activities_devices",
                )
            ]
            assert counts[0] == 1
            assert counts[2] > 0
            import_activity(connection, summary, details, fit)
            assert counts == [
                connection.execute(
                    f"SELECT count(*) FROM garmin_activities.{table} WHERE activity_id = %s",
                    (activity_id,),
                ).fetchone()[0]
                for table in (
                    "activities",
                    "activity_laps",
                    "activity_records",
                    "activities_devices",
                )
            ]
            raise RuntimeError("rollback")
        assert (
            connection.execute(
                "SELECT count(*) FROM garmin_activities.activities WHERE activity_id = %s",
                (activity_id,),
            ).fetchone()[0]
            == 0
        )


@pytest.mark.skipif(
    not os.environ.get("FIT_IMPORT_TEST_DB"), reason="requires a disposable database"
)
def test_device_update_preserves_newer_metadata():
    database = os.environ["FIT_IMPORT_TEST_DB"]
    assert database.startswith("weather_import_trial")
    with (
        psycopg.connect(
            host=os.environ["FIT_IMPORT_TEST_HOST"],
            dbname=database,
            user="postgres",
            password=os.environ["FIT_IMPORT_TEST_PASSWORD"],
            sslmode="disable",
        ) as connection,
        pytest.raises(RuntimeError, match="rollback"),
        connection.transaction(),
    ):
        _upsert_device(
            connection,
            {"serial_number": 123456, "timestamp": "2026-01-02", "product": "new"},
        )
        _upsert_device(
            connection,
            {"serial_number": 123456, "timestamp": "2026-01-01", "product": "old"},
        )
        assert (
            connection.execute(
                "SELECT product FROM garmin.devices WHERE serial_number = 123456"
            ).fetchone()[0]
            == "new"
        )
        _upsert_device(
            connection,
            {"serial_number": 123456, "timestamp": "2026-01-03", "product": None},
        )
        assert (
            connection.execute(
                "SELECT product FROM garmin.devices WHERE serial_number = 123456"
            ).fetchone()[0]
            == "new"
        )
        raise RuntimeError("rollback")


@pytest.mark.skipif(
    not os.environ.get("FIT_IMPORT_TEST_DB"), reason="requires a disposable database"
)
def test_import_failure_rolls_back_activity(monkeypatch):
    database = os.environ["FIT_IMPORT_TEST_DB"]
    assert database.startswith("weather_import_trial")
    reference = Path(os.environ["FIT_IMPORT_TEST_REFERENCE"]) / "activities"
    summary = json.loads(next(reference.glob("activity_[0-9]*.json")).read_text())
    activity_id = str(summary["activityId"])
    details = json.loads(
        (reference / f"activity_details_{activity_id}.json").read_text()
    )
    fit = next(
        path
        for path in (
            reference / f"{activity_id}.fit",
            reference / f"{activity_id}_ACTIVITY.fit",
        )
        if path.exists()
    )
    monkeypatch.setattr(
        "weather_score.garmin_activity_import._devices",
        lambda *_: (
            [{"serial_number": 123456, "manufacturer": "not_an_enum_value"}],
            [],
        ),
    )
    with psycopg.connect(
        host=os.environ["FIT_IMPORT_TEST_HOST"],
        dbname=database,
        user="postgres",
        password=os.environ["FIT_IMPORT_TEST_PASSWORD"],
        sslmode="disable",
    ) as connection:
        with pytest.raises(psycopg.errors.InvalidTextRepresentation):
            import_activity(connection, summary, details, fit)
        assert (
            connection.execute(
                "SELECT count(*) FROM garmin_activities.activities WHERE activity_id = %s",
                (activity_id,),
            ).fetchone()[0]
            == 0
        )


@pytest.mark.skipif(
    not os.environ.get("FIT_IMPORT_TEST_DB"), reason="requires a disposable database"
)
def test_existing_activity_updates_without_losing_missing_fields(monkeypatch):
    database = os.environ["FIT_IMPORT_TEST_DB"]
    assert database.startswith("weather_import_trial")
    reference = Path(os.environ["FIT_IMPORT_TEST_REFERENCE"]) / "activities"
    summary = json.loads(next(reference.glob("activity_[0-9]*.json")).read_text())
    activity_id = str(summary["activityId"])
    details = json.loads(
        (reference / f"activity_details_{activity_id}.json").read_text()
    )
    fit = next(
        path
        for path in (
            reference / f"{activity_id}.fit",
            reference / f"{activity_id}_ACTIVITY.fit",
        )
        if path.exists()
    )
    decode = importer.decode_fit
    with (
        psycopg.connect(
            host=os.environ["FIT_IMPORT_TEST_HOST"],
            dbname=database,
            user="postgres",
            password=os.environ["FIT_IMPORT_TEST_PASSWORD"],
            sslmode="disable",
        ) as connection,
        pytest.raises(RuntimeError, match="rollback"),
        connection.transaction(),
    ):
        import_activity(connection, summary, details, fit)
        connection.execute(
            "UPDATE garmin_activities.activity_records SET position_lat = 12.5 WHERE activity_id = %s AND record = 0",
            (activity_id,),
        )
        connection.execute(
            "UPDATE garmin_activities.activities SET description = 'Preserved', hrz_1_time = '00:07:00' WHERE activity_id = %s",
            (activity_id,),
        )

        def changed(fit_file):
            result = decode(fit_file)
            result["records"][0]["hr"] = 141
            result["records"][0]["position_lat"] = None
            return result

        monkeypatch.setattr(importer, "decode_fit", changed)
        monkeypatch.setattr(importer, "_apply_zones", lambda *_: None)
        import_activity(
            connection,
            summary | {"activityName": "Updated activity", "description": None},
            details,
            fit,
        )
        assert (
            connection.execute(
                "SELECT name FROM garmin_activities.activities WHERE activity_id = %s",
                (activity_id,),
            ).fetchone()[0]
            == "Updated activity"
        )
        assert connection.execute(
            "SELECT hr, position_lat FROM garmin_activities.activity_records WHERE activity_id = %s AND record = 0",
            (activity_id,),
        ).fetchone() == (141, 12.5)
        assert (
            connection.execute(
                "SELECT description FROM garmin_activities.activities WHERE activity_id = %s",
                (activity_id,),
            ).fetchone()[0]
            == "Preserved"
        )
        assert (
            connection.execute(
                "SELECT hrz_1_time::text FROM garmin_activities.activities WHERE activity_id = %s",
                (activity_id,),
            ).fetchone()[0]
            == "00:07:00"
        )
        raise RuntimeError("rollback")


@pytest.mark.skipif(
    not os.environ.get("FIT_IMPORT_TEST_DB"), reason="requires a disposable database"
)
def test_shorter_fit_aborts_and_rolls_back_summary(monkeypatch):
    database = os.environ["FIT_IMPORT_TEST_DB"]
    assert database.startswith("weather_import_trial")
    reference = Path(os.environ["FIT_IMPORT_TEST_REFERENCE"]) / "activities"
    summary = json.loads(next(reference.glob("activity_[0-9]*.json")).read_text())
    activity_id = str(summary["activityId"])
    details = json.loads(
        (reference / f"activity_details_{activity_id}.json").read_text()
    )
    fit = next(
        path
        for path in (
            reference / f"{activity_id}.fit",
            reference / f"{activity_id}_ACTIVITY.fit",
        )
        if path.exists()
    )
    decode = importer.decode_fit
    with (
        psycopg.connect(
            host=os.environ["FIT_IMPORT_TEST_HOST"],
            dbname=database,
            user="postgres",
            password=os.environ["FIT_IMPORT_TEST_PASSWORD"],
            sslmode="disable",
        ) as connection,
        pytest.raises(RuntimeError, match="rollback"),
        connection.transaction(),
    ):
        import_activity(connection, summary, details, fit)
        before = connection.execute(
            "SELECT name FROM garmin_activities.activities WHERE activity_id = %s",
            (activity_id,),
        ).fetchone()[0]

        def truncated(fit_file):
            result = decode(fit_file)
            result["records"].pop()
            return result

        monkeypatch.setattr(importer, "decode_fit", truncated)
        with pytest.raises(ValueError, match="fewer"):
            import_activity(
                connection,
                summary | {"activityName": "Should roll back"},
                details,
                fit,
            )
        assert (
            connection.execute(
                "SELECT name FROM garmin_activities.activities WHERE activity_id = %s",
                (activity_id,),
            ).fetchone()[0]
            == before
        )
        raise RuntimeError("rollback")


@pytest.mark.skipif(
    not os.environ.get("FIT_IMPORT_TEST_DB"), reason="requires a disposable database"
)
def test_sport_change_is_rejected_without_changing_existing_activity(monkeypatch):
    database = os.environ["FIT_IMPORT_TEST_DB"]
    assert database.startswith("weather_import_trial")
    reference = Path(os.environ["FIT_IMPORT_TEST_REFERENCE"]) / "activities"
    summary = json.loads(next(reference.glob("activity_[0-9]*.json")).read_text())
    activity_id = str(summary["activityId"])
    details = json.loads(
        (reference / f"activity_details_{activity_id}.json").read_text()
    )
    fit = next(
        path
        for path in (
            reference / f"{activity_id}.fit",
            reference / f"{activity_id}_ACTIVITY.fit",
        )
        if path.exists()
    )
    map_summary = importer.map_activity_summary
    with (
        psycopg.connect(
            host=os.environ["FIT_IMPORT_TEST_HOST"],
            dbname=database,
            user="postgres",
            password=os.environ["FIT_IMPORT_TEST_PASSWORD"],
            sslmode="disable",
        ) as connection,
        pytest.raises(RuntimeError, match="rollback"),
        connection.transaction(),
    ):
        import_activity(connection, summary, details, fit)
        before = connection.execute(
            "SELECT sport FROM garmin_activities.activities WHERE activity_id = %s",
            (activity_id,),
        ).fetchone()[0]
        monkeypatch.setattr(
            importer,
            "map_activity_summary",
            lambda *args: map_summary(*args) | {"sport": "other_sport"},
        )
        with pytest.raises(ValueError, match="sport changed"):
            import_activity(connection, summary, details, fit)
        assert (
            connection.execute(
                "SELECT sport FROM garmin_activities.activities WHERE activity_id = %s",
                (activity_id,),
            ).fetchone()[0]
            == before
        )
        raise RuntimeError("rollback")


@pytest.mark.skipif(
    not os.environ.get("FIT_IMPORT_TEST_DB"), reason="requires a disposable database"
)
def test_multisport_sessions_are_imported_atomically(monkeypatch, tmp_path):
    database = os.environ["FIT_IMPORT_TEST_DB"]
    assert database.startswith("weather_import_trial")
    start = datetime(2026, 1, 1, tzinfo=UTC)

    def message(**fields):
        return SimpleNamespace(fields=fields)

    fit = SimpleNamespace(
        session=[
            message(
                start_time=start,
                total_elapsed_time=time(0, 1),
                total_timer_time=time(0, 1),
                num_laps=1,
                sport="running",
            ),
            message(
                start_time=start + timedelta(minutes=1),
                total_elapsed_time=time(0, 1),
                total_timer_time=time(0, 1),
                num_laps=1,
                sport="cycling",
            ),
        ],
        record=[
            message(timestamp=start),
            message(timestamp=start + timedelta(minutes=1)),
            message(timestamp=start + timedelta(minutes=2)),
        ],
        lap=[
            message(
                start_time=start,
                total_elapsed_time=time(0, 1),
                total_timer_time=time(0, 1),
            ),
            message(
                start_time=start + timedelta(minutes=1),
                total_elapsed_time=time(0, 1),
                total_timer_time=time(0, 1),
            ),
        ],
        file_id=[message(serial_number=None)],
        device_info=[],
        hr_zones_timer=[
            message(
                hr_zones_timer_type=SimpleNamespace(name="session"),
                record_num=1,
                hr_zones_time=[
                    time.min,
                    time(0, 0, 10),
                    time.min,
                    time.min,
                    time.min,
                    time.min,
                ],
            ),
            message(
                hr_zones_timer_type=SimpleNamespace(name="lap"),
                record_num=1,
                hr_zones_time=[
                    time.min,
                    time(0, 0, 8),
                    time.min,
                    time.min,
                    time.min,
                    time.min,
                ],
            ),
        ],
        split=[],
        utc_datetime_to_local=lambda value: value.replace(tzinfo=None),
    )
    monkeypatch.setattr(importer, "File", lambda _: fit)
    monkeypatch.setattr(importer, "decode_multisport", lambda *_: fit)
    (tmp_path / "999999.fit").write_bytes(
        bytes.fromhex("0c100000010000002e46495400cffb")
    )
    summary = {
        "activityId": 999999,
        "startTimeLocal": "2026-01-01 00:00:00",
        "elapsedDuration": 120,
        "movingDuration": 120,
    }
    details = {"activityId": 999999}
    with (
        psycopg.connect(
            host=os.environ["FIT_IMPORT_TEST_HOST"],
            dbname=database,
            user="postgres",
            password=os.environ["FIT_IMPORT_TEST_PASSWORD"],
            sslmode="disable",
        ) as connection,
        pytest.raises(RuntimeError, match="rollback"),
        connection.transaction(),
    ):
        import_one = importer._import_session
        calls = []

        def fail_second(*args):
            calls.append(1)
            if len(calls) == 2:
                raise ValueError("second session failed")
            return import_one(*args)

        monkeypatch.setattr(importer, "_import_session", fail_second)
        with pytest.raises(ValueError, match="second session failed"):
            import_activity(connection, summary, details, tmp_path / "999999.fit")
        assert (
            connection.execute(
                "SELECT count(*) FROM garmin_activities.activities WHERE activity_id = ANY(%s)",
                (["999999", "999999_1", "999999_2"],),
            ).fetchone()[0]
            == 0
        )
        monkeypatch.setattr(importer, "_import_session", import_one)
        import_activity(connection, summary, details, tmp_path / "999999.fit")
        rows = connection.execute(
            "SELECT activity_id, sport FROM garmin_activities.activities WHERE activity_id = ANY(%s) ORDER BY activity_id",
            (["999999", "999999_1", "999999_2"],),
        ).fetchall()
        assert rows == [
            ("999999", "multisport"),
            ("999999_1", "running"),
            ("999999_2", "cycling"),
        ]
        assert connection.execute(
            "SELECT activity_id, count(*) FROM garmin_activities.activity_records WHERE activity_id = ANY(%s) GROUP BY activity_id ORDER BY activity_id",
            (["999999_1", "999999_2"],),
        ).fetchall() == [("999999_1", 1), ("999999_2", 2)]
        assert (
            connection.execute(
                "SELECT hrz_1_time::text FROM garmin_activities.activities WHERE activity_id = '999999_2'"
            ).fetchone()[0]
            == "00:00:10"
        )
        assert (
            connection.execute(
                "SELECT hrz_1_time::text FROM garmin_activities.activity_laps WHERE activity_id = '999999_2' AND lap = 0"
            ).fetchone()[0]
            == "00:00:08"
        )
        raise RuntimeError("rollback")


@pytest.mark.skipif(
    not os.environ.get("FIT_IMPORT_TEST_DB")
    or not os.environ.get("FIT_MULTISPORT_EXAMPLES"),
    reason="requires disposable database and official Garmin examples",
)
def test_official_multisport_examples_import_identically():
    database = os.environ["FIT_IMPORT_TEST_DB"]
    assert database.startswith("weather_import_trial")
    directory = Path(os.environ["FIT_MULTISPORT_EXAMPLES"])
    with (
        psycopg.connect(
            host=os.environ["FIT_IMPORT_TEST_HOST"],
            dbname=database,
            user="postgres",
            password=os.environ["FIT_IMPORT_TEST_PASSWORD"],
            sslmode="disable",
        ) as connection,
        pytest.raises(RuntimeError, match="rollback"),
        connection.transaction(),
    ):
        for activity_id in (99999991, 99999992):
            summary = {
                "activityId": activity_id,
                "startTimeLocal": "2023-09-02 08:15:24",
                "elapsedDuration": 7200,
                "movingDuration": 7200,
            }
            import_activity(
                connection,
                summary,
                {"activityId": activity_id},
                directory / f"{activity_id}.fit",
            )
        for index in range(1, 6):
            left = f"99999991_{index}"
            right = f"99999992_{index}"
            for table, ordering in (
                ("activity_records", "record"),
                ("activity_laps", "lap"),
            ):
                sql = f"SELECT to_jsonb(row) - 'activity_id' FROM (SELECT * FROM garmin_activities.{table} WHERE activity_id = %s ORDER BY {ordering}) row"
                assert (
                    connection.execute(sql, (left,)).fetchall()
                    == connection.execute(sql, (right,)).fetchall()
                )
        assert connection.execute(
            "SELECT sport FROM garmin_activities.activities WHERE activity_id LIKE '99999991_%' ORDER BY activity_id"
        ).fetchall() == [
            ("swimming",),
            ("transition",),
            ("cycling",),
            ("transition",),
            ("running",),
        ]
        assert connection.execute(
            "SELECT start_time FROM garmin_activities.activities WHERE activity_id = '99999991_1'"
        ).fetchone()[0] == datetime.fromisoformat("2023-09-02 08:15:24")
        assert (
            connection.execute(
                "SELECT count(*) FROM garmin.device_info WHERE file_id = '99999991'"
            ).fetchone()[0]
            > 0
        )
        assert (
            connection.execute(
                "SELECT count(*) FROM garmin_activities.activity_laps WHERE activity_id LIKE '99999991_%' AND (hrz_1_time > time '00:00' OR hrz_2_time > time '00:00' OR hrz_3_time > time '00:00' OR hrz_4_time > time '00:00' OR hrz_5_time > time '00:00')"
            ).fetchone()[0]
            > 0
        )
        assert (
            connection.execute(
                "SELECT count(*) FROM garmin_activities.activity_records WHERE activity_id LIKE '99999991_%'"
            ).fetchone()[0]
            == 4043
        )
        assert (
            connection.execute(
                "SELECT count(*) FROM garmin_activities.activity_laps WHERE activity_id LIKE '99999991_%'"
            ).fetchone()[0]
            == 11
        )
        raise RuntimeError("rollback")
