from unittest.mock import MagicMock

import pytest

from scripts import initialize_postgres


def test_creates_both_schemas_without_syncing(monkeypatch):
    for key, value in {
        "DB_NAME": "weather",
        "DB_NAME_GARMIN": "garmin",
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_USER": "postgres",
        "DB_PASSWORD": "test",
    }.items():
        monkeypatch.setenv(key, value)
    connect = MagicMock()
    monkeypatch.setattr(initialize_postgres.psycopg, "connect", connect)

    initialize_postgres.initialize_databases()

    assert [call.kwargs["dbname"] for call in connect.call_args_list] == [
        "weather", "garmin"
    ]
    statements = [
        call.args[0]
        for call in connect.return_value.__enter__.return_value.execute.call_args_list
    ]
    assert "CREATE TABLE public.athlete_profile" in statements[1]
    assert "CREATE TABLE garmin_activities.activities" in statements[3]
    assert "CREATE TABLE garmin_activities.activity_records" in statements[3]
    assert "CREATE VIEW garmin_activities.running_activities_view" in statements[3]
    assert "DROP " not in statements[1] + statements[3]


def test_rejects_shared_application_and_garmin_database(monkeypatch):
    monkeypatch.setenv("DB_NAME", "same")
    monkeypatch.setenv("DB_NAME_GARMIN", "same")
    connect = MagicMock()
    monkeypatch.setattr(initialize_postgres.psycopg, "connect", connect)

    with pytest.raises(ValueError, match="must differ"):
        initialize_postgres.initialize_databases()

    connect.assert_not_called()


def test_shared_database_requires_explicit_opt_in(monkeypatch):
    for key, value in {
        "DB_NAME": "shared", "DB_NAME_GARMIN": "shared", "DB_SHARED_GARMIN": "1",
        "DB_HOST": "localhost", "DB_PORT": "5432", "DB_PASSWORD": "test",
    }.items():
        monkeypatch.setenv(key, value)
    connect = MagicMock()
    monkeypatch.setattr(initialize_postgres.psycopg, "connect", connect)

    initialize_postgres.initialize_databases()

    assert [call.kwargs["dbname"] for call in connect.call_args_list] == ["shared", "shared"]
    statements = [call.args[0] for call in connect.return_value.__enter__.return_value.execute.call_args_list]
    assert "ALTER TABLE public.activity_grades ENABLE ROW LEVEL SECURITY" in statements
    assert "ALTER TABLE public.athlete_profile ENABLE ROW LEVEL SECURITY" in statements
