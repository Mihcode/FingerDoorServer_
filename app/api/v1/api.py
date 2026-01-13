from fastapi import APIRouter

from app.api.v1.endpoints import devices, users, employees

api_router = APIRouter()

# Đăng ký router devices
api_router.include_router(devices.router, prefix="/devices", tags=["Devices Control"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(employees.router, prefix="/employees", tags=["Employees"])