# app/services/device_service.py
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.models import Device, DoorStateEnum

from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models.models import Device, DoorStateEnum

class DeviceService:
    def __init__(self):
        pass 

    def get_db(self):
        return SessionLocal()

    # [HELPER] Hàm lấy giờ hiện tại theo UTC+7
    def get_current_time_vn(self):
        # Lấy giờ UTC gốc + 7 tiếng = Giờ VN
        return datetime.utcnow() + timedelta(hours=7)

    def exists(self, device_id: str) -> bool:
        with self.get_db() as session:
            return session.query(Device).filter(Device.device_id == device_id).first() is not None

    # [UPDATE] Lưu last_seen theo giờ VN
    def update_heartbeat(self, device_id: str):
        with self.get_db() as session:
            device = session.query(Device).filter(Device.device_id == device_id).first()
            if device:
                device.status = "online"
                device.last_seen = self.get_current_time_vn() # <--- Dùng giờ VN
                session.commit()

    def update_door_state(self, device_id: str, state_str: str):
        state_map = {
            "locked": DoorStateEnum.LOCKED,
            "open": DoorStateEnum.OPEN,
            "unlocked_wait_open": DoorStateEnum.WAITING_TO_OPEN
        }
        
        enum_val = state_map.get(state_str.lower())
        if not enum_val:
            return

        with self.get_db() as session:
            device = session.query(Device).filter(Device.device_id == device_id).first()
            if device:
                device.door_state = enum_val
                session.commit()

    # [UPDATE] So sánh thời gian theo hệ quy chiếu VN
    def get_full_status(self, device_id: str):
        with self.get_db() as session:
            device = session.query(Device).filter(Device.device_id == device_id).first()
            if not device:
                return None
            
            is_offline = False
            
            if not device.last_seen:
                is_offline = True
            else:
                # 1. Lấy giờ hiện tại (VN)
                now_vn = self.get_current_time_vn()
                
                # 2. Lấy giờ trong DB (Đã là VN do lúc lưu mình dùng update_heartbeat ở trên)
                last_seen_vn = device.last_seen
                
                # 3. Tính độ lệch
                # Handle trường hợp lệch nhỏ do đồng hồ (last_seen lớn hơn hiện tại xíu)
                if last_seen_vn > now_vn:
                     diff_seconds = 0
                else:
                     diff = now_vn - last_seen_vn
                     diff_seconds = diff.total_seconds()

                # 4. Check timeout (120 giây)
                if diff_seconds > 120:
                    is_offline = True

            # Logic update trạng thái offline vào DB
            current_status = device.status
            
            if is_offline and current_status == "online":
                device.status = "offline"
                session.commit()
                session.refresh(device)
                
            final_status = "offline" if is_offline else "online"

            return {
                "device_id": device.device_id,
                "connection_status": final_status, 
                "door_state": device.door_state,   
                "last_seen": device.last_seen
            }
    

device_service = DeviceService()