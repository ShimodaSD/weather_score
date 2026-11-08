"""Archive a verified Supabase snapshot locally before removing expired rows."""

import hashlib
import os
import subprocess
import sys
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path

import psycopg
from dotenv import dotenv_values
from psycopg import sql

try:
    from .retention_policy import ACTIVITY_TABLES, DATED_TABLES, dated_delete
except ImportError:
    from retention_policy import ACTIVITY_TABLES, DATED_TABLES, dated_delete

ROOT = Path(os.environ.get("WEATHER_SCORE_ROOT", Path(__file__).resolve().parents[1])).resolve()
SCHEMAS = (
    "public",
    "garmin",
    "garmin_activities",
    "garmin_monitoring",
    "garmin_summary",
    "summary",
)
EXPECTED = {
    "public": {"activity_grades", "athlete_profile"},
    "garmin": {"_attributes", "attributes", "devices", "files"}
    | set(DATED_TABLES["garmin"]),
    "garmin_activities": {"_attributes", "activities", *ACTIVITY_TABLES},
    "garmin_monitoring": {"_attributes"} | set(DATED_TABLES["garmin_monitoring"]),
    "garmin_summary": {"_attributes", "summary"} | set(DATED_TABLES["garmin_summary"]),
    "summary": {"_attributes", "summary"} | set(DATED_TABLES["summary"]),
}


def docker(
    *args: str, input_text: str | None = None, timeout: int = 1200
) -> subprocess.CompletedProcess:
    """Run Docker without printing credentials or archived data."""
    result = subprocess.run(
        ["docker", "compose", *args],
        cwd=ROOT,
        input=input_text,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(f"Docker command failed: {args[0]}")
    return result


def tables(connection: psycopg.Connection) -> set[tuple[str, str]]:
    rows = connection.execute(
        "SELECT table_schema, table_name FROM information_schema.tables "
        "WHERE table_type = 'BASE TABLE' AND table_schema = ANY(%s)",
        (list(SCHEMAS),),
    ).fetchall()
    actual = set(rows)
    expected = {(schema, name) for schema, names in EXPECTED.items() for name in names}
    optional = {("public", "garmin_activities")}
    if not expected <= actual or actual - expected - optional:
        raise RuntimeError(
            "Database tables changed; review retention policy before archiving"
        )
    return actual


def has_expired(connection: psycopg.Connection, cutoff: datetime) -> bool:
    if connection.execute(
        "SELECT EXISTS (SELECT 1 FROM garmin_activities.activities WHERE start_time < %s)",
        (cutoff,),
    ).fetchone()[0]:
        return True
    if connection.execute(
        "SELECT EXISTS (SELECT 1 FROM public.activity_grades g "
        "WHERE g.created_at < (%s::timestamp AT TIME ZONE 'America/Sao_Paulo') "
        "AND g.status <> 'processing' AND NOT EXISTS "
        "(SELECT 1 FROM garmin_activities.activities a WHERE a.activity_id = g.activity_id))",
        (cutoff,),
    ).fetchone()[0]:
        return True
    for schema, definitions in DATED_TABLES.items():
        for table, (column, period) in definitions.items():
            end = sql.Identifier(column)
            if period:
                end = sql.SQL("{} + {}::interval").format(end, sql.Literal(period))
            query = sql.SQL("SELECT EXISTS (SELECT 1 FROM {}.{} WHERE {} < %s)").format(
                sql.Identifier(schema),
                sql.Identifier(table),
                end,
            )
            if connection.execute(query, (cutoff,)).fetchone()[0]:
                return True
    return False


def restore_snapshot(snapshot: str, archive: str, config: dict[str, str]) -> None:
    """Restore the exported snapshot into a new local PostgreSQL database."""
    if not (ROOT / "workspace/postgres/PG_VERSION").is_file():
        raise RuntimeError("Local PostgreSQL data directory is missing")
    docker("--profile", "local", "up", "-d", "postgres")
    docker(
        "cp",
        str(ROOT / "workspace/supabase/ca.crt"),
        "postgres:/tmp/weather-archive-ca.crt",
    )
    command = r"""set -eu
umask 077
IFS= read -r PGPASSWORD
export PGPASSWORD PGSSLMODE=verify-full PGSSLROOTCERT=/tmp/weather-archive-ca.crt
export PGHOST="$1" PGPORT="$2" PGUSER="$3" PGDATABASE="$4"
pg_dump -Fc -n public -n garmin -n garmin_activities -n garmin_monitoring -n garmin_summary -n summary --snapshot="$5" -f "/tmp/$6.dump"
pg_restore -l "/tmp/$6.dump" | sed '/ SCHEMA - public /d' > "/tmp/$6.list"
unset PGHOST PGPORT PGUSER PGDATABASE PGPASSWORD PGSSLMODE PGSSLROOTCERT
createdb -U "$POSTGRES_USER" "$6"
pg_restore --exit-on-error --no-owner --no-privileges -L "/tmp/$6.list" -U "$POSTGRES_USER" -d "$6" "/tmp/$6.dump"
"""
    docker(
        "exec",
        "-T",
        "postgres",
        "sh",
        "-c",
        command,
        "archive",
        config["DB_HOST"],
        config["DB_PORT"],
        config["DB_USER"],
        config["DB_NAME"],
        snapshot,
        archive,
        input_text=config["DB_PASSWORD"] + "\n",
    )


def digest_remote(connection: psycopg.Connection, schema: str, table: str) -> bytes:
    query = sql.SQL(
        'COPY (SELECT row_to_json(t)::text COLLATE "C" FROM {}.{} t ORDER BY 1) TO STDOUT'
    ).format(sql.Identifier(schema), sql.Identifier(table))
    digest = hashlib.sha256()
    with connection.cursor().copy(query) as copy:
        for chunk in copy:
            digest.update(chunk)
    return digest.digest()


def digest_local(archive: str, schema: str, table: str) -> bytes:
    query = (
        sql.SQL(
            'COPY (SELECT row_to_json(t)::text COLLATE "C" FROM {}.{} t ORDER BY 1) TO STDOUT'
        )
        .format(sql.Identifier(schema), sql.Identifier(table))
        .as_string()
    )
    process = subprocess.Popen(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "postgres",
            "env",
            "PGTZ=UTC",
            "PGOPTIONS=-c extra_float_digits=3 -c statement_timeout=60000",
            "psql",
            "-X",
            "-q",
            "-U",
            "postgres",
            "-d",
            archive,
            "-c",
            query,
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    digest = hashlib.sha256()
    assert process.stdout is not None
    timer = threading.Timer(120, process.kill)
    timer.start()
    try:
        for chunk in iter(lambda: process.stdout.read(1024 * 1024), b""):
            digest.update(chunk)
        process.stdout.close()
        if process.wait() != 0:
            raise RuntimeError("Cannot verify local archive")
    finally:
        timer.cancel()
    return digest.digest()


def delete_expired(
    connection: psycopg.Connection, cutoff: datetime, current: set[tuple[str, str]]
) -> int:
    connection.execute(
        "CREATE TEMP TABLE retention_ids ON COMMIT DROP AS "
        "SELECT a.activity_id FROM garmin_activities.activities a "
        "WHERE a.start_time < %s AND NOT EXISTS "
        "(SELECT 1 FROM public.activity_grades g WHERE g.activity_id = a.activity_id AND g.status = 'processing')",
        (cutoff,),
    )
    count = 0
    for name in ACTIVITY_TABLES:
        count += connection.execute(
            sql.SQL(
                "DELETE FROM garmin_activities.{} WHERE activity_id IN (SELECT activity_id FROM retention_ids)"
            ).format(sql.Identifier(name))
        ).rowcount
    for name in ("activity_grades", "garmin_activities"):
        if ("public", name) in current:
            count += connection.execute(
                sql.SQL(
                    "DELETE FROM public.{} WHERE activity_id IN (SELECT activity_id FROM retention_ids)"
                ).format(sql.Identifier(name))
            ).rowcount
    count += connection.execute(
        "DELETE FROM public.activity_grades g "
        "WHERE g.created_at < (%s::timestamp AT TIME ZONE 'America/Sao_Paulo') "
        "AND g.status <> 'processing' AND NOT EXISTS "
        "(SELECT 1 FROM garmin_activities.activities a WHERE a.activity_id = g.activity_id)",
        (cutoff,),
    ).rowcount
    count += connection.execute(
        "DELETE FROM garmin_activities.activities WHERE activity_id IN (SELECT activity_id FROM retention_ids)"
    ).rowcount
    for schema, definitions in DATED_TABLES.items():
        for table in definitions:
            count += connection.execute(dated_delete(schema, table), (cutoff,)).rowcount
    return count


def main() -> None:
    config = dotenv_values(ROOT / ".env.supabase")
    if any(
        not config.get(key)
        for key in ("DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME")
    ):
        raise RuntimeError("Supabase database settings are incomplete")
    params = {
        "host": config["DB_HOST"],
        "port": config["DB_PORT"],
        "user": config["DB_USER"],
        "password": config["DB_PASSWORD"],
        "dbname": config["DB_NAME"],
        "sslmode": "verify-full",
        "sslrootcert": str(ROOT / "workspace/supabase/ca.crt"),
        "connect_timeout": 15,
    }
    archive = (
        "weather_archive_"
        + datetime.now(UTC).strftime("%Y%m%d_%H%M%S_")
        + uuid.uuid4().hex[:8]
    )
    with psycopg.connect(**params) as snapshot:
        snapshot.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        snapshot.execute("SET LOCAL TIME ZONE 'UTC'")
        snapshot.execute("SET LOCAL extra_float_digits = 3")
        if not snapshot.execute(
            "SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user"
        ).fetchone()[0]:
            raise RuntimeError("Database role cannot verify all protected rows")
        cutoff = snapshot.execute(
            "SELECT (now() AT TIME ZONE 'America/Sao_Paulo') - interval '1 year'"
        ).fetchone()[0]
        original = tables(snapshot)
        if not has_expired(snapshot, cutoff):
            print("No records are old enough to archive.")
            return
        snapshot_id = snapshot.execute("SELECT pg_export_snapshot()").fetchone()[0]
        restore_snapshot(snapshot_id, archive, config)
    with psycopg.connect(**params) as remote:
        remote.execute("SET LOCAL TIME ZONE 'UTC'")
        remote.execute("SET LOCAL extra_float_digits = 3")
        remote.execute("SET LOCAL lock_timeout = '5s'")
        remote.execute("SET LOCAL statement_timeout = '60s'")
        remote.execute("SET LOCAL idle_in_transaction_session_timeout = '120s'")
        remote.execute("SELECT pg_advisory_xact_lock(8730242)")
        for schema, table in sorted(original):
            remote.execute(
                sql.SQL("LOCK TABLE {}.{} IN SHARE ROW EXCLUSIVE MODE").format(
                    sql.Identifier(schema),
                    sql.Identifier(table),
                )
            )
        if tables(remote) != original:
            raise RuntimeError("Database tables changed during archiving")
        for schema, table in sorted(original):
            if digest_remote(remote, schema, table) != digest_local(
                archive, schema, table
            ):
                raise RuntimeError(f"Archive verification failed for {schema}.{table}")
        count = delete_expired(remote, cutoff, original)
        if tables(remote) != original:
            raise RuntimeError("Database tables changed during deletion")
    print(
        f"Archived and verified local database {archive}; removed {count} expired rows."
    )


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(f"Archive stopped: {error}", file=sys.stderr)
        raise SystemExit(1) from None
    except (OSError, psycopg.Error, subprocess.SubprocessError) as error:
        print(f"Archive stopped: {type(error).__name__}", file=sys.stderr)
        raise SystemExit(1) from None
