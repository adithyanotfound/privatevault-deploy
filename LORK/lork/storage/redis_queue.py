"""
Redis-backed queue for LORK task scheduling.
Allows multiple workers to pull tasks concurrently.
"""

import json
import redis.asyncio as redis


class RedisQueue:

    def __init__(self, url="redis://localhost:6379", queue_name="lork_tasks"):
        self._redis = redis.from_url(url)
        self._queue = queue_name

    async def enqueue(self, task_id: str):
        await self._redis.rpush(self._queue, task_id)

    async def dequeue(self):
        result = await self._redis.blpop(self._queue, timeout=1)
        if not result:
            return None
        _, task_id = result
        return task_id.decode()

    async def size(self):
        return await self._redis.llen(self._queue)
