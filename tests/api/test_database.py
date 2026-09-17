import importlib
import os

os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "shared")

database = importlib.import_module("apps.api.routes.connections.database")


def test_database_pools_fall_back_to_shared_name(monkeypatch):
    monkeypatch.delenv("DB_NAME_WEATHERAPI", raising=False)
    monkeypatch.delenv("DB_NAME_GARMIN", raising=False)
    monkeypatch.setenv("DB_NAME", "shared")

    assert database._database_url("weatherapi").endswith("/shared")
    assert database._database_url("garmin").endswith("/shared")
