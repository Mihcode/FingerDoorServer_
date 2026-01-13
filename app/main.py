from fastapi import FastAPI
from app.api.v1 import api as v1_api
from contextlib import asynccontextmanager
from app.mqtt.client import mqtt_client
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://iot-attendance-pi.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    mqtt_client.connect()
    
    yield
    
    # --- SHUTDOWN ---
    mqtt_client.disconnect()

app = FastAPI(title="IoT System", lifespan=lifespan)
# Đăng ký router cho API v1
app.include_router(v1_api.api_router, prefix="/api/v1")
    
