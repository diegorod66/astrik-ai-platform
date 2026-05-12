"""Cliente PostgreSQL para leer historial de workflows."""

import asyncpg

DATABASE_URL = "postgresql://astrik:astrik_secret@192.168.2.112:5432/astrik"


class DBClient:
    def __init__(self, dsn: str = DATABASE_URL):
        self.dsn = dsn
        self._pool = None

    async def connect(self):
        self._pool = await asyncpg.create_pool(self.dsn, min_size=2, max_size=5)

    async def close(self):
        if self._pool:
            await self._pool.close()

    async def get_checkpoints(self, limit: int = 50) -> list[dict]:
        if not self._pool:
            await self.connect()
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT thread_id, checkpoint, parent_checkpoint_id, metadata "
                "FROM checkpoints ORDER BY checkpoint DESC LIMIT $1",
                limit,
            )
            return [dict(r) for r in rows]

    async def get_workflow_by_thread(self, thread_id: str) -> dict | None:
        if not self._pool:
            await self.connect()
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT thread_id, checkpoint, parent_checkpoint_id, metadata "
                "FROM checkpoints WHERE thread_id = $1 ORDER BY checkpoint DESC LIMIT 1",
                thread_id,
            )
            return dict(row) if row else None
