from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api.v1 import api as v1_api
from app.mqtt.client import mqtt_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    mqtt_client.connect()
    yield
    # --- SHUTDOWN ---
    mqtt_client.disconnect()


app = FastAPI(
    title="IoT System",
    lifespan=lifespan
)

# ✅ CORS middleware (PHẢI đặt sau khi tạo app, trước router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://iot-attendance-pi.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Router
app.include_router(
    v1_api.api_router,
    prefix="/api/v1"
)
