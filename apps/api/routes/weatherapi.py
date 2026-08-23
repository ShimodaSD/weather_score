from psycopg.rows import TupleRow

from .connections.database import weatherapi_pool


async def get_distance() -> list[TupleRow]:
    async with (
        weatherapi_pool.connection() as connection,
        connection.cursor() as cursor,
    ):
        await cursor.execute("")
        return await cursor.fetchall()
