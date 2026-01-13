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
    device_id: str
    finger_id: int
    enrolled_at: str

class DeviceLogResp(BaseModel):
    event_type: str
    finger_id: Optional[int]
    employee_id: Optional[int]
    timestamp: str
    success: bool
    message: Optional[str]

# ==========================================
# 1. Đăng ký vân tay (Enroll)
# ==========================================
@router.post(
    "/{device_id}/fingerprints/enroll",
    status_code=status.HTTP_202_ACCEPTED
)
def enroll_fingerprint(
    device_id: str,
    finger_id: int,
    body: EnrollFingerprintReq
):
    if not device_service.exists(device_id):
        raise HTTPException(404, "Device not found")

    # 1. Set Context để chờ MQTT phản hồi
    enroll_context.set(
        device_id=device_id,
        employee_id=body.employee_id,
        finger_id=finger_id
    )

    # 2. Gửi lệnh xuống MQTT
    mqtt_client.send_command(
        device_id=device_id,
        cmd="fp_enroll",
        finger_id=finger_id
    )

    # 3. [NEW] Ghi log: Đã gửi yêu cầu đăng ký
    device_log_service.add(
        device_id=device_id,
        employee_id=body.employee_id,
        finger_id=finger_id,
        event_type="enroll_req",   # Đánh dấu đây là request từ server
        success=1,                 # Request gửi đi thành công (chưa biết device có nhận được ko)
        message=f"Server sent enroll command for finger {finger_id}",
        timestamp=datetime.now()
    )

    return {
        "device_id": device_id,
        "employee_id": body.employee_id,
        "finger_id": finger_id,
        "status": "waiting_device_response"
    }

# ==========================================
# 2. Xóa vân tay (Delete)
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
# 3. Mở cửa từ xa (Open Door)
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

# ==========================================
# Các API Read (Get) giữ nguyên
# ==========================================
@router.get(
    "/{device_id}/fingerprints",
    response_model=List[FingerprintResp]
)
def list_fingerprints(device_id: str):
    if not device_service.exists(device_id):
        raise HTTPException(404, "Device not found")
    return fingerprint_service.get_by_device(device_id)

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
    status_val = device_service.get_status(device_id)
    return {
        "device_id": device_id,
        "status": status_val or "unknown"
    }