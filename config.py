import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Khai báo các biến bắt buộc phải có trong .env
    PROJECT_NAME: str = "FingerDoor Project"
    DATABASE_URL: str
    MQTT_BROKER: str
    MQTT_PORT: int
    MQTT_USERNAME: str = ""
    MQTT_PASSWORD: str = ""
    MQTT_BASE_TOPIC: str

    class Config:
        env_file = ".env"
        # Bỏ qua các biến thừa trong .env không khai báo ở trên
        extra = "ignore"
      
settings = Settings()
