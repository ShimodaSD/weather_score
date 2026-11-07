import importlib
import os
import runpy
from pathlib import Path

import pytest
from psycopg.conninfo import conninfo_to_dict

os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "shared")

database = importlib.import_module("apps.api.routes.connections.database")


@pytest.mark.parametrize("username,expected", [("", "postgres"), ("postgres.project", "postgres.project")])
def test_connection_builders_handle_blank_and_explicit_users(monkeypatch, username, expected):
    monkeypatch.setenv("DB_USER", username)
    main_database = runpy.run_path(str(Path(__file__).parents[2] / "apps/api/database.py"))

    assert conninfo_to_dict(main_database["DATABASE_URL"])["user"] == expected
    for name in ("weatherapi", "garmin"):
        assert conninfo_to_dict(database._database_url(name))["user"] == expected


def test_database_pools_fall_back_to_shared_name(monkeypatch):
    monkeypatch.delenv("DB_NAME_WEATHERAPI", raising=False)
    monkeypatch.delenv("DB_NAME_GARMIN", raising=False)
    monkeypatch.setenv("DB_NAME", "shared")

    assert conninfo_to_dict(database._database_url("weatherapi"))["dbname"] == "shared"
    assert conninfo_to_dict(database._database_url("garmin"))["dbname"] == "shared"


def test_database_credentials_preserve_special_characters(monkeypatch):
    monkeypatch.setenv("DB_USER", "postgres.project")
    monkeypatch.setenv("DB_PASSWORD", "a ' password/@")

    config = conninfo_to_dict(database._database_url("garmin"))
    assert config["user"] == "postgres.project"
    assert config["password"] == "a ' password/@"
