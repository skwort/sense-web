import asyncio
import os
import sys
import signal
import subprocess
import time
from types import FrameType
from typing import List, Optional, Any
import logging as log

import sense_web.db as db
from sense_web.api.server import start_api

log.basicConfig(level=log.INFO)

DB_URI = os.getenv("DATABASE_URI", "sqlite+aiosqlite:///./dev.db")

procs: List[subprocess.Popen[Any]] = []


def shutdown_handler(sig: int, frame: Optional[FrameType]) -> None:
    log.info("Shutting down...")

    for proc in procs:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    sys.exit(0)


if __name__ == "__main__":
    # Initialise the database
    asyncio.run(db.session.sessionmanager.init(DB_URI))

    # Start the REST API
    api_proc = start_api(
        "0.0.0.0",
        8000,
        env=dict(os.environ),
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    procs.append(api_proc)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        shutdown_handler(signal.SIGINT, None)
