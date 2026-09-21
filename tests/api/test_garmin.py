import asyncio
import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from apps.api.services.garmin import _activity_id, _open_activities, run_garmindb_sync


def test_reads_garmindb_activities_in_batches(tmp_path):
    database_path = tmp_path / "garmin_activities.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "CREATE TABLE activities (activity_id INTEGER PRIMARY KEY, name TEXT)"
        )
        connection.executemany(
            "INSERT INTO activities VALUES (?, ?)",
            [(1, "Morning Run"), (2, "Evening Ride")],
        )

    connection, cursor = _open_activities(database_path)
    try:
        assert [dict(row) for row in cursor.fetchmany(1)] == [
            {"activity_id": 1, "name": "Morning Run"}
        ]
        assert [dict(row) for row in cursor.fetchmany(1)] == [
            {"activity_id": 2, "name": "Evening Ride"}
        ]
        assert cursor.fetchmany(1) == []
    finally:
        connection.close()


def test_rejects_activity_without_identifier():
    with pytest.raises(ValueError, match="no activity identifier"):
        _activity_id({"name": "Morning Run"})


def test_rejects_missing_garmindb(tmp_path):
    with pytest.raises(FileNotFoundError):
        _open_activities(tmp_path / "missing.db")


def test_rejects_garmindb_without_activities_table(tmp_path):
    database_path = tmp_path / "empty.db"
    sqlite3.connect(database_path).close()

    with pytest.raises(sqlite3.Error, match="no such table"):
        _open_activities(database_path)


@pytest.mark.asyncio
async def test_runs_repository_garmin_sync_command(monkeypatch):
    process = type(
        "Process",
        (),
        {"returncode": 0, "communicate": AsyncMock(return_value=(b"", None))},
    )()
    create = AsyncMock(return_value=process)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", create)

    await run_garmindb_sync()

    assert create.await_args.args == ("make", "garmin-sync")
    assert create.await_args.kwargs["cwd"] == Path(__file__).parents[2]
