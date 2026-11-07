import os

from dotenv import load_dotenv
from psycopg.conninfo import make_conninfo
from psycopg_pool import AsyncConnectionPool

load_dotenv()

DATABASE_URL = make_conninfo(
    host=os.environ["DB_HOST"],
    port=os.environ["DB_PORT"],
    user=os.environ.get("DB_USER") or "postgres",
    password=os.environ.get("DB_PASSWORD", ""),
    dbname=os.environ["DB_NAME"],
)

pool = AsyncConnectionPool(conninfo=DATABASE_URL, open=False)
