"""
PostgreSQL storage backend for LORK.
"""

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


class PostgresStorage:

    def __init__(self, url="postgresql+asyncpg://postgres:postgres@localhost/lork"):
        self.engine = create_async_engine(url, echo=False)

    async def save_agent(self, agent_id, data):
        async with self.engine.begin() as conn:
            await conn.execute(
                text("INSERT INTO agents (id, data) VALUES (:id, :data)"),
                {"id": agent_id, "data": data},
            )

    async def get_agent(self, agent_id):
        async with self.engine.begin() as conn:
            result = await conn.execute(
                text("SELECT data FROM agents WHERE id=:id"),
                {"id": agent_id},
            )
            row = result.fetchone()
            return row[0] if row else None
