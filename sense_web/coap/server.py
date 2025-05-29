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
import cbor2
import datetime

from sense_web.db.session import sessionmanager
from sense_web.services.datapoint import create_datapoint
from sense_web.services.device import list_devices, get_device_by_uuid
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


class DeviceDataResource(resource.Resource):
    def __init__(self, uuid: uuid.UUID) -> None:
        self._uuid = uuid

    async def render_post(self, request: Message) -> Message:
        """
        Handle POST requests from SENSE Core devices.

        Devices will send a CBOR payload with the following fields:
        - i -> imei_tail: Last 6 digits of device IMEI for validation
        - t -> timestamp: Unix timestamp indicating when value was recorded
        - s -> sensor: Sensor where value was recorded
        - f -> val_float: Float value if applicable
        - r -> val_str: String value if applicable
        - u -> val_units: Units of value if applicable

        The IMEI tail will be used to verify the identity of the device.
        """

        try:
            data = cbor2.loads(request.payload)
        except Exception:
            return Message(code=Code.BAD_REQUEST, payload=b"Invalid CBOR")

        device = await get_device_by_uuid(self._uuid)
        if device is None:
            return Message(code=Code.BAD_REQUEST, payload=b"Invalid device")

        imei_tail = data.get("i", None)
        if (
            not imei_tail
            or not isinstance(imei_tail, str)
            or len(imei_tail) != 6
        ):
            return Message(
                code=Code.UNAUTHORIZED, payload=b"Missing or invalid imei_tail"
            )

        if device.imei[-6:] != imei_tail:
            return Message(code=Code.UNAUTHORIZED, payload=b"Unauthorised")

        ts = data.get("t", None)
        if not isinstance(ts, (int, float)):
            return Message(code=Code.BAD_REQUEST, payload=b"Invalid timestamp")

        try:
            timestamp = datetime.datetime.fromtimestamp(
                ts, tz=datetime.timezone.utc
            )
        except (OverflowError, OSError):
            return Message(
                code=Code.BAD_REQUEST, payload=b"Invalid timestamp value"
            )

        sensor = data.get("s", None)
        val_float = data.get("f", None)
        val_str = data.get("r", None)
        val_units = data.get("u", None)

        if sensor is None:
            return Message(code=Code.BAD_REQUEST, payload=b"Missing sensor")

        if val_float is None and val_str is None:
            return Message(code=Code.BAD_REQUEST, payload=b"Missing value")

        dp = await create_datapoint(
            device_uuid=device.uuid,
            timestamp=timestamp,
            sensor=sensor,
            val_float=val_float,
            val_str=val_str,
            val_units=val_units,
        )

        log.info(f"Created DataPoint:\n{dp!r}")

        return Message(code=Code.CREATED, payload=b"DataPoint accepted")


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
    state.coap_site.add_resource(
        [str(device), "data"], DeviceDataResource(uuid.UUID(device))
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
        state.coap_site.add_resource(
            [str(d.uuid), "data"], DeviceDataResource(d.uuid)
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
