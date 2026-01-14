from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from app.mqtt.client import mqtt_client
from app.services.fingerprint_service import fingerprint_service
from app.services.device_log_service import device_log_service
from app.services.device_service import device_service
from app.services.enroll_context import enroll_context

router = APIRouter()

class EnrollFingerprintReq(BaseModel):
    employee_id: int

class FingerprintResp(BaseModel):
    id: int
    employee_id: int
    emp_code: Optional[str] = None
    device_id: str
    finger_id: int
    enrolled_at: Optional[datetime]

    class Config:
        from_attributes = True

class DeviceLogResp(BaseModel):
    event_type: str
    finger_id: Optional[int]
    employee_id: Optional[int]
    timestamp: str
    success: bool
    message: Optional[str]

class DeviceStatusResp(BaseModel):
    device_id: str
    status: str       # online/offline
    door_state: str   # LOCKED/OPEN/WAITING_TO_OPEN
    last_seen: Optional[datetime]


# ==========================================
# 1. Đăng ký vân tay (Enroll)
# ==========================================
@router.post(
    "/{device_id}/fingerprints/enroll",
    status_code=status.HTTP_202_ACCEPTED
)
def enroll_fingerprint(
    device_id: str,
    body: EnrollFingerprintReq
):
    # 1. Kiểm tra thiết bị tồn tại
    if not device_service.exists(device_id):
        raise HTTPException(404, "Device not found")

    # 2. [NEW] Tự động tìm ID trống nhỏ nhất (0-128)
    next_finger_id = fingerprint_service.get_next_available_id(device_id)

    if next_finger_id is None:
        raise HTTPException(
            status_code=400, 
            detail="Device fingerprint memory is full (Max 128)"
        )

    # 3. Set Context để chờ MQTT phản hồi (dùng ID vừa tìm được)
    enroll_context.set(
        device_id=device_id,
        employee_id=body.employee_id,
        finger_id=next_finger_id
    )

    # 4. Gửi lệnh xuống MQTT với ID tự động
    mqtt_client.send_command(
        device_id=device_id,
        cmd="fp_enroll",
        finger_id=next_finger_id
    )

    # 5. Ghi log
    device_log_service.add(
        device_id=device_id,
        employee_id=body.employee_id,
        finger_id=next_finger_id,
        event_type="enroll_req",
        success=1,
        message=f"Server auto-assigned finger_id {next_finger_id} and sent command",
        timestamp=datetime.now()
    )

    return {
        "device_id": device_id,
        "employee_id": body.employee_id,
        "assigned_finger_id": next_finger_id, # Trả về ID để FE biết
        "status": "waiting_device_response"
    }

# ==========================================
# 2. Check trạng thái đăng ký (GET)
# ==========================================

@router.get("/{device_id}/fingerprints/{finger_id}/enroll-status")
def check_enroll_status(device_id: str, finger_id: int):
    """
    API để Frontend gọi định kỳ (polling) kiểm tra kết quả.
    """
    # 1. Tìm log kết quả trong DB
    log = device_log_service.get_enroll_status(device_id, finger_id)

    # 2. Nếu chưa có log -> Thiết bị chưa gửi phản hồi xong
    if not log:
        return {
            "status": "pending",
            "message": "Waiting for device..."
        }

    # 3. Nếu có log -> Trả về kết quả (dựa vào cột success)
    # Kiểm tra xem log này có cũ quá không? (Optional: ví dụ log từ hôm qua thì ko tính)
    # Ở đây giả định quy trình làm liền mạch nên lấy log mới nhất là đúng.
    
    if log.success == 1:
        return {
            "status": "success",
            "message": "Enrollment completed successfully"
        }
    else:
        return {
            "status": "failed",
            "message": log.message or "Device reported failure"
        }
# ==========================================
# 3. Xóa vân tay (Delete)
# ==========================================
@router.delete(
    "/{device_id}/fingerprints/{finger_id}",
    status_code=status.HTTP_202_ACCEPTED
)
def delete_fingerprint(device_id: str, finger_id: int):

    fingerprint = fingerprint_service.get_by_device_and_finger(
        device_id=device_id,
        finger_id=finger_id
    )

    if not fingerprint:
        raise HTTPException(404, "Fingerprint not found")

    # Lưu lại employee_id trước khi xóa để ghi log
    emp_id = fingerprint.employee_id

    # 1. Gửi lệnh xóa xuống MQTT
    mqtt_client.send_command(
        device_id=device_id,
        cmd="fp_delete",
        finger_id=finger_id
    )

    # 2. Xóa trong DB (Soft delete hoặc Hard delete tùy logic service của bạn)
    fingerprint_service.mark_deleted(fingerprint.id)

    # 3. [NEW] Ghi log: Đã thực hiện lệnh xóa
    device_log_service.add(
        device_id=device_id,
        employee_id=emp_id,
        finger_id=finger_id,
        event_type="delete_req",
        success=1,
        message="Server processed delete request",
        timestamp=datetime.now()
    )

    return {
        "device_id": device_id,
        "finger_id": finger_id,
        "status": "delete_command_sent"
    }

# ==========================================
# 4. Mở cửa từ xa (Open Door)
# ==========================================
@router.post("/{device_id}/door/open")
def open_door(device_id: str):

    if not device_service.exists(device_id):
        raise HTTPException(404, "Device not found")

    # 1. Gửi lệnh mở cửa
    mqtt_client.send_command(
        device_id=device_id,
        cmd="door_unlock"
    )

    # 2. [NEW] Ghi log: Admin/User mở cửa từ App/Web
    device_log_service.add(
        device_id=device_id,
        employee_id=None,          # Mở thủ công thường không gắn với employee cụ thể trừ khi có auth user
        finger_id=None,
        event_type="door_open_req",
        success=1,
        message="Remote door unlock requested via API",
        timestamp=datetime.now()
    )

    return {
        "device_id": device_id,
        "status": "door_unlock_sent"
    }

@router.get(
    "/{device_id}/fingerprints",
    response_model=List[FingerprintResp]
)
def list_fingerprints(
    device_id: str, 
    employee_id: Optional[int] = None  # <--- Thêm tham số này (FastAPI tự hiểu là Query Param)
):
    if not device_service.exists(device_id):
        raise HTTPException(404, "Device not found")
    
    # Truyền thêm employee_id vào service
    return fingerprint_service.get_by_device(device_id, employee_id)

@router.get(
    "/{device_id}/logs",
    response_model=List[DeviceLogResp]
)
def get_device_logs(device_id: str, limit: int = 50):
    if not device_service.exists(device_id):
        raise HTTPException(404, "Device not found")
    return device_log_service.get_recent(device_id, limit)

@router.get("/{device_id}/status")
def get_device_status(device_id: str):
    data = device_service.get_full_status(device_id)
    
    if not data:
        raise HTTPException(404, "Device not found")
    
    return {
        "device_id": data["device_id"],
        "status": data["connection_status"], # Trả về "online" hoặc "offline"
        "door_state": data["door_state"],    # Trả về Enum value
        "last_seen": data["last_seen"]
    }