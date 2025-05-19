import pytest
from typing import Generator, AsyncGenerator
import httpx
import os
import subprocess
import time

from sense_web.db.session import sessionmanager
from sense_web.api.server import start_api

DB_URI = "sqlite+aiosqlite:///pytest.db"
os.environ["DATABASE_URI"] = DB_URI


@pytest.fixture(scope="module")
def api_server() -> Generator[str, None, None]:
    host = "127.0.0.1"
    port = 6789

    proc = start_api(
        host=host,
        port=port,
        env=dict(os.environ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        # wait for server to start
        time.sleep(1)
        if proc.poll() is not None:
            raise RuntimeError("API server exited prematurely")
        yield f"http://{host}:{port}"
    finally:
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
