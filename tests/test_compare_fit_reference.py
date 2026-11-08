"""Verify the reference comparison reports missing and changed data."""

import sqlite3
from datetime import datetime

from scripts.compare_fit_reference import compare, equivalent


def test_comparison_is_read_only_and_reports_differences(tmp_path, monkeypatch):
    database = tmp_path / "reference.db"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE activity_records (activity_id text, record integer, hr integer)"
        )
        connection.execute("CREATE TABLE activity_laps (activity_id text, lap integer)")
        connection.executemany(
            "INSERT INTO activity_records VALUES (?, ?, ?)",
            [("1", 0, 140), ("2", 0, 120)],
        )
    (tmp_path / "1.fit").touch()
    monkeypatch.setattr(
        "scripts.compare_fit_reference.decode_activity",
        lambda _: {"records": [{"record": 0, "hr": 141}], "laps": []},
    )

    result = compare(database, tmp_path)

    assert result == {
        "activities": 1,
        "missing_fit": 1,
        "unsupported": 0,
        "record_count_mismatch": 0,
        "field_mismatches": 1,
        "lap_count_mismatch": 0,
        "lap_field_mismatches": 0,
    }
    with sqlite3.connect(database) as connection:
        assert (
            connection.execute("SELECT COUNT(*) FROM activity_records").fetchone()[0]
            == 2
        )


def test_compares_datetime_and_float_values():
    assert equivalent(
        "2026-01-01 12:00:00", datetime.fromisoformat("2026-01-01 12:00:00")
    )
    assert equivalent(
        "2026-01-01 12:00:00.000000", datetime.fromisoformat("2026-01-01 12:00:00")
    )
    assert equivalent(1.0, 1.0000000001)
