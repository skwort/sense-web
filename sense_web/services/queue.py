from typing import Any
import redis.asyncio as redis
import json


class RedisQueue:
    def __init__(
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

    def _key(self, id: str) -> str:
        return f"queue:{id}"

    async def dequeue(self, id: str) -> Any | None:
        item = await self._client.lpop(self._key(id))
        if item is not None:
            return json.loads(item)

        return None

    async def enqueue(self, id: str, item: Any) -> None:
        await self._client.rpush(self._key(id), json.dumps(item))

    async def peek(self, id: str) -> list[Any]:
        items = await self._client.lrange(self._key(id), 0, 0)
        return [json.loads(i) for i in items]

    async def close(self) -> None:
        await self._client.aclose()
