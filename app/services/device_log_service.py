# app/services/device_log_service.py

from datetime import datetime
from typing import List, Optional, Union
from sqlalchemy.orm import Session

# Import kết nối DB và Model
from app.database import SessionLocal
from app.models.models import DeviceLog

class DeviceLogService:

    def add(
        self,
        device_id: str,
        event_type: str,
        finger_id: Optional[int] = None,
        employee_id: Optional[int] = None,
        success: bool = True,
        message: Optional[str] = None,
        timestamp: Optional[Union[str, datetime]] = None,
    ):
        """
        Ghi log vào Database.
        timestamp: Có thể là chuỗi (từ MQTT json) hoặc datetime object (từ API).
        """
        db: Session = SessionLocal()
        try:
            # 1. Xử lý thời gian: Nếu không truyền vào, dùng giờ hiện tại
            if timestamp is None:
                final_timestamp = datetime.now()
            else:
                final_timestamp = timestamp

            # 2. Convert success (bool -> int) vì trong Model khai báo là Integer
            success_int = 1 if success else 0

            # 3. Tạo record
            new_log = DeviceLog(
                device_id=device_id,
                event_type=event_type,
                finger_id=finger_id,
                employee_id=employee_id,
                success=success_int,
                message=message,
                timestamp=final_timestamp
            )

            db.add(new_log)
            db.commit()
            db.refresh(new_log) # (Tùy chọn) lấy lại ID vừa tạo
            
            return new_log

        except Exception as e:
            db.rollback()
            # Bạn có thể log error ra console hoặc file log hệ thống
            print(f"[DeviceLogService] Error adding log: {e}")
            raise e
        finally:
            db.close()

    def get_recent(self, device_id: str, limit: int = 50) -> List[DeviceLog]:
        """
        Lấy danh sách log gần đây nhất của một thiết bị.
        Sắp xếp giảm dần theo timestamp.
        """
        db: Session = SessionLocal()
        try:
            logs = (
                db.query(DeviceLog)
                .filter(DeviceLog.device_id == device_id)
                .order_by(DeviceLog.timestamp.desc())
                .limit(limit)
                .all()
            )
            return logs
        finally:
            db.close()

# Khởi tạo instance singleton để dùng ở nơi khác
device_log_service = DeviceLogService()