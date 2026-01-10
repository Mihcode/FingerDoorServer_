from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional

from app.mqtt.client import mqtt_client
from app.services.fingerprint_service import fingerprint_service
from app.services.device_log_service import device_log_service
from app.services.device_service import device_service
from app.services.enroll_context import enroll_context

router = APIRouter(
    prefix="/devices",
    tags=["Devices"]
)


router = APIRouter(prefix="/devices", tags=["Devices"])

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

@router.post(
    "/{device_id}/fingerprints/enroll",
    status_code=status.HTTP_202_ACCEPTED
)
def enroll_fingerprint(device_id: str, body: EnrollFingerprintReq):
    """
    Gửi lệnh enroll vân tay xuống ESP32.
    DB chỉ ghi khi nhận MQTT event fp_enroll_done.
    """

    if not device_service.exists(device_id):
        raise HTTPException(404, "Device not found")
    print(f"[CTX SET] device_id={device_id} employee_id={body.employee_id}")
    print("[DEBUG] enroll_context =", enroll_context.dump())

    enroll_context.set(
        device_id=device_id,
        employee_id=body.employee_id
    )
    

    # 2. Gửi command xuống device
    mqtt_client.send_command(
        device_id=device_id,
        cmd="fp_enroll"
    )

    return {
        "device_id": device_id,
        "employee_id": body.employee_id,
        "status": "waiting_device_response"
    }

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

    mqtt_client.send_command(
        device_id=device_id,
        cmd="fp_delete",
        params={"finger_id": finger_id}
    )

    fingerprint_service.mark_deleted(fingerprint.id)

    return {
        "device_id": device_id,
        "finger_id": finger_id,
        "status": "delete_command_sent"
    }

@router.post("/{device_id}/door/open")
def open_door(device_id: str):

    if not device_service.exists(device_id):
        raise HTTPException(404, "Device not found")

    mqtt_client.send_command(
        device_id=device_id,
        cmd="door_unlock"
    )

    return {
        "device_id": device_id,
        "status": "door_unlock_sent"
    }

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
    """
    Lấy từ cache (Redis / in-memory).
    KHÔNG query DB.
    """

    status = device_service.get_status(device_id)

    return {
        "device_id": device_id,
        "status": status or "unknown"
    }
