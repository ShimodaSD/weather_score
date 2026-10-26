import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import psycopg
import pytest
from scripts import sync_garmindb

SCRIPT = Path(__file__).parents[1] / "scripts" / "sync_garmindb.py"


def test_generates_private_config_from_environment(tmp_path, monkeypatch):
    source = tmp_path / "GarminConnectConfig.json"
    template = {
        "db": {"type": "sqlite"},
        "credentials": {"user": "runner", "password_file": "/outside/password"},
        "directories": {"base_dir": "/outside/data"},
    }
    source.write_text(json.dumps(template))
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    monkeypatch.setenv("GARMINDB_CONFIG", str(source))
    monkeypatch.delenv("SECRET_GARMIN", raising=False)
    target = tmp_path / "HealthData" / "DBs" / "garmin_activities.db"
    with pytest.raises(SystemExit, match="set SECRET_GARMIN"):
        sync_garmindb._get_garmin_config(target)
    monkeypatch.setenv("SECRET_GARMIN", "test-password")
    directory, config = sync_garmindb._get_garmin_config(target)
    generated = tmp_path / "home/.GarminDb/GarminConnectConfig.json"
    assert directory == target.parent.parent
    assert json.loads(generated.read_text()) == config
    assert config["credentials"] == {
        "user": "runner", "password": "test-password",
        "password_file": None, "secure_password": False,
    }
    assert generated.stat().st_mode & 0o777 == 0o600
    assert json.loads(source.read_text()) == template


def test_uses_password_from_private_config_when_environment_secret_is_unset(
    tmp_path, monkeypatch
):
    source = tmp_path / "GarminConnectConfig.json"
    source.write_text(
        json.dumps(
            {
                "db": {"type": "sqlite"},
                "credentials": {"user": "runner", "password": "private"},
                "directories": {"base_dir": "/outside/data"},
            }
        )
    )
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    monkeypatch.setenv("GARMINDB_CONFIG", str(source))
    monkeypatch.delenv("SECRET_GARMIN", raising=False)

    _, config = sync_garmindb._get_garmin_config(
        tmp_path / "HealthData" / "DBs" / "garmin_activities.db"
    )

    assert config["credentials"] == {
        "user": "runner",
        "password": "private",
        "password_file": None,
        "secure_password": False,
    }


def _create_database(path: Path, activities: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as database:
        if activities:
            database.execute("CREATE TABLE activities (id INTEGER PRIMARY KEY)")


def _create_environment(tmp_path: Path) -> tuple[dict[str, str], Path, Path]:
    home = tmp_path / "home"
    destination = tmp_path / "destination"
    target = destination / "HealthData" / "DBs" / "garmin_activities.db"
    config_dir = home / ".GarminDb"
    config_dir.mkdir(parents=True)
    (config_dir / "GarminConnectConfig.json").write_text(
        json.dumps(
            {
                "db": {"type": "sqlite"},
                "directories": {"relative_to_home": False, "base_dir": "HealthData"},
            }
        )
    )

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_cli = bin_dir / "garmindb_cli.py"
    fake_cli.write_text(
        "import os, sys\nfrom pathlib import Path\n"
        'Path(os.environ["GARMIN_TEST_CWD"]).write_text(os.getcwd())\n'
        'Path(os.environ["GARMIN_TEST_ARGS"]).write_text(" ".join(sys.argv[1:]))\n'
    )
    (bin_dir / "garmindb.py").write_text(
        "class Download:\n"
        "    get_activities = _Download__get_activity_summaries = lambda *args: None\n"
        "    save_json_to_file = save_binary_file = lambda *args: None\n"
    )
    fake_cli.chmod(0o755)
    environment = os.environ | {
        "HOME": str(home),
        "PYTHONPATH": str(bin_dir),
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "GARMINDB_PATH": str(target),
        "GARMIN_TEST_CWD": str(tmp_path / "cwd"),
        "GARMIN_TEST_ARGS": str(tmp_path / "args"),
    }
    environment.pop("DB_NAME_GARMIN", None)
    environment.pop("GARMINDB_CONFIG", None)
    return environment, target, destination


def test_bootstraps_and_runs_incremental_refresh(tmp_path: Path) -> None:
    environment, target, destination = _create_environment(tmp_path)
    source = tmp_path / "existing" / "garmin_activities.db"
    _create_database(source, activities=True)
    environment["GARMINDB_BOOTSTRAP_PATH"] = str(source)

    result = subprocess.run(
        [sys.executable, SCRIPT],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert target.is_file()
    assert (tmp_path / "cwd").read_text().strip() == str(destination)
    assert (tmp_path / "args").read_text().strip() == (
        "--activities --download --import --latest"
    )


def test_returns_failure_when_upstream_hides_login_error(tmp_path: Path) -> None:
    environment, target, _ = _create_environment(tmp_path)
    _create_database(target, activities=True)
    fake_cli = Path(environment["PATH"].split(os.pathsep)[0]) / "garmindb_cli.py"
    fake_cli.write_text("print('Failed to login!')\n")
    fake_cli.chmod(0o755)

    result = subprocess.run(
        [sys.executable, SCRIPT],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "GarminDB operation failed" in result.stderr


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


def test_startup_sync_fails_when_garmin_config_is_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--if-needed"])
    monkeypatch.setenv("DB_NAME_GARMIN", "garmin")
    monkeypatch.setenv("GARMINDB_CONFIG", str(tmp_path / "missing.json"))
    monkeypatch.setattr(sync_garmindb, "_postgres_sync_needed", lambda _: True)

    with pytest.raises(SystemExit, match="startup import requires GarminDB config"):
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
    [(None, None, 157), ("athlete_profile", None, 157), ("athlete_profile", (165,), 165)],
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
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), *(["--if-needed"] if startup else [])])
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
        "prepare", "download", "import_data", "names", "tss"
    ]
    updates.download.assert_called_once_with(tmp_path.parent)
    updates.import_data.assert_called_once_with({}, tmp_path.parent, "garmin", True)


def test_initializes_all_postgres_tables(monkeypatch) -> None:
    import garmindb.garmindb as databases
    import garmindb.summarydb as summaries

    monkeypatch.setattr(
        sync_garmindb, "_get_postgres_parameters",
        lambda _: {"user": "user", "password": "test", "host": "localhost", "port": "5432"},
    )
    constructors = []
    for module, name in [
        (databases, "GarminDb"), (databases, "ActivitiesDb"),
        (databases, "MonitoringDb"), (databases, "GarminSummaryDb"),
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
    assert "ADD COLUMN IF NOT EXISTS tss" in (
        connection.return_value.__enter__.return_value.execute.call_args.args[0]
    )


def test_postgres_initialization_failure_prevents_download(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", [str(SCRIPT)])
    monkeypatch.setenv("GARMINDB_PATH", str(tmp_path / "garmin_activities.db"))
    monkeypatch.setenv("DB_NAME_GARMIN", "garmin")
    monkeypatch.setattr(sync_garmindb, "_get_garmin_config", lambda _: (tmp_path, {}))
    monkeypatch.setattr(sync_garmindb, "_bootstrap_database", MagicMock())
    monkeypatch.setattr(
        sync_garmindb, "_prepare_postgres_database",
        MagicMock(side_effect=SystemExit("initialization failed")),
    )
    download = MagicMock()
    monkeypatch.setattr(sync_garmindb, "_sync_sqlite", download)

    with pytest.raises(SystemExit, match="initialization failed"):
        sync_garmindb.main()

    download.assert_not_called()
