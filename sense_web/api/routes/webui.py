import uuid
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.encoders import jsonable_encoder
from fastapi.templating import Jinja2Templates
from sense_web.services.datapoint import get_datapoints_by_device_uuid
from sense_web.services.device import list_devices, get_device_by_uuid
from sense_web.services.ipc import peek_commands
from sense_web.services.command import (
    CMD_TYPE_MAP,
    CMD_SENSOR_MAP,
    CMD_RAIL_MAP,
)

router = APIRouter()
templates = Jinja2Templates(directory="sense_web/api/webui/templates")


@router.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    devices = await list_devices()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "devices": devices},
    )


@router.get("/devices/{uuid}", response_class=HTMLResponse)
async def device(uuid: uuid.UUID, request: Request) -> HTMLResponse:
    device = await get_device_by_uuid(uuid)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    commands = await peek_commands(str(uuid))

    datapoints = await get_datapoints_by_device_uuid(uuid)
    datapoints_dict = [jsonable_encoder(d) for d in datapoints]
    sensors = sorted(set(dp.sensor for dp in datapoints))

    return templates.TemplateResponse(
        "device.html",
        {
            "request": request,
            "device": device,
            "commands": commands,
            "datapoints": datapoints,
            "datapoints_dict": datapoints_dict,
            "sensors": sensors,
            "cmd_type_map": {
                k.value: v for k, v in CMD_TYPE_MAP.items() if k > 0
            },
            "cmd_sensor_map": {k.value: v for k, v in CMD_SENSOR_MAP.items()},
            "cmd_rail_map": {k.value: v for k, v in CMD_RAIL_MAP.items()},
        },
    )


@router.get("/command-form-fields", response_class=HTMLResponse)
async def get_command_form_fields(request: Request, ty: int) -> HTMLResponse:
    return templates.TemplateResponse(
        "command_form_fields.html",
        {
            "request": request,
            "ty": ty,
            "cmd_sensor_map": {k.value: v for k, v in CMD_SENSOR_MAP.items()},
            "cmd_rail_map": {k.value: v for k, v in CMD_RAIL_MAP.items()},
        },
    )
