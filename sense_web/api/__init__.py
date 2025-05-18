from fastapi import APIRouter
from .routes import root

api_router = APIRouter()
api_router.include_router(root.router)
