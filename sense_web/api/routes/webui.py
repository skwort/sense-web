from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sense_web.services.device import list_devices

router = APIRouter()
templates = Jinja2Templates(directory="sense_web/api/webui/templates")


@router.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    devices = await list_devices()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "devices": devices},
    )
