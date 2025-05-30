import os
import sys
import subprocess
from typing import IO, Dict, AsyncIterator, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from fastapi.staticfiles import StaticFiles
from .routes import root, devices, webui

from sense_web.db.session import sessionmanager
from sense_web.services.ipc import ipc

DB_URI = os.getenv("DATABASE_URI", "sqlite+aiosqlite:///./dev.db")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

api_router = APIRouter()
api_router.include_router(root.router)
api_router.include_router(devices.router)


def init_api(use_webui: bool = True) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await sessionmanager.init(DB_URI)
        await ipc.init(host=REDIS_HOST, port=REDIS_PORT)
        yield
        if sessionmanager._engine is not None:
            await sessionmanager.close()
        await ipc.close()

    api = FastAPI(title="SENSE Web - CoAP-HTTP Gateway", lifespan=lifespan)
    api.include_router(api_router, prefix="/api")

    if use_webui:
        api.include_router(webui.router)
        api.mount(
            "/static",
            StaticFiles(directory="sense_web/api/webui/static"),
            name="static",
        )

    return api


server = init_api()


def start_api(
    host: str,
    port: int,
    env: Dict[str, str],
    stdout: IO[Any] | int,
    stderr: IO[Any] | int,
) -> subprocess.Popen[bytes]:
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "sense_web.api.server:server",
            "--host",
            host,
            "--port",
            str(port),
        ],
        env=env,
        stdout=stdout,
        stderr=stderr,
    )

    return proc
