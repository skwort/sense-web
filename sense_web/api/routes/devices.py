from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from sense_web.exceptions import DeviceAlreadyExists
from sense_web.services.device import register_device

router = APIRouter()


class DeviceRegistrationRequest(BaseModel):
    imei: str


class DeviceRegistrationResponse(BaseModel):
    imei: str
    uuid: str


@router.post(
    "/devices",
    response_model=DeviceRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    request: DeviceRegistrationRequest,
) -> DeviceRegistrationResponse:
    try:
        device = await register_device(request.imei)
    except DeviceAlreadyExists as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    return DeviceRegistrationResponse(imei=device.imei, uuid=str(device.uuid))
