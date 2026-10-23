import asyncio
import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from apps.api.services.garmin import (
    _activity_id,
    _open_activities,
    get_sync_progress,
    run_garmindb_sync,
)


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
    stdout = asyncio.StreamReader()
    stdout.feed_data(b'garmin-progress: {"phase":"downloading","downloaded_files":1,"total_files":3}\n')
    stdout.feed_data(b'garmin-progress: {"phase":"importing","downloaded_files":3,"total_files":3}\n')
    stdout.feed_eof()
    process = type(
        "Process",
        (),
        {"returncode": 0, "stdout": stdout, "wait": AsyncMock(return_value=0)},
    )()
    create = AsyncMock(return_value=process)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", create)

    await run_garmindb_sync()

    assert create.await_args.args == ("make", "garmin-sync")
    assert create.await_args.kwargs["cwd"] == Path(__file__).parents[2]
    assert get_sync_progress().model_dump() == {
        "phase": "complete", "downloaded_files": 3, "total_files": 3,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("returncode", [0, 1])
async def test_sync_ignores_invalid_progress_and_reports_failure(monkeypatch, returncode):
    from fastapi import HTTPException

    stdout = asyncio.StreamReader()
    stdout.feed_data(b'garmin-progress: not-json\n')
    stdout.feed_data(b'garmin-progress: {"phase":"downloading","downloaded_files":4,"total_files":3}\n')
    stdout.feed_eof()
    process = type("Process", (), {
        "returncode": returncode, "stdout": stdout, "wait": AsyncMock(),
    })()
    monkeypatch.setattr(asyncio, "create_subprocess_exec", AsyncMock(return_value=process))
    if returncode:
        with pytest.raises(HTTPException) as error:
            await run_garmindb_sync()
        assert error.value.status_code == 502
    else:
        await run_garmindb_sync()
    assert get_sync_progress().phase == ("failed" if returncode else "complete")
    assert get_sync_progress().downloaded_files == 0


@pytest.mark.asyncio
async def test_reports_live_progress_and_rejects_concurrent_sync(monkeypatch):
    from fastapi import HTTPException

    stdout = asyncio.StreamReader()
    process = type("Process", (), {
        "returncode": 0, "stdout": stdout, "wait": AsyncMock(),
    })()
    monkeypatch.setattr(asyncio, "create_subprocess_exec", AsyncMock(return_value=process))
    task = asyncio.create_task(run_garmindb_sync())
    try:
        await asyncio.sleep(0)
        assert get_sync_progress().phase == "checking"
        with pytest.raises(HTTPException) as error:
            await run_garmindb_sync()
        assert error.value.status_code == 409
        stdout.feed_data(b'garmin-progress: {"phase":"downloading","downloaded_files":2,"total_files":6}\n')
        await asyncio.sleep(0)
        assert get_sync_progress().model_dump() == {
            "phase": "downloading", "downloaded_files": 2, "total_files": 6,
        }
    finally:
        stdout.feed_eof()
        await task
