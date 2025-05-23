import pytest
import pytest_asyncio
import redis.asyncio as redis
import fakeredis

from sense_web.services.ipc import (
    ipc,
    IPC,
    enqueue_command,
    dequeue_command,
    peek_commands,
)


@pytest_asyncio.fixture
async def ipc_backend() -> redis.Redis:
    return fakeredis.FakeAsyncRedis(decode_responses=True)


@pytest.mark.asyncio
async def test_enqueue_and_dequeue(
    ipc_backend: redis.Redis,
) -> None:
    ipc_instance = IPC()
    await ipc_instance.init(_backend=ipc_backend)

    item = {"cmd": "reboot", "ts": 123456}
    await ipc_instance.enqueue("device-123", item)

    result = await ipc_instance.dequeue("device-123")
    assert result == item


@pytest.mark.asyncio
async def test_peek(ipc_backend: redis.Redis) -> None:
    ipc_instance = IPC()
    await ipc_instance.init(_backend=ipc_backend)

    item1 = {"cmd": "ping"}
    item2 = {"cmd": "pong"}
    await ipc_instance.enqueue("device-123", item1)
    await ipc_instance.enqueue("device-123", item2)

    peeked = await ipc_instance.peek("device-123")
    assert len(peeked) == 2
    assert peeked[0] == item1
    assert peeked[1] == item2


@pytest.mark.asyncio
async def test_peek_empty(ipc_backend: redis.Redis) -> None:
    ipc_instance = IPC()
    await ipc_instance.init(_backend=ipc_backend)

    result = await ipc_instance.peek("device-123")
    assert len(result) == 0


@pytest.mark.asyncio
async def test_dequeue_empty(ipc_backend: redis.Redis) -> None:
    ipc_instance = IPC()
    await ipc_instance.init(_backend=ipc_backend)

    result = await ipc_instance.dequeue("device-123")
    assert result is None


@pytest.mark.asyncio
async def test_close(ipc_backend: redis.Redis) -> None:
    ipc_instance = IPC()
    await ipc_instance.init(_backend=ipc_backend)

    await ipc_instance.close()


@pytest.mark.asyncio
async def test_enqueue_without_init_raises() -> None:
    ipc_instance = IPC()
    with pytest.raises(RuntimeError, match="IPC not initialised"):
        await ipc_instance.enqueue("device-123", {"cmd": "test"})


@pytest.mark.asyncio
async def test_dequeue_without_init_raises() -> None:
    ipc_instance = IPC()
    with pytest.raises(RuntimeError, match="IPC not initialised"):
        await ipc_instance.dequeue("device-123")


@pytest.mark.asyncio
async def test_peek_without_init_raises() -> None:
    ipc_instance = IPC()
    with pytest.raises(RuntimeError, match="IPC not initialised"):
        await ipc_instance.peek("device-123")


@pytest.mark.asyncio
async def test_close_without_init_does_not_error() -> None:
    ipc_instance = IPC()
    await ipc_instance.close()


@pytest.mark.asyncio
async def test_enqueue_and_dequeue_command(ipc_backend: redis.Redis) -> None:
    await ipc.init(_backend=ipc_backend)

    device_id = "device-abc"
    command = {"cmd": "reboot", "ts": "123456"}

    await enqueue_command(device_id, command)
    result = await dequeue_command(device_id)

    assert result == command


@pytest.mark.asyncio
async def test_peek_commands(ipc_backend: redis.Redis) -> None:
    await ipc.init(_backend=ipc_backend)

    device_id = "device-xyz"
    command1 = {"cmd": "ping"}
    command2 = {"cmd": "status"}

    await enqueue_command(device_id, command1)
    await enqueue_command(device_id, command2)

    peeked = await peek_commands(device_id)

    assert len(peeked) == 2
    assert peeked[0] == command1
    assert peeked[1] == command2


async def test_peek_commands_empty(ipc_backend: redis.Redis) -> None:
    await ipc.init(_backend=ipc_backend)

    peeked = await peek_commands("non-existent")

    assert peeked is not None
    assert len(peeked) == 0
