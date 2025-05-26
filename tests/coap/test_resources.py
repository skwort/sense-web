import pytest
import time
import json
import os
import subprocess
import asyncio
from aiocoap import Context, Message, Code
from typing import AsyncGenerator, Generator
from testcontainers.redis import RedisContainer

from sense_web.services.device import register_device
from sense_web.services.ipc import (
    ipc,
    PubSubChannels,
    enqueue_command,
    peek_commands,
)
from sense_web.db.session import sessionmanager
from sense_web.coap.server import start_coap

DB_URI = "sqlite+aiosqlite:///pytest.db"
os.environ["DATABASE_URI"] = DB_URI


@pytest.fixture(scope="function")
async def db_manager() -> AsyncGenerator[None]:
    await sessionmanager.init(DB_URI)

    async with sessionmanager.connect() as conn:
        await sessionmanager.drop_all(conn)
        await sessionmanager.create_all(conn)

    yield

    await sessionmanager.close()


@pytest.fixture(scope="module")
def coap_server() -> Generator[None, None, None]:
    host = "0.0.0.0"
    port = 5683

    redis = RedisContainer().with_exposed_ports(6379)
    redis.start()

    os.environ["REDIS_HOST"] = redis.get_container_host_ip()
    os.environ["REDIS_PORT"] = redis.get_exposed_port(6379)

    proc = start_coap(
        host=host,
        port=port,
        env=dict(os.environ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        time.sleep(2)
        if proc.poll() is not None:
            raise RuntimeError("CoAP server exited prematurely")
        yield
    finally:
        redis.stop()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.mark.asyncio
async def test_device_resource(coap_server: None, db_manager: None) -> None:
    device = await register_device("12345")
    uuid = device.uuid

    await ipc.init(
        host=os.environ["REDIS_HOST"], port=int(os.environ["REDIS_PORT"])
    )
    await ipc.publish(
        PubSubChannels.DEVICE_REGISTRATION.value, str(device.uuid)
    )

    # Let the CoAP server process the registration message
    await asyncio.sleep(0.2)

    protocol = await Context.create_client_context()

    request = Message(code=Code.GET, uri=f"coap://127.0.0.1/{str(uuid)}")
    response = await protocol.request(request).response

    assert response.code.is_successful()
    assert isinstance(response.payload, bytes)

    await ipc.close()


@pytest.mark.asyncio
async def test_get_delete_device_command_resource(
    coap_server: None, db_manager: None
) -> None:
    device = await register_device("12345")
    uuid = str(device.uuid)

    await ipc.init(
        host=os.environ["REDIS_HOST"], port=int(os.environ["REDIS_PORT"])
    )
    await ipc.publish(PubSubChannels.DEVICE_REGISTRATION.value, uuid)

    cmd = {"test": "command"}
    await enqueue_command(uuid, cmd)

    # Let the CoAP server process the registration message
    await asyncio.sleep(0.2)

    protocol = await Context.create_client_context()

    request = Message(code=Code.GET, uri=f"coap://127.0.0.1/{uuid}/commands")
    response = await protocol.request(request).response

    assert response.code.is_successful()
    assert json.loads(response.payload) == cmd

    request = Message(
        code=Code.DELETE, uri=f"coap://127.0.0.1/{uuid}/commands"
    )
    response = await protocol.request(request).response

    assert response.code.is_successful()
    assert len(await peek_commands(uuid)) == 0

    await ipc.close()


@pytest.mark.asyncio
async def test_get_device_command_resource_empty(
    coap_server: None, db_manager: None
) -> None:
    device = await register_device("12345")
    uuid = str(device.uuid)

    await ipc.init(
        host=os.environ["REDIS_HOST"], port=int(os.environ["REDIS_PORT"])
    )
    await ipc.publish(PubSubChannels.DEVICE_REGISTRATION.value, uuid)

    # Let the CoAP server process the registration message
    await asyncio.sleep(0.1)

    protocol = await Context.create_client_context()

    request = Message(code=Code.GET, uri=f"coap://127.0.0.1/{uuid}/commands")
    response = await protocol.request(request).response

    assert response.code.is_successful()
    assert len(response.payload) == 0

    await ipc.close()


@pytest.mark.asyncio
async def test_delete_device_command_resource_empty(
    coap_server: None, db_manager: None
) -> None:
    device = await register_device("12345")
    uuid = str(device.uuid)

    await ipc.init(
        host=os.environ["REDIS_HOST"], port=int(os.environ["REDIS_PORT"])
    )
    await ipc.publish(PubSubChannels.DEVICE_REGISTRATION.value, uuid)

    # Let the CoAP server process the registration message
    await asyncio.sleep(0.1)

    protocol = await Context.create_client_context()

    request = Message(
        code=Code.DELETE, uri=f"coap://127.0.0.1/{uuid}/commands"
    )
    response = await protocol.request(request).response

    assert response.code.is_successful()
    assert len(response.payload) == 0

    await ipc.close()
