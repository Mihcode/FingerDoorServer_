from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # <--- QUAN TRỌNG: Phải có import này
from contextlib import asynccontextmanager

from app.api.v1 import api as v1_api
from app.mqtt.client import mqtt_client

# --- LIFESPAN (QUẢN LÝ KHỞI ĐỘNG/TẮT) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Startup: Kết nối MQTT
    print("🚀 System Starting...")
    mqtt_client.connect()
    
    yield
    
    # 2. Shutdown: Ngắt kết nối MQTT
    print("🛑 System Shutting down...")
    mqtt_client.disconnect()

# --- KHỞI TẠO APP ---
app = FastAPI(
    title="IoT System",
    lifespan=lifespan
)

# --- CẤU HÌNH CORS (CHO PHÉP WEB KẾT NỐI) ---
# Đây là phần bạn cậu ấy cần
origins = [
    "http://localhost:3000",                # Cho phép test trên máy tính cá nhân (nếu chạy local)
    "https://iot-attendance-pi.vercel.app", # Cho phép Web trên Vercel của bạn cậu ấy
    "*"                                     # (Tạm thời) Cho phép TẤT CẢ để tránh lỗi vặt khi dev
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,      # Danh sách các nguồn được phép
    allow_credentials=True,
    allow_methods=["*"],        # Cho phép mọi phương thức (GET, POST, PUT, DELETE...)
    allow_headers=["*"],        # Cho phép mọi Header
)

# --- ĐĂNG KÝ ROUTER ---
app.include_router(
    v1_api.api_router,
    prefix="/api/v1"
)
