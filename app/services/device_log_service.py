# app/services/device_log_service.py

from typing import List, Optional


_logs = []


class DeviceLogService:

    def add(
        self,
        device_id: str,
        event_type: str,
        finger_id: Optional[int] = None,
        employee_id: Optional[int] = None,
        success: bool = True,
        message: Optional[str] = None,
        timestamp: Optional[str] = None,
    ):
        _logs.append({
            "id": len(_logs) + 1,
            "device_id": device_id,
            "event_type": event_type,
            "finger_id": finger_id,
            "employee_id": employee_id,
            "success": success,
            "message": message,
            "timestamp": timestamp,
        })

    def get_recent(self, device_id: str, limit: int = 50) -> List[dict]:
        return [
            log for log in reversed(_logs)
            if log["device_id"] == device_id
        ][:limit]


device_log_service = DeviceLogService()
