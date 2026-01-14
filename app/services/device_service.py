# app/services/device_service.py
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.models import Device, DoorStateEnum

class DeviceService:
    def __init__(self):
        self.db = SessionLocal()

    def get_db(self):
        # Helper để lấy session mới nếu cần thiết
        return SessionLocal()

    def exists(self, device_id: str) -> bool:
        with self.get_db() as session:
            return session.query(Device).filter(Device.device_id == device_id).first() is not None

    # [NEW] Cập nhật heartbeat (Online)
    def update_heartbeat(self, device_id: str):
        with self.get_db() as session:
            device = session.query(Device).filter(Device.device_id == device_id).first()
            if device:
                device.status = "online"
                device.last_seen = datetime.now()
                session.commit()

    # [NEW] Cập nhật trạng thái cửa
    def update_door_state(self, device_id: str, state_str: str):
        # Map string từ MQTT sang Enum
        # MQTT gửi: "locked", "open"... -> Cần chuyển thành "LOCKED", "OPEN"
        state_map = {
            "locked": DoorStateEnum.LOCKED,
            "open": DoorStateEnum.OPEN,
            "unlocked_wait_open": DoorStateEnum.WAITING_TO_OPEN
        }
        
        enum_val = state_map.get(state_str.lower())
        if not enum_val:
            return # Hoặc log warning nếu state không hợp lệ

        with self.get_db() as session:
            device = session.query(Device).filter(Device.device_id == device_id).first()
            if device:
                device.door_state = enum_val
                session.commit()

    # [NEW] Lấy trạng thái đầy đủ & Tự động check Offline
    def get_full_status(self, device_id: str):
        with self.get_db() as session:
            device = session.query(Device).filter(Device.device_id == device_id).first()
            if not device:
                return None
            
            # Logic: Nếu quá 2 phút không thấy last_seen -> set offline
            is_offline = False
            if device.last_seen:
                diff = datetime.now() - device.last_seen
                if diff > timedelta(minutes=2):
                    is_offline = True
            else:
                # Chưa từng thấy -> coi như offline
                is_offline = True

            # Nếu phát hiện offline mà trong DB vẫn ghi online -> Update lại ngay
            if is_offline and device.status == "online":
                device.status = "offline"
                session.commit()
                session.refresh(device)

            return {
                "device_id": device.device_id,
                "connection_status": device.status, # online/offline
                "door_state": device.door_state,    # LOCKED/OPEN...
                "last_seen": device.last_seen
            }

device_service = DeviceService()