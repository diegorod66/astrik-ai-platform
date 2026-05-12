from __future__ import annotations

from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from .config import settings


pool = AsyncConnectionPool(
    conninfo=settings.database_url,
    max_size=20,
    kwargs={"autocommit": True},
    open=False,
)


@asynccontextmanager
async def lifespan_checkpointer():
    await pool.open()
    saver = AsyncPostgresSaver(pool)
    await saver.setup()
    try:
        yield saver
    finally:
        await pool.close()
