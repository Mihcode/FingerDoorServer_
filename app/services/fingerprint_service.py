# app/services/fingerprint_service.py
from typing import List, Optional
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.models import Fingerprint

class FingerprintService:
    def get_db(self):
        return SessionLocal()

    def get_by_device(self, device_id: str) -> List[Fingerprint]:
        """Lấy danh sách vân tay của 1 thiết bị từ DB"""
        with self.get_db() as session:
            return session.query(Fingerprint).filter(
                Fingerprint.device_id == device_id
            ).all()

    def get_by_device_and_finger(self, device_id: str, finger_id: int) -> Optional[Fingerprint]:
        """Tìm vân tay cụ thể để xử lý logic (VD: trước khi xóa)"""
        with self.get_db() as session:
            return session.query(Fingerprint).filter(
                Fingerprint.device_id == device_id,
                Fingerprint.finger_id == finger_id
            ).first()

    def add(self, device_id: str, employee_id: int, finger_id: int):
        """Lưu vân tay mới vào DB"""
        with self.get_db() as session:
            new_fp = Fingerprint(
                device_id=device_id,
                employee_id=employee_id,
                finger_id=finger_id
            )
            session.add(new_fp)
            session.commit()
            session.refresh(new_fp)
            return new_fp

    def mark_deleted(self, fp_id: int):
        """
        Xóa hẳn khỏi DB (Hard Delete).
        Cần xóa hẳn vì trong models.py có UniqueConstraint(device_id, finger_id).
        Nếu chỉ đánh dấu flag, DB sẽ báo lỗi Duplicate khi đăng ký lại ID này.
        """
        with self.get_db() as session:
            fp = session.query(Fingerprint).filter(Fingerprint.id == fp_id).first()
            if fp:
                session.delete(fp)
                session.commit()

    def get_next_available_id(self, device_id: str) -> Optional[int]:
        """
        Tìm số nguyên nhỏ nhất trong khoảng [0, 127] chưa được sử dụng
        cho thiết bị này để gán tự động.
        """
        MAX_FINGERS = 128  # Giới hạn bộ nhớ của module vân tay (thường là 127 hoặc vài trăm)
        
        with self.get_db() as session:
            # Lấy danh sách các ID đang tồn tại trong DB của device đó
            # Trả về list of tuples: [(0,), (1,), (5,)...]
            used_ids_query = session.query(Fingerprint.finger_id)\
                .filter(Fingerprint.device_id == device_id)\
                .all()
            
            # Convert sang set để tra cứu cho nhanh: {0, 1, 5}
            used_ids = {row[0] for row in used_ids_query}

            # Quét từ 0 -> Max, số nào chưa có trong set thì lấy ngay
            for candidate in range(MAX_FINGERS):
                if candidate not in used_ids:
                    return candidate
            
            # Nếu loop hết mà không return -> Full bộ nhớ
            return None

fingerprint_service = FingerprintService()