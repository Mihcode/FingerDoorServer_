# app/core/config.py
from pydantic_settings import BaseSettings

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
    
    class Config:
        env_file = ".env"

settings = Settings()
