"""Create application and Garmin tables without downloading activity data."""

import os
from pathlib import Path

import psycopg


def initialize_databases() -> None:
    """Apply schema-only snapshots transactionally, preserving existing data."""
    names = [os.environ["DB_NAME"], os.environ["DB_NAME_GARMIN"]]
    if names[0] == names[1]:
        raise ValueError("DB_NAME_GARMIN must differ from DB_NAME")
    directory = Path(__file__).resolve().parents[1] / "apps" / "api" / "sql"
    for schema, name in zip(("application", "garmin"), names, strict=True):
        with psycopg.connect(
            host=os.environ["DB_HOST"],
            port=os.environ["DB_PORT"],
            user=os.environ.get("DB_USER", "postgres"),
            password=os.environ["DB_PASSWORD"],
            dbname=name,
        ) as connection:
            connection.execute("SELECT pg_advisory_xact_lock(8730241)")
            connection.execute((directory / f"{schema}.sql").read_text())
        print(f"postgres-init: {schema} tables ready", flush=True)


if __name__ == "__main__":
    initialize_databases()
