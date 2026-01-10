from fastapi import APIRouter

from app.api.v1.endpoints import devices
from app.api.v1.endpoints import users

api_router = APIRouter()

# Đăng ký router devices
api_router.include_router(devices.router, prefix="/devices", tags=["Devices Control"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])