import os
from urllib.parse import quote_plus

from dotenv import find_dotenv, load_dotenv
from psycopg import AsyncConnection
from psycopg.rows import TupleRow
from psycopg_pool import AsyncConnectionPool

load_dotenv(find_dotenv())

Pool = AsyncConnectionPool[AsyncConnection[TupleRow]]


def _database_url(database_name: str) -> str:
    """Build a PostgreSQL connection string for a configured database."""
    password = os.environ.get("DB_PASSWORD", "")
    host = os.environ.get("DB_HOST")
    port = os.environ.get("DB_PORT")
    if not host or not port:
        raise ValueError("Invalid database configuration. Missing host or port.")
    if database_name == "weatherapi":
        name = os.environ.get("DB_NAME_WEATHERAPI")
    elif database_name == "garmin":
        name = os.environ.get("DB_NAME_GARMIN")
    else:
        raise ValueError("Invalid database name. Use 'weatherapi' or 'garmin'.")

    return f"postgresql://postgres:{quote_plus(password)}@{host}:{port}/{name}"


# Pools are created once and opened/closed by the application's lifespan.
weatherapi_pool: Pool = AsyncConnectionPool(
    conninfo=_database_url("weatherapi"), open=False
)
garmin_pool: Pool = AsyncConnectionPool(conninfo=_database_url("garmin"), open=False)

_pools: dict[str, Pool] = {
    "weatherapi": weatherapi_pool,
    "garmin": garmin_pool,
}


def get_database_pool(db_name: str) -> Pool:
    """Return the already-configured pool for a database."""
    if db_name == "weatherapi":
        return _pools["weatherapi"]
    if db_name == "garmin":
        return _pools["garmin"]
    raise ValueError("Invalid database name. Use 'weatherapi' or 'garmin'.")


# Preserve the original function name for existing callers.
get_database_connection = get_database_pool
