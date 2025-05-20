from typing import Any
import redis.asyncio as redis
import json


class RedisQueue:
    def __init__(self) -> None:
        self._client: redis.Redis | None = None

    async def init(
        self,
        host: str = "localhost",
        port: int = 6379,
        _client: redis.Redis | None = None,
    ) -> None:
        if _client is None:
            self._client = redis.Redis(
                host=host, port=port, decode_responses=True, protocol=3
            )
        else:
            self._client = _client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _key(self, id: str) -> str:
        return f"queue:{id}"

    async def enqueue(self, id: str, item: Any) -> None:
        if self._client is None:
            raise RuntimeError("RedisQueue not initialised")

        await self._client.rpush(self._key(id), json.dumps(item))  # type: ignore[misc]

    async def dequeue(self, id: str) -> dict[str, str] | None:
        if self._client is None:
            raise RuntimeError("RedisQueue not initialised")

        item = await self._client.lpop(self._key(id))  # type: ignore[misc]
        return json.loads(item) if item else None

    async def peek(self, id: str) -> list[dict[str, str]]:
        if self._client is None:
            raise RuntimeError("RedisQueue not initialised")

        items = await self._client.lrange(self._key(id), 0, 0)  # type: ignore[misc]
        return [json.loads(i) for i in items]


queue = RedisQueue()
