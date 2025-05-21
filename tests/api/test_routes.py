import pytest
from typing import Generator, AsyncGenerator
import httpx
import os
import subprocess
import time
import uuid
from testcontainers.redis import RedisContainer

from sense_web.db.session import sessionmanager
from sense_web.api.server import start_api

DB_URI = "sqlite+aiosqlite:///pytest.db"
os.environ["DATABASE_URI"] = DB_URI


@pytest.fixture(scope="module")
def api_server() -> Generator[str, None, None]:
    host = "127.0.0.1"
    port = 6789

    redis = RedisContainer().with_exposed_ports(6379)
    redis.start()

    os.environ["REDIS_HOST"] = redis.get_container_host_ip()
    os.environ["REDIS_PORT"] = redis.get_exposed_port(6379)

    time.sleep(1)

    proc = start_api(
        host=host,
        port=port,
        env=dict(os.environ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        # Wait for server to start
        time.sleep(2)
        if proc.poll() is not None:
            raise RuntimeError("API server exited prematurely")
        yield f"http://{host}:{port}"
    finally:
        redis.stop()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture(scope="function")
async def db_manager() -> AsyncGenerator[None]:
    await sessionmanager.init(DB_URI)

    async with sessionmanager.connect() as conn:
        await sessionmanager.drop_all(conn)
        await sessionmanager.create_all(conn)

    yield

    await sessionmanager.close()


def test_api_root_get(
    api_server: str,
) -> None:
    with httpx.Client(base_url=api_server) as client:
        response = client.get("/api/", timeout=2)
        assert response.status_code == 200


def test_api_device_register_ok(api_server: str, db_manager: None) -> None:
    with httpx.Client(base_url=api_server) as client:
        data = {"imei": "123456789"}

        response = client.post("/api/devices", json=data, timeout=2)

        assert response.status_code == 201

        json = response.json()
        assert json.get("imei", "") == data["imei"]
        assert json.get("uuid") is not None or ""


def test_api_device_register_already_exists(
    api_server: str, db_manager: None
) -> None:
    with httpx.Client(base_url=api_server) as client:
        data = {"imei": "123456789"}

        response = client.post("/api/devices", json=data, timeout=2)

        assert response.status_code == 201

        json = response.json()
        assert json.get("imei", "") == data["imei"]
        assert json.get("uuid") is not None or ""

        response = client.post("/api/devices", json=data, timeout=2)

        assert response.status_code == 409


def test_api_device_list_all(api_server: str, db_manager: None) -> None:
    with httpx.Client(base_url=api_server) as client:
        # Register two devices
        device1 = {"imei": "100000000000001"}
        device2 = {"imei": "100000000000002"}

        res1 = client.post("/api/devices", json=device1, timeout=2)
        res2 = client.post("/api/devices", json=device2, timeout=2)

        assert res1.status_code == 201
        assert res2.status_code == 201

        # Get all devices
        response = client.get("/api/devices", timeout=2)

        assert response.status_code == 200
        devices = response.json()
        assert isinstance(devices, list)
        assert len(devices) == 2

        imeis = [d["imei"] for d in devices]
        assert device1["imei"] in imeis
        assert device2["imei"] in imeis


def test_api_device_get_by_uuid(api_server: str, db_manager: None) -> None:
    with httpx.Client(base_url=api_server) as client:
        data = {"imei": "200000000000001"}
        register_response = client.post("/api/devices", json=data, timeout=2)

        assert register_response.status_code == 201
        uuid = register_response.json()["uuid"]

        response = client.get(f"/api/devices/{uuid}", timeout=2)

        assert response.status_code == 200
        device = response.json()
        assert device["imei"] == data["imei"]
        assert device["uuid"] == uuid


def test_api_device_get_by_imei(api_server: str, db_manager: None) -> None:
    with httpx.Client(base_url=api_server) as client:
        data = {"imei": "200000000000002"}
        register_response = client.post("/api/devices", json=data, timeout=2)

        assert register_response.status_code == 201
        uuid = register_response.json()["uuid"]

        response = client.get(f"/api/devices/imei/{data['imei']}", timeout=2)

        assert response.status_code == 200
        device = response.json()
        assert device["imei"] == data["imei"]
        assert device["uuid"] == uuid


def test_api_device_get_by_uuid_not_found(
    api_server: str, db_manager: None
) -> None:
    with httpx.Client(base_url=api_server) as client:
        unknown_uuid = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/devices/{unknown_uuid}", timeout=2)

        assert response.status_code == 404
        assert response.json()["detail"] == "Device not found"


def test_api_device_get_by_imei_not_found(
    api_server: str, db_manager: None
) -> None:
    with httpx.Client(base_url=api_server) as client:
        unknown_imei = "999999999999999"
        response = client.get(f"/api/devices/imei/{unknown_imei}", timeout=2)

        assert response.status_code == 404
        assert response.json()["detail"] == "Device not found"


def test_api_commands_post_get(api_server: str, db_manager: None) -> None:
    with httpx.Client(base_url=api_server) as client:
        data = {"imei": "200000000000001"}
        register_response = client.post("/api/devices", json=data, timeout=2)

        assert register_response.status_code == 201
        uuid = register_response.json()["uuid"]

        commands_list = client.get(f"/api/devices/{uuid}/commands", timeout=2)
        assert commands_list.status_code == 200
        assert len(commands_list.json()) == 0

        command = {"cmd": "test", "timestamp": 1234}
        command_response = client.post(
            f"/api/devices/{uuid}/commands", json=command, timeout=2
        )
        assert command_response.status_code == 202

        commands_list = client.get(f"/api/devices/{uuid}/commands", timeout=2)
        assert commands_list.status_code == 200
        assert commands_list.json()[0] == command


def test_api_commands_post_not_found(
    api_server: str, db_manager: None
) -> None:
    with httpx.Client(base_url=api_server) as client:
        device_uuid = uuid.uuid4()
        command = {"cmd": "test", "timestamp": 1234}
        command_response = client.post(
            f"/api/devices/{device_uuid}/commands", json=command, timeout=2
        )
        assert command_response.status_code == 404


def test_api_commands_get_not_found(api_server: str, db_manager: None) -> None:
    with httpx.Client(base_url=api_server) as client:
        device_uuid = uuid.uuid4()
        command_response = client.get(
            f"/api/devices/{device_uuid}/commands", timeout=2
        )
        assert command_response.status_code == 404
