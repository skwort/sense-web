import pytest
from typing import Generator
import httpx
import os
import subprocess
import time

from sense_web.api import start_api


@pytest.fixture
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


def test_api_root_get(api_server: str) -> None:
    with httpx.Client(base_url=api_server) as client:
        response = client.get("/api/", timeout=2)
        assert response.status_code == 200
