from fastapi import APIRouter
from typing import Dict

router = APIRouter()


@router.get("/")
async def root() -> Dict[str, str]:
    return {"message": "Sense Web is running"}
