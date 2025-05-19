import sys
import subprocess
from typing import IO, Dict, AsyncIterator, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from .routes import root

from sense_web.db import sessionmanager

api_router = APIRouter()
api_router.include_router(root.router)


def init_api() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        if sessionmanager._engine is not None:
            await sessionmanager.close()

    api = FastAPI(title="SENSE Web - CoAP-HTTP Gateway", lifespan=lifespan)
    api.include_router(api_router, prefix="/api")

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
            "sense_web.api:server",
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
