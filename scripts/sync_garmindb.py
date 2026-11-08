"""Download Garmin Personal API activities and import the existing databases."""

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Never
from urllib.parse import quote

import psycopg
from psycopg import sql

from weather_score.application.training_stress import calculate_activity_tss

DIRECT_IMPORT_VERSION = 1
TSS_SYNC_VERSION = 1


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
    config_path = target.parent / "config" / "GarminConnectConfig.json"
    default_source = Path.home() / ".GarminDb" / "GarminConnectConfig.json"
    source_path = Path(os.environ.get("GARMINDB_CONFIG", str(default_source)))
    if os.environ.get("GARMINDB_CONFIG") and not source_path.is_file():
        _fail_sync(f"cannot read GarminDB import config at {source_path}")
    try:
        config = json.loads(source_path.read_text()) if source_path.is_file() else {}
    except (OSError, json.JSONDecodeError) as error:
        _fail_sync(f"cannot read GarminDB import config at {source_path}: {error}")
    if (
        not isinstance(config, dict)
        or not isinstance(config.get("db", {}), dict)
        or config.get("db", {}).get("type", "sqlite") != "sqlite"
    ):
        _fail_sync("GarminDB import config must use SQLite")
    if not isinstance(config.get("data", {}), dict):
        _fail_sync("GarminDB import config data must be an object")
    config.pop("credentials", None)
    config["db"] = {"type": "sqlite"}
    config["directories"] = {
        "relative_to_home": False,
        "base_dir": str(target.parent.parent),
    }
    config.setdefault("settings", {"metric": True})
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(
        config_path, "w", opener=lambda path, flags: os.open(path, flags, 0o600)
    ) as output:
        config_path.chmod(0o600)
        json.dump(config, output, indent=2)

    return target.parent.parent, config


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
) -> None:
    command = [
        sys.executable,
        "-u",
        str(Path(__file__).with_name("import_garmindb.py")),
    ] + arguments
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
        print(line, end="", flush=True)
        upstream_failed |= any(marker in line.casefold() for marker in markers)
    if process.wait() != 0 or upstream_failed:
        _fail_sync("GarminDB operation failed; see the output above")


def _get_postgres_parameters(database_name: str) -> dict[str, str]:
    variables = {
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
        "dbname": database_name,
        "user": os.environ.get("DB_USER") or "postgres",
    }


def _prepare_postgres_database(database_name: str) -> bool:
    weather_database = os.environ.get("DB_NAME")
    if not weather_database:
        _fail_sync("missing PostgreSQL setting: DB_NAME")
    shared = database_name == weather_database
    if shared and os.environ.get("DB_SHARED_GARMIN") != "1":
        _fail_sync("DB_NAME_GARMIN must differ from DB_NAME")
    admin_parameters = _get_postgres_parameters(weather_database)
    try:
        if not shared:
            with psycopg.connect(**admin_parameters, autocommit=True) as connection:
                exists = connection.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s", (database_name,)
                ).fetchone()
                if not exists:
                    connection.execute(
                        sql.SQL("CREATE DATABASE {}").format(
                            sql.Identifier(database_name)
                        )
                    )
        with psycopg.connect(**_get_postgres_parameters(database_name)) as connection:
            schemas = {
                row[0]
                for row in connection.execute(
                    "SELECT schema_name FROM information_schema.schemata "
                    "WHERE schema_name = ANY(%s)",
                    (["garmin", "garmin_activities"],),
                )
            }
            populated = False
            if schemas == {"garmin", "garmin_activities"}:
                table = connection.execute(
                    "SELECT to_regclass('garmin_activities.activities')"
                ).fetchone()[0]
                if table:
                    populated = connection.execute(
                        "SELECT EXISTS (SELECT 1 FROM garmin_activities.activities)"
                    ).fetchone()[0]
    except psycopg.Error:
        _fail_sync("cannot create or inspect the Garmin PostgreSQL database")
    full_import = not populated
    _initialize_postgres_tables(database_name)
    return full_import


def _initialize_postgres_tables(database_name: str) -> None:
    """Create GarminDB tables before downloading any Garmin data."""
    if os.environ.get("DB_SHARED_GARMIN") == "1":
        try:
            from .garmindb_postgres import configure_schema_connections
        except ImportError:
            from garmindb_postgres import configure_schema_connections
        configure_schema_connections()

    from garmindb.garmindb import ActivitiesDb, GarminDb
    from idbutils import DbParams
    from sqlalchemy.exc import SQLAlchemyError

    parameters = _get_postgres_parameters(database_name)
    db_params = DbParams(
        db_type="postgresql",
        db_username=quote(parameters["user"], safe=""),
        db_password=quote(parameters["password"], safe=""),
        db_host=parameters["host"],
        db_port=int(parameters["port"]),
        pg_database=database_name,
    )
    try:
        for database_type in (GarminDb, ActivitiesDb):
            database = database_type(db_params)
            database.engine.dispose()
        with psycopg.connect(**parameters) as connection:
            connection.execute(
                "ALTER TABLE garmin_activities.activities "
                "ADD COLUMN IF NOT EXISTS tss double precision"
            )
    except psycopg.Error, SQLAlchemyError, RuntimeError:
        _fail_sync("cannot initialize Garmin PostgreSQL tables")


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
    config: dict[str, object],
    working_directory: Path,
    database_name: str,
    full_import: bool,
) -> None:
    try:
        with psycopg.connect(**_get_postgres_parameters(database_name)) as connection:
            version_columns = connection.execute(
                "SELECT table_schema, table_name, column_name FROM information_schema.columns "
                "WHERE (table_schema, table_name, column_name) IN "
                "(('garmin_activities', 'activities', 'import_fingerprint'), "
                "('public', 'athlete_profile', 'tss_sync_key'))"
            ).fetchall()
            if (
                "garmin_activities",
                "activities",
                "import_fingerprint",
            ) in version_columns:
                connection.execute(
                    "UPDATE garmin_activities.activities SET import_fingerprint = NULL "
                    "WHERE import_fingerprint IS NOT NULL"
                )
            if ("public", "athlete_profile", "tss_sync_key") in version_columns:
                connection.execute(
                    "UPDATE public.athlete_profile SET tss_sync_key = NULL "
                    "WHERE tss_sync_key IS NOT NULL"
                )
    except psycopg.Error:
        _fail_sync("cannot invalidate direct-import versions before GarminDB import")
    postgres_config = deepcopy(config)
    parameters = _get_postgres_parameters(database_name)
    postgres_config["db"] = {
        "type": "postgresql",
        "user": quote(parameters["user"], safe=""),
        "password": quote(parameters["password"], safe=""),
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
            "--activities",
            "--import",
            *([] if full_import else ["--latest"]),
        ]
        _run_garmindb(working_directory, arguments)

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
    except sqlite3.Error, psycopg.Error:
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


def _sync_postgres_activity_tss(
    database_name: str, *, threshold: int | None = None
) -> tuple[int, int]:
    """Backfill all recorded activities with the current profile's HR estimate."""
    try:
        if threshold is None:
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
                except TypeError, ValueError:
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
    """Fetch Personal API files, then run the local GarminDB parser only."""
    from zipfile import BadZipFile

    import requests
    from garmindb import GarminConnectConfigManager

    from weather_score.garmin import fetch_activities

    target = Path(os.environ["GARMINDB_PATH"]).expanduser()
    config_directory = target.parent / "config"
    config = GarminConnectConfigManager(str(config_directory))
    try:
        fetch_activities(Path(config.get_activities_dir()))
    except (requests.RequestException, ValueError, OSError, BadZipFile) as error:
        _fail_sync(f"Personal API download failed: {error}")
    _run_garmindb(
        working_directory,
        ["--config", str(config_directory), "--activities", "--import"],
    )


def _import_fingerprint(summary: Path, details: Path, fit: Path) -> str:
    """Hash the complete inputs and importer version without decoding FIT files."""
    if fit.stat().st_size > 128 * 1024 * 1024:
        raise ValueError("FIT file exceeds 128 MiB")
    digest = hashlib.sha256(
        f"weather-score-direct-import-v{DIRECT_IMPORT_VERSION}\0".encode()
    )
    for path in (summary, details, fit):
        digest.update(path.name.encode())
        digest.update(b"\0")
        with path.open("rb") as source:
            digest.update(hashlib.file_digest(source, "sha256").digest())
    return digest.hexdigest()


def _sync_direct(target: Path, database_name: str) -> None:
    """Download and import activities directly into a shared PostgreSQL database."""
    from zipfile import BadZipFile

    import requests

    from weather_score.garmin import fetch_activities
    from weather_score.garmin_activity_import import import_activity

    if os.environ.get("DB_SHARED_GARMIN") != "1" or database_name != os.environ.get(
        "DB_NAME"
    ):
        _fail_sync(
            "direct import requires the app and Garmin tables in the same database"
        )
    try:
        with psycopg.connect(**_get_postgres_parameters(database_name)) as connection:
            if not connection.execute(
                "SELECT to_regclass('public.activity_grades')"
            ).fetchone()[0]:
                _fail_sync("direct import requires activity grade storage")
            columns = connection.execute(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_schema = 'garmin_activities' AND table_name = 'steps_activities' "
                "AND column_name IN ('avg_steps_per_min', 'max_steps_per_min')"
            ).fetchall()
            if dict(columns) != {
                "avg_steps_per_min": "double precision",
                "max_steps_per_min": "double precision",
            }:
                _fail_sync(
                    "direct import requires fractional cadence columns; migrate the schema first"
                )
            version_columns = connection.execute(
                "SELECT table_schema, table_name, column_name, data_type FROM information_schema.columns "
                "WHERE (table_schema, table_name, column_name) IN "
                "(('garmin_activities', 'activities', 'import_fingerprint'), "
                "('public', 'athlete_profile', 'tss_sync_key'))"
            ).fetchall()
            if set(version_columns) != {
                ("garmin_activities", "activities", "import_fingerprint", "text"),
                ("public", "athlete_profile", "tss_sync_key", "text"),
            }:
                _fail_sync("direct import requires the import-version schema migration")
            profile = connection.execute(
                "SELECT threshold_heart_rate_bpm, tss_sync_key FROM public.athlete_profile WHERE id = 1"
            ).fetchone()
            if profile is None:
                connection.execute(
                    "INSERT INTO public.athlete_profile (id) VALUES (1) ON CONFLICT (id) DO NOTHING"
                )
                profile = connection.execute(
                    "SELECT threshold_heart_rate_bpm, tss_sync_key FROM public.athlete_profile WHERE id = 1"
                ).fetchone()
            threshold = profile[0]
            if not 30 <= threshold <= 250:
                _fail_sync("profile threshold must be between 30 and 250 bpm")
            connection.commit()
            directory = target.parent.parent / "FitFiles" / "Activities"
            fetch_activities(directory, refresh_changed=True)
            fingerprints = dict(
                connection.execute(
                    "SELECT activity_id, import_fingerprint FROM garmin_activities.activities "
                    "WHERE import_fingerprint IS NOT NULL"
                ).fetchall()
            )
            connection.commit()
            count = 0
            skipped = 0
            for summary_path in sorted(directory.glob("activity_[0-9]*.json")):
                summary = json.loads(summary_path.read_text())
                if not isinstance(summary, dict):
                    raise TypeError("Invalid activity summary file")
                activity_id = summary.get("activityId")
                if (
                    not isinstance(activity_id, int)
                    or isinstance(activity_id, bool)
                    or activity_id <= 0
                    or summary_path.name != f"activity_{activity_id}.json"
                ):
                    raise ValueError("Invalid activity summary file")
                details_path = directory / f"activity_details_{activity_id}.json"
                fit = next(
                    (
                        path
                        for path in (
                            directory / f"{activity_id}.fit",
                            directory / f"{activity_id}_ACTIVITY.fit",
                        )
                        if path.is_file()
                    ),
                    None,
                )
                if fit is None:
                    raise ValueError("Activity FIT file is missing")
                fingerprint = _import_fingerprint(summary_path, details_path, fit)
                if fingerprints.get(str(activity_id)) == fingerprint:
                    skipped += 1
                    continue
                summary = json.loads(summary_path.read_text())
                if (
                    not isinstance(summary, dict)
                    or summary.get("activityId") != activity_id
                ):
                    raise ValueError("Activity summary changed during import")
                details = json.loads(details_path.read_text())
                if not isinstance(details, dict):
                    raise TypeError("Invalid activity details file")
                with connection.transaction():
                    import_activity(
                        connection,
                        summary,
                        details,
                        fit,
                        threshold_heart_rate_bpm=threshold,
                    )
                    if (
                        _import_fingerprint(summary_path, details_path, fit)
                        != fingerprint
                    ):
                        raise ValueError("Activity input changed during import")
                    connection.execute(
                        "UPDATE garmin_activities.activities SET import_fingerprint = %s WHERE activity_id = %s",
                        (fingerprint, str(activity_id)),
                    )
                count += 1
            profile = connection.execute(
                "SELECT threshold_heart_rate_bpm, tss_sync_key FROM public.athlete_profile WHERE id = 1"
            ).fetchone()
            if profile is None:
                raise ValueError("Athlete profile disappeared during sync")
            threshold, synced_tss_key = profile
            if not 30 <= threshold <= 250:
                _fail_sync("profile threshold must be between 30 and 250 bpm")
            tss_key = f"heart-rate-tss-v{TSS_SYNC_VERSION}:{threshold}"
    except (
        psycopg.Error,
        requests.RequestException,
        ValueError,
        TypeError,
        OSError,
        BadZipFile,
    ) as error:
        _fail_sync(f"direct activity import failed: {error}")
    if synced_tss_key != tss_key:
        with psycopg.connect(**_get_postgres_parameters(database_name)) as connection:
            marked = connection.execute(
                "UPDATE public.athlete_profile SET tss_sync_key = NULL "
                "WHERE id = 1 AND threshold_heart_rate_bpm = %s RETURNING id",
                (threshold,),
            ).fetchone()
        if marked is None:
            _fail_sync("profile changed during sync; retry to update TSS")
        with psycopg.connect(**_get_postgres_parameters(database_name)) as connection:
            profile = connection.execute(
                "SELECT threshold_heart_rate_bpm, tss_sync_key FROM public.athlete_profile WHERE id = 1 FOR UPDATE"
            ).fetchone()
            if profile is None or profile[0] != threshold:
                _fail_sync("profile changed during sync; retry to update TSS")
            if profile[1] != tss_key:
                scored, excluded = _sync_postgres_activity_tss(
                    database_name, threshold=threshold
                )
                connection.execute(
                    "UPDATE public.athlete_profile SET tss_sync_key = %s WHERE id = 1",
                    (tss_key,),
                )
                print(
                    f"garmin-sync: TSS calculated for {scored} activities; {excluded} unavailable"
                )
    print(f"garmin-sync: imported {count} activities; skipped {skipped} unchanged")


def main() -> None:
    """Bootstrap a GarminDB checkpoint when needed and run an incremental refresh."""
    importer = os.environ.get("GARMIN_IMPORTER", "garmindb")
    if importer not in {"garmindb", "direct"}:
        _fail_sync("GARMIN_IMPORTER must be garmindb or direct")
    if importer == "direct":
        if "--if-needed" in sys.argv[1:]:
            print("garmin-sync: direct importer does not run at startup")
            return
        target = os.environ.get("GARMINDB_PATH")
        database_name = os.environ.get("DB_NAME_GARMIN")
        if not target or not database_name:
            _fail_sync("direct import requires GARMINDB_PATH and DB_NAME_GARMIN")
        _sync_direct(Path(target).expanduser().resolve(), database_name)
        return
    if "--if-needed" in sys.argv[1:]:
        database_name = os.environ.get("DB_NAME_GARMIN")
        if not database_name:
            _fail_sync("missing PostgreSQL setting: DB_NAME_GARMIN")
        if not _postgres_sync_needed(database_name):
            print("garmin-sync: PostgreSQL is initialized; skipping startup import")
            return
        print("garmin-sync: initializing GarminDB before API startup", flush=True)
    if not os.environ.get("GARMIN_CONNECT", "").strip():
        _fail_sync("set GARMIN_CONNECT to a Garmin Personal API key")
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
    postgres_database = os.environ.get("DB_NAME_GARMIN")
    if postgres_database:
        full_import = _prepare_postgres_database(postgres_database)
    _sync_sqlite(data_directory.parent)
    if not _validate_database(target, "activities"):
        _fail_sync(f"refresh did not create a valid activities database at {target}")
    if postgres_database:
        _import_postgres(config, data_directory.parent, postgres_database, full_import)
        names = _sync_postgres_activity_names(target, postgres_database)
        print(f"garmin-sync: copied {names} activity names to PostgreSQL")
        scored, excluded = _sync_postgres_activity_tss(postgres_database)
        print(
            f"garmin-sync: calculated TSS for {scored} activities; {excluded} unavailable"
        )
    print(f"garmin-sync: ready: {target}")


if __name__ == "__main__":
    main()
