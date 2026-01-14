# app/services/enroll_context.py
from typing import Dict, Optional, Any

class EnrollContext:
    def __init__(self):
        # Lưu trữ trạng thái theo device_id
        # Structure: { "device_abc": { "employee_id": 10, "finger_id": 5 } }
        self._storage: Dict[str, Dict[str, Any]] = {}

    def set(self, device_id: str, employee_id: int, finger_id: int):
        """Lưu context khi bắt đầu gửi lệnh Enroll"""
        self._storage[device_id] = {
            "employee_id": employee_id,
            "finger_id": finger_id
        }

    def pop(self, device_id: str) -> Optional[Dict[str, Any]]:
        """
        Lấy ra và xóa luôn context (dùng khi nhận phản hồi xong).
        Trả về dict { "employee_id": ..., "finger_id": ... } hoặc None.
        """
        return self._storage.pop(device_id, None)

    def get(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Lấy xem thử (không xóa)"""
        return self._storage.get(device_id)

    def clear(self):
        self._storage.clear()

# 🔥 SINGLE INSTANCE
enroll_context = EnrollContext()