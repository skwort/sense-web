from enum import IntEnum
from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from typing import List

from sense_web.exceptions import DeviceAlreadyExists
from sense_web.services.datapoint import (
    get_datapoints_by_device_uuid,
    delete_datapoint,
)
from sense_web.dto.datapoint import DataPointDTO
from sense_web.services.device import (
    register_device,
    list_devices,
    get_device_by_imei,
    get_device_by_uuid,
)
from sense_web.services.ipc import (
    ipc,
    PubSubChannels,
    peek_commands,
    enqueue_command,
)
from sense_web.services.command import CommandType

router = APIRouter()


class DeviceRegistrationRequest(BaseModel):
    imei: str
    name: str


class DeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    imei: str
    uuid: UUID
    name: str


class CommandRequest(BaseModel):
    ty: CommandType = Field(..., description="Command type")
    ta: int = Field(
        ..., description="Target ID (sensor or rail, depending on ty)"
    )
    i: int | None = Field(
        None, description="Integer payload, e.g., poll interval in ms"
    )
    b: bool | None = Field(
        None, description="Boolean payload, e.g., rail state"
    )


class CommandResponse(BaseModel):
    ty: CommandType
    ta: int
    i: int | None = None
    b: bool | None = None


@router.post(
    "/devices",
    response_model=DeviceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    request: DeviceRegistrationRequest,
) -> DeviceResponse:
    try:
        device = await register_device(request.imei, request.name)
    except DeviceAlreadyExists as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    await ipc.publish(
        PubSubChannels.DEVICE_REGISTRATION.value, str(device.uuid)
    )

    return DeviceResponse.model_validate(device)


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


@router.get(
    "/devices/{device_uuid}/data",
    response_model=list[DataPointDTO] | None,
    status_code=status.HTTP_200_OK,
)
async def datapoints_get(device_uuid: UUID) -> list[DataPointDTO] | None:
    device = await get_device_by_uuid(device_uuid)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    return await get_datapoints_by_device_uuid(device_uuid)


@router.delete(
    "/devices/{device_uuid}/data/{datapoint_uuid}",
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def datapoint_delete(
    device_uuid: UUID, datapoint_uuid: UUID
) -> JSONResponse | None:
    device = await get_device_by_uuid(device_uuid)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    deleted = await delete_datapoint(datapoint_uuid)

    if not deleted:
        raise HTTPException(status_code=404, detail="Datapoint not found")

    return JSONResponse(
        content={"detail": "Datapoint deleted"}, status_code=200
    )
