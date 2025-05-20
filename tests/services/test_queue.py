import redis.asyncio as redis
import pytest
import pytest_asyncio
import fakeredis

from sense_web.services.queue import RedisQueue


@pytest_asyncio.fixture
async def redis_client() -> redis.Redis:
    return fakeredis.FakeAsyncRedis(decode_responses=True)


@pytest.mark.asyncio
async def test_redis_queue_enqueue_and_dequeue(
    redis_client: redis.Redis,
) -> None:
    queue = RedisQueue()
    await queue.init(_client=redis_client)

    item = {"cmd": "reboot", "ts": 123456}
    await queue.enqueue("device-123", item)

    result = await queue.dequeue("device-123")
    assert result == item


@pytest.mark.asyncio
async def test_redis_queue_peek(redis_client: redis.Redis) -> None:
    queue = RedisQueue()
    await queue.init(_client=redis_client)

    item = {"cmd": "ping"}
    await queue.enqueue("device-123", item)
    await queue.enqueue("device-123", {"cmd": "status"})

    peeked = await queue.peek("device-123")
    assert len(peeked) == 1
    assert peeked[0] == item


@pytest.mark.asyncio
async def test_redis_queue_peek_empty(redis_client: redis.Redis) -> None:
    queue = RedisQueue()
    await queue.init(_client=redis_client)

    result = await queue.peek("device-123")
    assert len(result) == 0


@pytest.mark.asyncio
async def test_redis_queue_dequeue_empty(redis_client: redis.Redis) -> None:
    queue = RedisQueue()
    await queue.init(_client=redis_client)

    result = await queue.dequeue("device-123")
    assert result is None


@pytest.mark.asyncio
async def test_redis_queue_close(redis_client: redis.Redis) -> None:
    queue = RedisQueue()
    await queue.init(_client=redis_client)

    await queue.close()
