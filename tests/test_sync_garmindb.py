import json
import sqlite3
import sys
from pathlib import Path
from unittest.mock import MagicMock

import psycopg
import pytest

from scripts import sync_garmindb

SCRIPT = Path(__file__).parents[1] / "scripts" / "sync_garmindb.py"


@pytest.fixture(autouse=True)
def configure_personal_api(monkeypatch):
    monkeypatch.setenv("GARMIN_CONNECT", "test-key")


def test_generates_import_config_without_credentials(tmp_path, monkeypatch):
    source = tmp_path / "GarminConnectConfig.json"
    template = {
        "db": {"type": "sqlite"},
        "credentials": {"user": "runner", "password": "private"},
        "settings": {"metric": False},
    }
    source.write_text(json.dumps(template))
    monkeypatch.setenv("GARMINDB_CONFIG", str(source))
    target = tmp_path / "HealthData/DBs/garmin_activities.db"
    directory, config = sync_garmindb._get_garmin_config(target)
    generated = target.parent / "config/GarminConnectConfig.json"
    assert directory == target.parent.parent
    assert "credentials" not in config
    assert config["settings"] == {"metric": False}
    assert json.loads(generated.read_text()) == config
    assert generated.stat().st_mode & 0o777 == 0o600
    assert json.loads(source.read_text()) == template


def test_import_config_needs_no_existing_config(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    monkeypatch.delenv("GARMINDB_CONFIG", raising=False)
    target = tmp_path / "HealthData/DBs/garmin_activities.db"
    directory, config = sync_garmindb._get_garmin_config(target)
    assert directory == target.parent.parent
    assert config["settings"]["metric"] is True


def _create_database(path: Path, activities: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as database:
        if activities:
            database.execute("CREATE TABLE activities (id INTEGER PRIMARY KEY)")


def test_bootstraps_existing_sqlite_history(tmp_path):
    source = tmp_path / "existing/garmin_activities.db"
    target = tmp_path / "new/garmin_activities.db"
    _create_database(source, activities=True)
    sync_garmindb._bootstrap_database(target, source)
    assert sync_garmindb._validate_database(target, "activities")


def test_sqlite_uses_api_download_then_import_only(tmp_path, monkeypatch):
    import garmindb

    import weather_score.garmin as personal_api

    target = tmp_path / "HealthData/DBs/garmin_activities.db"
    monkeypatch.setenv("GARMINDB_PATH", str(target))
    config = MagicMock()
    config.config = {}
    config.get_activities_dir.return_value = str(tmp_path / "activities")
    monkeypatch.setattr(garmindb, "GarminConnectConfigManager", lambda _: config)
    download = MagicMock()
    monkeypatch.setattr(personal_api, "fetch_activities", download)
    run = MagicMock()
    monkeypatch.setattr(sync_garmindb, "_run_garmindb", run)
    sync_garmindb._sync_sqlite(tmp_path)
    download.assert_called_once_with(tmp_path / "activities")
    run.assert_called_once_with(
        tmp_path,
        [
            "--config",
            str(target.parent / "config"),
            "--activities",
            "--import",
        ],
    )
    _create_database(target, activities=True)
    sync_garmindb._sync_sqlite(tmp_path)
    assert download.call_args.args == (tmp_path / "activities",)


def test_api_failure_prevents_import(tmp_path, monkeypatch):
    import weather_score.garmin as personal_api

    target = tmp_path / "HealthData/DBs/garmin_activities.db"
    monkeypatch.setenv("GARMINDB_PATH", str(target))
    sync_garmindb._get_garmin_config(target)
    monkeypatch.setattr(
        personal_api, "fetch_activities", MagicMock(side_effect=ValueError("HTTP 401"))
    )
    run = MagicMock()
    monkeypatch.setattr(sync_garmindb, "_run_garmindb", run)
    with pytest.raises(SystemExit, match="HTTP 401"):
        sync_garmindb._sync_sqlite(tmp_path)
    run.assert_not_called()


def test_postgres_reuses_weather_connection_settings(monkeypatch) -> None:
    values = {
        "DB_USER": "weather-user",
        "DB_PASSWORD": "secret",
        "DB_HOST": "database.example",
        "DB_PORT": "5432",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)

    assert sync_garmindb._get_postgres_parameters("garmin") == {
        "user": "weather-user",
        "password": "secret",
        "host": "database.example",
        "port": "5432",
        "dbname": "garmin",
    }


@pytest.mark.parametrize("activities", ["garmin_activities.activities", None])
def test_startup_sync_detects_missing_activities_table(monkeypatch, activities) -> None:
    monkeypatch.setenv("DB_NAME", "weather")
    admin_connection = MagicMock()
    admin_connection.__enter__.return_value = admin_connection
    admin_connection.execute.return_value.fetchone.return_value = (1,)
    garmin_connection = MagicMock()
    garmin_connection.__enter__.return_value = garmin_connection
    garmin_connection.execute.return_value.fetchone.return_value = (activities,)
    monkeypatch.setattr(
        sync_garmindb, "_get_postgres_parameters", lambda name: {"dbname": name}
    )
    monkeypatch.setattr(
        sync_garmindb.psycopg,
        "connect",
        MagicMock(side_effect=[admin_connection, garmin_connection]),
    )

    assert sync_garmindb._postgres_sync_needed("garmin") is (activities is None)


def test_startup_sync_skips_import_when_initialized(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--if-needed"])
    monkeypatch.setenv("DB_NAME_GARMIN", "garmin")
    monkeypatch.setattr(sync_garmindb, "_postgres_sync_needed", lambda _: False)
    load_config = MagicMock()
    monkeypatch.setattr(sync_garmindb, "_get_garmin_config", load_config)

    sync_garmindb.main()

    load_config.assert_not_called()


def test_sync_requires_personal_api_key(monkeypatch):
    monkeypatch.setattr(sys, "argv", [str(SCRIPT)])
    monkeypatch.delenv("GARMIN_CONNECT")
    with pytest.raises(SystemExit, match="GARMIN_CONNECT"):
        sync_garmindb.main()


def test_copies_sqlite_activity_names_to_postgres(tmp_path, monkeypatch) -> None:
    source = tmp_path / "garmin_activities.db"
    with sqlite3.connect(source) as database:
        database.execute(
            "CREATE TABLE activities (activity_id TEXT PRIMARY KEY, name TEXT)"
        )
        database.executemany(
            "INSERT INTO activities VALUES (?, ?)",
            [("123", "Morning Run"), ("456", None)],
        )
    connection = MagicMock()
    connection.__enter__.return_value = connection
    cursor = connection.cursor.return_value
    cursor.__enter__.return_value = cursor
    monkeypatch.setattr(
        sync_garmindb.psycopg, "connect", MagicMock(return_value=connection)
    )
    monkeypatch.setattr(
        sync_garmindb,
        "_get_postgres_parameters",
        MagicMock(return_value={"dbname": "garmin"}),
    )

    copied = sync_garmindb._sync_postgres_activity_names(source, "garmin")

    assert copied == 1
    assert cursor.executemany.call_args.args[1] == [
        ("Morning Run", "123", "Morning Run")
    ]


def test_backfills_all_activity_tss_with_saved_threshold(monkeypatch) -> None:
    connection = MagicMock()
    connection.__enter__.return_value = connection
    cursor = connection.cursor.return_value
    cursor.__enter__.return_value = cursor
    cursor.fetchall.return_value = [
        ("run", "running", 160, 3600.0),
        ("bike", "cycling", 160, 1800.0),
        ("missing", "running", None, 3600.0),
        ("unsupported", "swimming", 160, 3600.0),
        ("invalid", "running", 160, -1.0),
    ]
    monkeypatch.setattr(sync_garmindb, "_fetch_tss_threshold", lambda: 160)
    monkeypatch.setattr(sync_garmindb, "_get_postgres_parameters", lambda _: {})
    monkeypatch.setattr(sync_garmindb.psycopg, "connect", lambda **_: connection)

    for _ in range(2):
        assert sync_garmindb._sync_postgres_activity_tss("garmin") == (2, 3)
        assert cursor.executemany.call_args.args[1] == [
            (100.0, "run", 100.0),
            (50.0, "bike", 50.0),
            (None, "missing", None),
            (None, "unsupported", None),
            (None, "invalid", None),
        ]
    assert "ADD COLUMN IF NOT EXISTS tss" in cursor.execute.call_args_list[0].args[0]
    assert "WHERE" not in cursor.execute.call_args_list[1].args[0]


@pytest.mark.parametrize(
    ("table", "profile", "expected"),
    [
        (None, None, 157),
        ("athlete_profile", None, 157),
        ("athlete_profile", (165,), 165),
    ],
)
def test_reads_tss_profile_threshold(monkeypatch, table, profile, expected) -> None:
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.execute.return_value.fetchone.side_effect = [(table,), profile]
    monkeypatch.setenv("DB_NAME", "weather")
    monkeypatch.setattr(sync_garmindb, "_get_postgres_parameters", lambda _: {})
    monkeypatch.setattr(sync_garmindb.psycopg, "connect", lambda **_: connection)

    assert sync_garmindb._fetch_tss_threshold() == expected


def test_tss_database_failure_fails_sync(monkeypatch) -> None:
    monkeypatch.setattr(
        sync_garmindb, "_fetch_tss_threshold", MagicMock(side_effect=psycopg.Error)
    )
    with pytest.raises(SystemExit, match="cannot calculate activity TSS"):
        sync_garmindb._sync_postgres_activity_tss("garmin")


@pytest.mark.parametrize("startup", [False, True])
def test_sync_updates_tss_after_activity_names(tmp_path, monkeypatch, startup) -> None:
    monkeypatch.setattr(
        sys, "argv", [str(SCRIPT), *(["--if-needed"] if startup else [])]
    )
    config = tmp_path / "GarminConnectConfig.json"
    config.write_text("{}")
    monkeypatch.setenv("GARMINDB_CONFIG", str(config))
    monkeypatch.setattr(sync_garmindb, "_postgres_sync_needed", lambda _: True)
    target = tmp_path / "garmin_activities.db"
    monkeypatch.setenv("GARMINDB_PATH", str(target))
    monkeypatch.setenv("DB_NAME_GARMIN", "garmin")
    monkeypatch.setattr(sync_garmindb, "_get_garmin_config", lambda _: (tmp_path, {}))
    for name in ("_bootstrap_database", "_sync_sqlite", "_import_postgres"):
        monkeypatch.setattr(sync_garmindb, name, MagicMock())
    monkeypatch.setattr(sync_garmindb, "_validate_database", lambda *_: True)
    updates = MagicMock()
    updates.prepare.return_value = True
    monkeypatch.setattr(sync_garmindb, "_prepare_postgres_database", updates.prepare)
    monkeypatch.setattr(sync_garmindb, "_sync_sqlite", updates.download)
    monkeypatch.setattr(sync_garmindb, "_import_postgres", updates.import_data)
    updates.names.return_value = 5
    updates.tss.return_value = (4, 1)
    monkeypatch.setattr(sync_garmindb, "_sync_postgres_activity_names", updates.names)
    monkeypatch.setattr(sync_garmindb, "_sync_postgres_activity_tss", updates.tss)

    sync_garmindb.main()
    assert [call[0] for call in updates.mock_calls] == [
        "prepare",
        "download",
        "import_data",
        "names",
        "tss",
    ]
    updates.download.assert_called_once_with(tmp_path.parent)
    updates.import_data.assert_called_once_with({}, tmp_path.parent, "garmin", True)


def test_initializes_all_postgres_tables(monkeypatch) -> None:
    import garmindb.garmindb as databases
    import garmindb.summarydb as summaries

    monkeypatch.setattr(
        sync_garmindb,
        "_get_postgres_parameters",
        lambda _: {
            "user": "user",
            "password": "test",
            "host": "localhost",
            "port": "5432",
        },
    )
    constructors = []
    for module, name in [
        (databases, "GarminDb"),
        (databases, "ActivitiesDb"),
        (databases, "MonitoringDb"),
        (databases, "GarminSummaryDb"),
        (summaries, "SummaryDb"),
    ]:
        constructor = MagicMock()
        monkeypatch.setattr(module, name, constructor)
        constructors.append(constructor)
    connection = MagicMock()
    monkeypatch.setattr(sync_garmindb.psycopg, "connect", connection)

    sync_garmindb._initialize_postgres_tables("garmin")

    for constructor in constructors:
        assert constructor.call_args.args[0].pg_database == "garmin"
        constructor.return_value.engine.dispose.assert_called_once()
    assert (
        "ADD COLUMN IF NOT EXISTS tss"
        in (connection.return_value.__enter__.return_value.execute.call_args.args[0])
    )


def test_postgres_initialization_failure_prevents_download(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", [str(SCRIPT)])
    monkeypatch.setenv("GARMINDB_PATH", str(tmp_path / "garmin_activities.db"))
    monkeypatch.setenv("DB_NAME_GARMIN", "garmin")
    monkeypatch.setattr(sync_garmindb, "_get_garmin_config", lambda _: (tmp_path, {}))
    monkeypatch.setattr(sync_garmindb, "_bootstrap_database", MagicMock())
    monkeypatch.setattr(
        sync_garmindb,
        "_prepare_postgres_database",
        MagicMock(side_effect=SystemExit("initialization failed")),
    )
    download = MagicMock()
    monkeypatch.setattr(sync_garmindb, "_sync_sqlite", download)

    with pytest.raises(SystemExit, match="initialization failed"):
        sync_garmindb.main()

    download.assert_not_called()


@pytest.mark.parametrize(
    "config", [{"db": None}, {"db": {"type": "postgresql"}}, {"data": None}]
)
def test_invalid_import_config_fails_cleanly(tmp_path, monkeypatch, config):
    source = tmp_path / "source.json"
    source.write_text(json.dumps(config))
    monkeypatch.setenv("GARMINDB_CONFIG", str(source))
    with pytest.raises(SystemExit, match="import config"):
        sync_garmindb._get_garmin_config(tmp_path / "DBs/garmin_activities.db")
