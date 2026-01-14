# app/core/config.py
from pydantic_settings import BaseSettings
from datetime import time, datetime

class Settings(BaseSettings):
    PROJECT_NAME: str
    MQTT_BROKER: str
    MQTT_PORT: int
    MQTT_USERNAME: str = ""
    MQTT_PASSWORD: str = ""
    DATABASE_URL: str  
    MQTT_BASE_TOPIC: str
    SMTP_EMAIL: str
    SMTP_PASSWORD: str
    WORK_START_TIME: str
    
    def get_work_start_time(self) -> time:
        # Hàm tiện ích để chuyển chuỗi "09:00:00" thành đối tượng time
        try:
            return datetime.strptime(self.WORK_START_TIME, "%H:%M:%S").time()
        except ValueError:
            return time(9, 0, 0) # Fallback an toàn
        
    class Config:
        env_file = ".env"

settings = Settings()
