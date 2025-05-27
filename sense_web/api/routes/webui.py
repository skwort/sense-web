import uuid
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sense_web.services.datapoint import get_datapoints_by_device_uuid
from sense_web.services.device import list_devices, get_device_by_uuid
from sense_web.services.ipc import peek_commands

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

    return templates.TemplateResponse(
        "device.html",
        {
            "request": request,
            "device": device,
            "commands": commands,
            "datapoints": datapoints,
        },
    )
