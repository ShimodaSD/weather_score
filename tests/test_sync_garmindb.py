import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

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
        "#!/bin/sh\n"
        'printf "%s\\n" "$PWD" > "$GARMIN_TEST_CWD"\n'
        'printf "%s\\n" "$*" > "$GARMIN_TEST_ARGS"\n'
    )
    fake_cli.chmod(0o755)
    environment = os.environ | {
        "HOME": str(home),
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
    fake_cli.write_text("#!/bin/sh\necho 'Failed to login!'\n")
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
