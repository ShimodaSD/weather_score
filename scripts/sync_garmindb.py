"""Bootstrap and incrementally refresh the configured GarminDB databases."""

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Never

import psycopg
from psycopg import sql
from weather_score.application.training_stress import calculate_activity_tss


def _fail_sync(message: str) -> Never:
    raise SystemExit(f"garmin-sync: {message}")


def _validate_database(path: Path, required_table: str | None = None) -> bool:
    if not path.is_file():
        return False
    try:
        with sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True) as database:
            if database.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                return False
            if (
                required_table
                and database.execute(
                    "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                    (required_table,),
                ).fetchone()
                is None
            ):
                return False
    except sqlite3.Error:
        return False
    return True


def _get_garmin_config(target: Path) -> tuple[Path, dict[str, object]]:
    config_path = Path.home() / ".GarminDb" / "GarminConnectConfig.json"
    source_path = Path(os.environ.get("GARMINDB_CONFIG", str(config_path)))
    try:
        config = json.loads(source_path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        _fail_sync(f"cannot read GarminDB config at {source_path}: {error}")

    if (
        not isinstance(config, dict)
        or config.get("db", {}).get("type", "sqlite") != "sqlite"
    ):
        _fail_sync("GarminDB config must use SQLite")

    if os.environ.get("GARMINDB_CONFIG"):
        credentials = config.get("credentials")
        if not isinstance(credentials, dict) or not credentials.get("user"):
            _fail_sync("set credentials.user in GarminConnectConfig.json")
        password = os.environ.get("SECRET_GARMIN") or credentials.get("password")
        if not password:
            _fail_sync("set SECRET_GARMIN in .env")
        credentials.update(
            password=password, secure_password=False, password_file=None
        )
        config["directories"] = {
            "relative_to_home": False,
            "base_dir": str(target.parent.parent),
        }
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(
            config_path, "w", opener=lambda path, flags: os.open(path, flags, 0o600)
        ) as output:
            config_path.chmod(0o600)
            json.dump(config, output, indent=2)

    directories = config.get("directories", {})
    configured = Path(directories.get("base_dir", "HealthData")).expanduser()
    if not configured.is_absolute():
        configured = (
            Path.home() / configured
            if directories.get("relative_to_home", True)
            else target.parent.parent.parent / configured
        )
    if configured.resolve() != target.parent.parent.resolve():
        _fail_sync(
            "GARMINDB_PATH does not match directories.base_dir in GarminDB config"
        )
    return configured, config


def _bootstrap_database(target: Path, source: Path | None) -> None:
    if target.exists():
        if not _validate_database(target, "activities"):
            _fail_sync(f"existing database is invalid: {target}")
        return
    if source is None:
        target.parent.mkdir(parents=True, exist_ok=True)
        return
    if not _validate_database(source, "activities"):
        _fail_sync(f"bootstrap database is invalid or lacks activities: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    with (
        sqlite3.connect(f"{source.as_uri()}?mode=ro", uri=True) as source_db,
        sqlite3.connect(target) as target_db,
    ):
        source_db.backup(target_db)


def _run_garmindb(
    working_directory: Path,
    arguments: list[str],
    normalize_activity_ids: bool = False,
) -> None:
    command = (
        [sys.executable, "-u", str(Path(__file__).with_name("import_garmindb.py"))]
        if normalize_activity_ids
        else ["garmindb_cli.py"]
    ) + arguments
    markers = (
        "failed to login",
        "failed to download",
        "traceback (most recent call last)",
    )
    try:
        process = subprocess.Popen(
            command,
            cwd=working_directory,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except OSError as error:
        _fail_sync(f"cannot start GarminDB: {error}")

    upstream_failed = False
    assert process.stdout is not None
    for line in process.stdout:
        print(line, end="")
        upstream_failed |= any(marker in line.casefold() for marker in markers)
    if process.wait() != 0 or upstream_failed:
        _fail_sync("GarminDB operation failed; see the output above")


def _get_postgres_parameters(database_name: str) -> dict[str, str]:
    variables = {
        "user": "DB_USER",
        "password": "DB_PASSWORD",
        "host": "DB_HOST",
        "port": "DB_PORT",
    }
    missing = [
        variable for variable in variables.values() if not os.environ.get(variable)
    ]
    if missing:
        _fail_sync(f"missing PostgreSQL settings: {', '.join(missing)}")
    return {key: os.environ[variable] for key, variable in variables.items()} | {
        "dbname": database_name
    }


def _prepare_postgres_database(database_name: str) -> bool:
    weather_database = os.environ.get("DB_NAME")
    if not weather_database:
        _fail_sync("missing PostgreSQL setting: DB_NAME")
    if database_name == weather_database:
        _fail_sync("DB_NAME_GARMIN must differ from DB_NAME")
    admin_parameters = _get_postgres_parameters(weather_database)
    try:
        with psycopg.connect(**admin_parameters, autocommit=True) as connection:
            exists = connection.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (database_name,)
            ).fetchone()
            if not exists:
                connection.execute(
                    sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name))
                )
        with psycopg.connect(**_get_postgres_parameters(database_name)) as connection:
            schemas = {
                row[0]
                for row in connection.execute(
                    "SELECT schema_name FROM information_schema.schemata "
                    "WHERE schema_name = ANY(%s)",
                    (["garmin", "garmin_activities", "garmin_monitoring"],),
                )
            }
    except psycopg.Error:
        _fail_sync("cannot create or inspect the Garmin PostgreSQL database")
    return schemas != {"garmin", "garmin_activities", "garmin_monitoring"}


def _postgres_sync_needed(database_name: str) -> bool:
    weather_database = os.environ.get("DB_NAME")
    if not weather_database:
        _fail_sync("missing PostgreSQL setting: DB_NAME")
    admin_parameters = _get_postgres_parameters(weather_database)
    try:
        with psycopg.connect(**admin_parameters, autocommit=True) as connection:
            exists = connection.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (database_name,)
            ).fetchone()
        if not exists:
            return True
        with psycopg.connect(**_get_postgres_parameters(database_name)) as connection:
            activities = connection.execute(
                "SELECT to_regclass('garmin_activities.activities')"
            ).fetchone()[0]
    except psycopg.Error:
        _fail_sync("cannot inspect the Garmin PostgreSQL database")
    return not activities


def _import_postgres(
    config: dict[str, object], working_directory: Path, database_name: str
) -> None:
    full_import = _prepare_postgres_database(database_name)
    postgres_config = deepcopy(config)
    parameters = _get_postgres_parameters(database_name)
    postgres_config["db"] = {
        "type": "postgresql",
        "user": parameters["user"],
        "password": parameters["password"],
        "host": parameters["host"],
        "port": int(parameters["port"]),
        "database": database_name,
    }
    with tempfile.TemporaryDirectory(prefix="weather-score-garmindb-") as directory:
        config_path = Path(directory) / "GarminConnectConfig.json"
        config_path.write_text(json.dumps(postgres_config))
        config_path.chmod(0o600)
        arguments = [
            "--config",
            directory,
            "--all",
            "--import",
            *([] if full_import else ["--latest"]),
        ]
        _run_garmindb(working_directory, arguments, normalize_activity_ids=True)

    try:
        with psycopg.connect(**_get_postgres_parameters(database_name)) as connection:
            count = connection.execute(
                "SELECT COUNT(*) FROM garmin_activities.activities"
            ).fetchone()
    except psycopg.Error:
        _fail_sync("Garmin PostgreSQL import validation failed")
    if not count or count[0] == 0:
        _fail_sync("Garmin PostgreSQL activities table is empty")


def _sync_postgres_activity_names(target: Path, database_name: str) -> int:
    """Copy names that GarminDB's PostgreSQL JSON importer cannot update."""
    try:
        with sqlite3.connect(f"{target.as_uri()}?mode=ro", uri=True) as source:
            names = source.execute(
                "SELECT CAST(activity_id AS TEXT), name FROM activities "
                "WHERE name IS NOT NULL"
            ).fetchall()
        with (
            psycopg.connect(**_get_postgres_parameters(database_name)) as connection,
            connection.cursor() as cursor,
        ):
            cursor.executemany(
                "UPDATE garmin_activities.activities SET name = %s "
                "WHERE activity_id = %s AND name IS DISTINCT FROM %s",
                [(name, activity_id, name) for activity_id, name in names],
            )
    except (sqlite3.Error, psycopg.Error):
        _fail_sync("cannot copy activity names to Garmin PostgreSQL")
    return len(names)


def _fetch_tss_threshold() -> int:
    """Read the saved profile threshold, defaulting for an unconfigured profile."""
    database_name = os.environ.get("DB_NAME")
    if not database_name:
        _fail_sync("set DB_NAME to read the TSS profile")
    with psycopg.connect(**_get_postgres_parameters(database_name)) as connection:
        if connection.execute("SELECT to_regclass('athlete_profile')").fetchone()[0]:
            profile = connection.execute(
                "SELECT threshold_heart_rate_bpm FROM athlete_profile WHERE id = 1"
            ).fetchone()
            if profile:
                return profile[0]
    return 157


def _sync_postgres_activity_tss(database_name: str) -> tuple[int, int]:
    """Backfill all recorded activities with the current profile's HR estimate."""
    try:
        threshold = _fetch_tss_threshold()
        if not 30 <= threshold <= 250:
            _fail_sync("profile threshold must be between 30 and 250 bpm")
        with (
            psycopg.connect(**_get_postgres_parameters(database_name)) as connection,
            connection.cursor() as cursor,
        ):
            cursor.execute(
                "ALTER TABLE garmin_activities.activities "
                "ADD COLUMN IF NOT EXISTS tss double precision"
            )
            cursor.execute(
                "SELECT activity_id, sport, avg_hr, "
                "EXTRACT(EPOCH FROM elapsed_time)::double precision "
                "FROM garmin_activities.activities"
            )
            updates = []
            scored = 0
            for activity_id, sport, average_hr, elapsed_seconds in cursor.fetchall():
                try:
                    tss = calculate_activity_tss(
                        sport,
                        threshold_heart_rate_bpm=threshold,
                        average_heart_rate_bpm=average_hr,
                        elapsed_seconds=elapsed_seconds,
                    )["tss"]
                    scored += 1
                except (TypeError, ValueError):
                    tss = None
                updates.append((tss, activity_id, tss))
            cursor.executemany(
                "UPDATE garmin_activities.activities SET tss = %s "
                "WHERE activity_id = %s AND tss IS DISTINCT FROM %s",
                updates,
            )
    except psycopg.Error:
        _fail_sync("cannot calculate activity TSS in Garmin PostgreSQL")
    return scored, len(updates) - scored


def _sync_sqlite(working_directory: Path) -> None:
    _run_garmindb(
        working_directory,
        [
            "--activities",
            "--download",
            "--import",
            "--latest",
        ],
    )


def main() -> None:
    """Bootstrap a GarminDB checkpoint when needed and run an incremental refresh."""
    if "--if-needed" in sys.argv[1:]:
        database_name = os.environ.get("DB_NAME_GARMIN")
        if not database_name:
            _fail_sync("missing PostgreSQL setting: DB_NAME_GARMIN")
        if not _postgres_sync_needed(database_name):
            print("garmin-sync: PostgreSQL is initialized; skipping startup import")
            return
        config_path = Path(
            os.environ.get(
                "GARMINDB_CONFIG",
                Path.home() / ".GarminDb" / "GarminConnectConfig.json",
            )
        )
        if not config_path.is_file():
            _fail_sync(f"startup import requires GarminDB config: {config_path}")
        print("garmin-sync: initializing GarminDB before API startup", flush=True)
    configured_target = os.environ.get("GARMINDB_PATH")
    if not configured_target:
        _fail_sync("set GARMINDB_PATH to garmin_activities.db")
    target = Path(configured_target).expanduser().resolve()
    if target.name != "garmin_activities.db":
        _fail_sync("GARMINDB_PATH must end with garmin_activities.db")

    data_directory, config = _get_garmin_config(target)
    configured_source = os.environ.get("GARMINDB_BOOTSTRAP_PATH")
    source = (
        Path(configured_source).expanduser().resolve() if configured_source else None
    )
    _bootstrap_database(target, source)
    _sync_sqlite(data_directory.parent)
    if not _validate_database(target, "activities"):
        _fail_sync(f"refresh did not create a valid activities database at {target}")
    postgres_database = os.environ.get("DB_NAME_GARMIN")
    if postgres_database:
        _import_postgres(config, data_directory.parent, postgres_database)
        names = _sync_postgres_activity_names(target, postgres_database)
        print(f"garmin-sync: copied {names} activity names to PostgreSQL")
        scored, excluded = _sync_postgres_activity_tss(postgres_database)
        print(f"garmin-sync: calculated TSS for {scored} activities; {excluded} unavailable")
    print(f"garmin-sync: ready: {target}")


if __name__ == "__main__":
    main()
