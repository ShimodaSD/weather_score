import importlib
import os

from psycopg.conninfo import conninfo_to_dict

os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "shared")

database = importlib.import_module("apps.api.routes.connections.database")


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
