import pytest
import pytest_asyncio
import redis.asyncio as redis
import fakeredis

from sense_web.services.queue import (
    queue,
    enqueue_command,
    dequeue_command,
    peek_commands,
)


@pytest_asyncio.fixture(scope="function")
async def redis_client() -> redis.Redis:
    return fakeredis.FakeAsyncRedis(decode_responses=True)


@pytest.mark.asyncio
async def test_enqueue_and_dequeue_command(redis_client: redis.Redis) -> None:
    await queue.init(_client=redis_client)

    device_id = "device-abc"
    command = {"cmd": "reboot", "ts": "123456"}

    await enqueue_command(device_id, command)
    result = await dequeue_command(device_id)

    assert result == command


@pytest.mark.asyncio
async def test_peek_commands(redis_client: redis.Redis) -> None:
    await queue.init(_client=redis_client)

    device_id = "device-xyz"
    command1 = {"cmd": "ping"}
    command2 = {"cmd": "status"}

    await enqueue_command(device_id, command1)
    await enqueue_command(device_id, command2)

    peeked = await peek_commands(device_id)

    assert len(peeked) == 2
    assert peeked[0] == command1
    assert peeked[1] == command2


async def test_peek_commands_empty(redis_client: redis.Redis) -> None:
    await queue.init(_client=redis_client)

    peeked = await peek_commands("non-existent")

    assert peeked is not None
    assert len(peeked) == 0
