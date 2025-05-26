import argparse
import os
import uuid
import asyncio
import sys
import json
import subprocess
from typing import IO, Any
from aiocoap import Context, Message, Code
import aiocoap.resource as resource
import logging as log

from sense_web.db.session import sessionmanager
from sense_web.services.device import list_devices
from sense_web.services.ipc import (
    ipc,
    peek_commands,
    dequeue_command,
    PubSubChannels,
)

log.basicConfig(level=log.INFO)

DB_URI = os.getenv("DATABASE_URI", "sqlite+aiosqlite:///./dev.db")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))


def start_coap(
    host: str,
    port: int,
    env: dict[str, str],
    stdout: IO[Any] | int,
    stderr: IO[Any] | int,
) -> subprocess.Popen[bytes]:
    proc = subprocess.Popen(
        [
            sys.executable,
            "sense_web/coap/server.py",
            "--ip",
            host,
            "--port",
            str(port),
        ],
        env=env,
        stdout=stdout,
        stderr=stderr,
    )

    return proc


class DeviceResource(resource.Resource):
    def __init__(self, uuid: uuid.UUID) -> None:
        self._uuid = uuid

    async def render_get(self, request: Message) -> Message:
        return Message(
            code=Code.CONTENT, payload=bytes(str(self._uuid), "utf-8")
        )


class DeviceCommandResource(resource.Resource):
    def __init__(self, uuid: uuid.UUID) -> None:
        self._uuid = uuid

    async def render_delete(self, request: Message) -> Message:
        cmd = await dequeue_command(str(self._uuid))
        if not cmd:
            return Message(code=Code.CONTENT, payload=b"")

        log.info(f"Deleted command: {cmd}")
        return Message(code=Code.DELETED)

    async def render_get(self, request: Message) -> Message:
        commands = await peek_commands(str(self._uuid))
        if len(commands) == 0:
            return Message(code=Code.CONTENT, payload=b"")

        command = json.dumps(commands[0])
        return Message(code=Code.CONTENT, payload=bytes(command, "utf-8"))


class State:
    def __init__(self) -> None:
        self.coap_site: resource.Site | None = None


state = State()


async def device_registration_callback(device: str) -> None:
    log.info(f"Registering new device {device}")
    if state.coap_site is None:
        raise RuntimeError("CoAP server state is not initialised")
    state.coap_site.add_resource([device], DeviceResource(uuid.UUID(device)))
    state.coap_site.add_resource(
        [device, "commands"], DeviceCommandResource(uuid.UUID(device))
    )


async def main(server_ip: str, server_port: int) -> None:
    await sessionmanager.init(DB_URI)
    await ipc.init(host=REDIS_HOST, port=REDIS_PORT)

    await ipc.subscribe(
        PubSubChannels.DEVICE_REGISTRATION.value, device_registration_callback
    )

    state.coap_site = resource.Site()

    state.coap_site.add_resource(
        [".well-known", "core"],
        resource.WKCResource(state.coap_site.get_resources_as_linkheader),
    )

    devices = await list_devices()
    for d in devices:
        state.coap_site.add_resource([str(d.uuid)], DeviceResource(d.uuid))
        state.coap_site.add_resource(
            [str(d.uuid), "commands"], DeviceCommandResource(d.uuid)
        )

    await Context.create_server_context(
        state.coap_site,
        bind=(server_ip, server_port),
        transports=["udp6"],
    )

    try:
        await asyncio.get_running_loop().create_future()
    except asyncio.CancelledError:
        log.info("CoAP server shutting down cleanly.")

    await sessionmanager.close()
    await ipc.unsubscribe(PubSubChannels.DEVICE_REGISTRATION.value)
    await ipc.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SENSE Web CoAP Server")
    parser.add_argument(
        "--ip",
        default="127.0.0.1",
        type=str,
        help="The IP the CoAP server will bind to",
    )
    parser.add_argument(
        "--port",
        default=5683,
        type=int,
        help=(
            "The port the CoAP server will listen on. Note that the server "
            "uses the udp6 based transport, which is interoperable with both "
            "IPv4 and IPv6 requests."
        ),
    )

    args = parser.parse_args()

    asyncio.run(main(server_ip=args.ip, server_port=args.port))
