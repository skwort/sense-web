from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict
from typing import List

from sense_web.exceptions import DeviceAlreadyExists
from sense_web.services.device import (
    register_device,
    list_devices,
    get_device_by_imei,
    get_device_by_uuid,
)
from sense_web.services.ipc import (
    peek_commands,
    enqueue_command,
)

router = APIRouter()


class DeviceRegistrationRequest(BaseModel):
    imei: str


class DeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    imei: str
    uuid: UUID


class CommandRequest(BaseModel):
    cmd: str
    timestamp: int


class CommandResponse(BaseModel):
    cmd: str
    timestamp: int


@router.post(
    "/devices",
    response_model=DeviceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    request: DeviceRegistrationRequest,
) -> DeviceResponse:
    try:
        device = await register_device(request.imei)
    except DeviceAlreadyExists as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    return DeviceResponse(imei=device.imei, uuid=device.uuid)


@router.get(
    "/devices",
    response_model=List[DeviceResponse],
    status_code=status.HTTP_200_OK,
)
async def devices_list() -> List[DeviceResponse]:
    devices = await list_devices()
    return [DeviceResponse.model_validate(d) for d in devices]


@router.get(
    "/devices/{uuid}",
    response_model=DeviceResponse,
    status_code=status.HTTP_200_OK,
)
async def devices_by_uuid(uuid: UUID) -> DeviceResponse:
    device = await get_device_by_uuid(uuid)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return DeviceResponse.model_validate(device)


@router.get(
    "/devices/imei/{imei}",
    response_model=DeviceResponse,
    status_code=status.HTTP_200_OK,
)
async def devices_by_imei(imei: str) -> DeviceResponse:
    device = await get_device_by_imei(imei)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return DeviceResponse.model_validate(device)


@router.post(
    "/devices/{uuid}/commands",
    status_code=status.HTTP_202_ACCEPTED,
)
async def commands_post(uuid: UUID, request: CommandRequest) -> None:
    device = await get_device_by_uuid(uuid)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    await enqueue_command(str(uuid), request.model_dump())


@router.get(
    "/devices/{uuid}/commands",
    response_model=list[CommandResponse] | None,
    status_code=status.HTTP_200_OK,
)
async def commands_get(uuid: UUID) -> list[CommandResponse] | None:
    device = await get_device_by_uuid(uuid)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    commands = await peek_commands(str(uuid))
    if len(commands) == 0:
        return []

    return [CommandResponse.model_validate(c) for c in commands]
