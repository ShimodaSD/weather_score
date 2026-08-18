import os
from psycopg_pool import AsyncConnectionPool
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = f"postgresql://postgres:{os.environ.get('DB_PASSWORD')}@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/{os.environ['DB_NAME']}"

pool = AsyncConnectionPool(conninfo=DATABASE_URL, open=False)
