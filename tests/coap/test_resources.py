import pytest
import time
import json
import cbor2
import datetime
import os
import subprocess
import asyncio
from aiocoap import Context, Message, Code
from typing import AsyncGenerator, Generator
from testcontainers.redis import RedisContainer

from sense_web.dto.device import DeviceDTO
from sense_web.services.datapoint import get_datapoints_by_device_uuid
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
async def device() -> AsyncGenerator[DeviceDTO]:
    device = await register_device("123456", "d1")
    uuid = str(device.uuid)

    await ipc.init(
        host=os.environ["REDIS_HOST"], port=int(os.environ["REDIS_PORT"])
    )
    await ipc.publish(PubSubChannels.DEVICE_REGISTRATION.value, uuid)

    # Let the CoAP server process the registration message
    await asyncio.sleep(0.1)

    yield device

    await ipc.close()


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
async def test_device_resource(
    coap_server: None, db_manager: None, device: DeviceDTO
) -> None:
    uuid = str(device.uuid)

    protocol = await Context.create_client_context()

    request = Message(code=Code.GET, uri=f"coap://127.0.0.1/{uuid}")
    response = await protocol.request(request).response

    assert response.code.is_successful()
    assert isinstance(response.payload, bytes)


@pytest.mark.asyncio
async def test_get_delete_device_command_resource(
    coap_server: None, db_manager: None, device: DeviceDTO
) -> None:
    uuid = str(device.uuid)

    cmd = {"test": "command"}
    await enqueue_command(uuid, cmd)

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


@pytest.mark.asyncio
async def test_get_device_command_resource_empty(
    coap_server: None, db_manager: None, device: DeviceDTO
) -> None:
    uuid = str(device.uuid)

    protocol = await Context.create_client_context()

    request = Message(code=Code.GET, uri=f"coap://127.0.0.1/{uuid}/commands")
    response = await protocol.request(request).response

    assert response.code.is_successful()
    assert len(response.payload) == 0


@pytest.mark.asyncio
async def test_delete_device_command_resource_empty(
    coap_server: None, db_manager: None, device: DeviceDTO
) -> None:
    uuid = str(device.uuid)

    protocol = await Context.create_client_context()

    request = Message(
        code=Code.DELETE, uri=f"coap://127.0.0.1/{uuid}/commands"
    )
    response = await protocol.request(request).response

    assert response.code.is_successful()
    assert len(response.payload) == 0


@pytest.mark.asyncio
async def test_device_data_resource_post_ok(
    coap_server: None, db_manager: None, device: DeviceDTO
) -> None:
    uuid = str(device.uuid)
    now = datetime.datetime.now(datetime.UTC)

    payload = {
        "i": device.imei[-6:],
        "t": now.timestamp(),
        "s": "voltage_sensor",
        "f": 1.3,
        "u": "V",
    }

    cbor_payload = cbor2.dumps(payload)

    protocol = await Context.create_client_context()

    request = Message(
        code=Code.POST,
        uri=f"coap://127.0.0.1/{uuid}/data",
        payload=cbor_payload,
    )

    response = await protocol.request(request).response

    assert response.code.is_successful()

    dps = await get_datapoints_by_device_uuid(device.uuid)
    assert len(dps) == 1

    dp = dps[0]
    assert dp is not None
    assert dp.device_uuid == device.uuid
    assert dp.timestamp == now
    assert dp.sensor == payload["s"]
    assert dp.val_float == payload["f"]
    assert dp.val_units == payload["u"]


@pytest.mark.asyncio
async def test_device_data_resource_post_invalid_cbor(
    coap_server: None, db_manager: None, device: DeviceDTO
) -> None:
    uuid = str(device.uuid)

    protocol = await Context.create_client_context()
    bad_payload = b"not-cbor"

    request = Message(
        code=Code.POST,
        uri=f"coap://127.0.0.1/{uuid}/data",
        payload=bad_payload,
    )

    response = await protocol.request(request).response
    assert response.code == Code.BAD_REQUEST
    assert response.payload == b"Invalid CBOR"


@pytest.mark.asyncio
async def test_device_data_resource_post_missing_imei_tail(
    coap_server: None, db_manager: None, device: DeviceDTO
) -> None:
    uuid = str(device.uuid)

    now = datetime.datetime.now(datetime.UTC)

    payload = {
        "t": now.timestamp(),
        "s": "voltage_sensor",
        "f": 1.3,
        "u": "V",
    }

    cbor_payload = cbor2.dumps(payload)
    protocol = await Context.create_client_context()

    request = Message(
        code=Code.POST,
        uri=f"coap://127.0.0.1/{uuid}/data",
        payload=cbor_payload,
    )

    response = await protocol.request(request).response
    assert response.code == Code.UNAUTHORIZED
    assert b"imei_tail" in response.payload


@pytest.mark.asyncio
async def test_device_data_resource_post_unauthorised_imei_tail(
    coap_server: None, db_manager: None, device: DeviceDTO
) -> None:
    uuid = str(device.uuid)

    now = datetime.datetime.now(datetime.UTC)

    payload = {
        "i": "000000",
        "t": now.timestamp(),
        "s": "voltage_sensor",
        "f": 1.3,
        "u": "V",
    }

    cbor_payload = cbor2.dumps(payload)
    protocol = await Context.create_client_context()

    request = Message(
        code=Code.POST,
        uri=f"coap://127.0.0.1/{uuid}/data",
        payload=cbor_payload,
    )

    response = await protocol.request(request).response
    assert response.code == Code.UNAUTHORIZED
    assert b"Unauthorised" in response.payload


@pytest.mark.asyncio
async def test_device_data_resource_post_invalid_timestamp_type(
    coap_server: None, db_manager: None, device: DeviceDTO
) -> None:
    uuid = str(device.uuid)

    payload = {
        "i": device.imei[-6:],
        "t": "not-a-number",
        "s": "voltage_sensor",
        "f": 1.3,
        "u": "V",
    }

    cbor_payload = cbor2.dumps(payload)
    protocol = await Context.create_client_context()

    request = Message(
        code=Code.POST,
        uri=f"coap://127.0.0.1/{uuid}/data",
        payload=cbor_payload,
    )

    response = await protocol.request(request).response
    assert response.code == Code.BAD_REQUEST
    assert b"Invalid timestamp" in response.payload


@pytest.mark.asyncio
async def test_device_data_resource_post_timestamp_exception(
    coap_server: None, db_manager: None, device: DeviceDTO
) -> None:
    uuid = str(device.uuid)

    payload = {
        "i": device.imei[-6:],
        "t": 1e20,
        "s": "voltage_sensor",
        "f": 1.3,
        "u": "V",
    }

    cbor_payload = cbor2.dumps(payload)
    protocol = await Context.create_client_context()

    request = Message(
        code=Code.POST,
        uri=f"coap://127.0.0.1/{uuid}/data",
        payload=cbor_payload,
    )

    response = await protocol.request(request).response
    assert response.code == Code.BAD_REQUEST
    assert b"Invalid timestamp" in response.payload


@pytest.mark.asyncio
async def test_device_data_resource_post_missing_sensor(
    coap_server: None, db_manager: None, device: DeviceDTO
) -> None:
    uuid = str(device.uuid)

    now = datetime.datetime.now(datetime.UTC)

    payload = {
        "i": "123456",
        "t": now.timestamp(),
        "f": 1.3,
        "u": "V",
    }

    cbor_payload = cbor2.dumps(payload)
    protocol = await Context.create_client_context()

    request = Message(
        code=Code.POST,
        uri=f"coap://127.0.0.1/{uuid}/data",
        payload=cbor_payload,
    )

    response = await protocol.request(request).response
    assert response.code == Code.BAD_REQUEST
    assert b"Missing sensor" in response.payload


@pytest.mark.asyncio
async def test_device_data_resource_post_missing_value_fields(
    coap_server: None, db_manager: None, device: DeviceDTO
) -> None:
    uuid = str(device.uuid)

    now = datetime.datetime.now(datetime.UTC)

    payload = {
        "i": "123456",
        "t": now.timestamp(),
        "s": "voltage_sensor",
        "u": "V",
    }

    cbor_payload = cbor2.dumps(payload)
    protocol = await Context.create_client_context()

    request = Message(
        code=Code.POST,
        uri=f"coap://127.0.0.1/{uuid}/data",
        payload=cbor_payload,
    )

    response = await protocol.request(request).response
    assert response.code == Code.BAD_REQUEST
    assert response.payload == b"Missing value"
