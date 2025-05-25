import os
import sys
import signal
import subprocess
import time
from types import FrameType
from typing import List, Optional, Any
import logging as log

from sense_web.api.server import start_api
from sense_web.coap.server import start_coap

log.basicConfig(level=log.INFO)

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
    # Start the REST API
    api_proc = start_api(
        "0.0.0.0",
        8000,
        env=dict(os.environ),
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    procs.append(api_proc)

    coap_proc = start_coap(
        "0.0.0.0",
        6873,
        env=dict(os.environ),
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    procs.append(coap_proc)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        shutdown_handler(signal.SIGINT, None)
