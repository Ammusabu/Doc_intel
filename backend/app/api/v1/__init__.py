from fastapi import APIRouter

from app.api.v1 import health, ml_debug

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(ml_debug.router)
