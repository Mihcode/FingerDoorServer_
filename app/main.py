from fastapi import FastAPI
from app.api.v1 import api as v1_api

app = FastAPI()

# Đăng ký router cho API v1
app.include_router(v1_api.api_router, prefix="/api/v1")
    
