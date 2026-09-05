from psycopg.rows import TupleRow

from .connections.database import garmin_pool


async def get_distance() -> list[TupleRow]:
    """Run a SELECT against Garmin and return its rows.

    Keep ``query`` in application code and pass values through ``params``;
    never interpolate user input into the SQL string.
    """
    async with (
        garmin_pool.connection() as connection,
        connection.cursor() as cursor,
    ):
        await cursor.execute("SELECT ")
        return await cursor.fetchall()
