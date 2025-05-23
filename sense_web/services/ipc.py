import asyncio
from enum import Enum
from typing import Any, Callable
import redis.asyncio as redis
import json


class PubSubChannels(Enum):
    DEVICE_REGISTRATION = "reg"


class IPC:
    def __init__(self) -> None:
        self._backend: redis.Redis | None = None
        self._pubsub: redis.client.PubSub | None = None
        self._subscriber_tasks: dict[str, asyncio.Task[Any]] = {}

    async def init(
        self,
        host: str = "localhost",
        port: int = 6379,
        _backend: redis.Redis | None = None,
    ) -> None:
        if _backend is None:
            self._backend = redis.Redis(
                host=host, port=port, decode_responses=True, protocol=3
            )
        else:
            self._backend = _backend

        self._pubsub = self._backend.pubsub()  # type: ignore[union-attr]

    async def close(self) -> None:
        if self._backend:
            await self._backend.aclose()
            self._backend = None

    def _key(self, id: str) -> str:
        return f"queue:{id}"

    async def enqueue(self, id: str, item: Any) -> None:
        if self._backend is None:
            raise RuntimeError("IPC not initialised")

        await self._backend.rpush(self._key(id), json.dumps(item))  # type: ignore[misc]

    async def dequeue(self, id: str) -> dict[str, str] | None:
        if self._backend is None:
            raise RuntimeError("IPC not initialised")

        item = await self._backend.lpop(self._key(id))  # type: ignore[misc]
        return json.loads(item) if item else None

    async def peek(self, id: str) -> list[dict[str, str]]:
        if self._backend is None:
            raise RuntimeError("IPC not initialised")

        items = await self._backend.lrange(self._key(id), 0, -1)  # type: ignore[misc]
        return [json.loads(i) for i in items]

    async def publish(self, channel: str, message: str) -> None:
        if self._backend is None:
            raise RuntimeError("IPC not initialised")

        await self._backend.publish(channel, message)

    async def subscribe(
        self, channel: str, callback: Callable[[str], Any]
    ) -> None:
        if self._pubsub is None:
            raise RuntimeError("IPC not initialised")

        async def _listener() -> None:
            if self._pubsub is None:
                raise RuntimeError("IPC not initialised")

            await self._pubsub.subscribe(channel)
            async for msg in self._pubsub.listen():
                if msg["type"] == "message":
                    await callback(msg["data"])

        task = asyncio.create_task(_listener())
        self._subscriber_tasks[channel] = task

    async def unsubscribe(self, channel: str) -> None:
        task = self._subscriber_tasks.pop(channel, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


ipc = IPC()


async def enqueue_command(device_uuid: str, command: dict[str, str]) -> None:
    await ipc.enqueue(device_uuid, command)


async def dequeue_command(device_uuid: str) -> dict[str, str] | None:
    return await ipc.dequeue(device_uuid)


async def peek_commands(device_uuid: str) -> list[dict[str, str]]:
    return await ipc.peek(device_uuid)
