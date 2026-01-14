import json
import time
import logging
from datetime import datetime
import paho.mqtt.client as mqtt
from app.core.config import settings

# Import services
from app.services.enroll_context import enroll_context
from app.services.fingerprint_service import fingerprint_service
from app.services.device_log_service import device_log_service  # <--- Sử dụng service này
from app.services.device_service import device_service

logger = logging.getLogger("mqtt")
logging.basicConfig(level=logging.INFO)

class MQTTClient:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

        if settings.MQTT_USERNAME and settings.MQTT_PASSWORD:
            self.client.username_pw_set(
                settings.MQTT_USERNAME,
                settings.MQTT_PASSWORD
            )

        # Map category → handler
        self.handlers = {
            "door": self.handle_door_event,
            "fingerprint": self.handle_fingerprint_event,
            "status": self.handle_status_event,
            "command": self.handle_command_debug,
        }

    # ---------- MQTT CALLBACKS ----------

    def _on_connect(self, client, userdata, flags, rc):
        if rc != 0:
            logger.error(f"[MQTT] Connection failed (rc={rc})")
            return

        topic = f"{settings.MQTT_BASE_TOPIC}/#"
        client.subscribe(topic)
        logger.info(f"[MQTT] Connected & subscribed: {topic}")

    def _on_message(self, client, userdata, msg):
        try:
            device_id, category = self.parse_topic(msg.topic)
            payload = self.parse_payload(msg.payload)

            handler = self.handlers.get(category)
            if not handler:
                logger.warning(f"[MQTT] Unknown category: {category}")
                return

            handler(device_id, payload)

        except Exception as e:
            logger.exception(f"[MQTT] Message error: {e}")

    # ---------- PARSER ----------

    @staticmethod
    def parse_topic(topic: str):
        parts = topic.split("/")

        # Expect: base/device_id/category
        if len(parts) < 3:
            raise ValueError(f"Invalid topic format: {topic}")

        return parts[-2], parts[-1]


    @staticmethod
    def parse_payload(payload: bytes):
        raw = payload.decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw 

    # ---------- HANDLERS ----------

    def handle_door_event(self, device_id: str, data: dict):
        # Topic: base/device_id/door
        # Payload mẫu: {"state":"locked", "event":"door_state", ...}
        
        state = data.get("state") # "locked", "open"
        ts = data.get("ts")

        logger.info(f"[DOOR] {device_id} → {state}")

        # [UPDATE] Lưu trạng thái cửa vào DB (update cột door_state trong bảng devices)
        if state:
            device_service.update_door_state(device_id, state)

        # [GIỮ NGUYÊN] Ghi log lịch sử (DeviceLog)
        device_log_service.add(
            device_id=device_id,
            event_type="door_event",
            success=True,
            message=f"Door state changed to: {state}",
            timestamp=ts
        )

    def handle_fingerprint_event(self, device_id: str, data: dict):
        event = data.get("event")
        
        device_finger_id = data.get("finger_id") 
        
        success = data.get("success", True)
        ts = data.get("ts")
        
        # Lấy message (ưu tiên payload cho lỗi, msg cho thông báo thường)
        message = data.get("payload") or data.get("msg", "")

        logger.info(
            f"[FP] {device_id} | event={event} | finger_id={device_finger_id}"
        )

        # ---------------------------------------------------------
        # CASE 1: Chấm công / Quẹt vân tay (Match)
        # ---------------------------------------------------------
        if event == "fp_match":
            if success:
                # TODO: Logic chấm công
                pass
            
            # Ghi log (dùng device_finger_id vì lúc match device luôn gửi ID lên)
            device_log_service.add(
                device_id=device_id,
                event_type="fp_match",
                finger_id=device_finger_id,
                success=success,
                message=message or ("Finger matched" if success else "Match failed"),
                timestamp=ts
            )

        # ---------------------------------------------------------
        # CASE 2 & 2.5: Xử lý phản hồi Enroll (Done hoặc Fail)
        # ---------------------------------------------------------
        elif event in ["fp_enroll_done", "fp_enroll_fail"]:
            # 1. Lấy context đã lưu từ Server (để biết ngón nào đang được chờ đăng ký)
            ctx = enroll_context.pop(device_id)

            # Nếu không tìm thấy context (có thể do server restart hoặc timeout)
            if not ctx:
                device_log_service.add(
                    device_id=device_id,
                    event_type="enroll_resp",
                    finger_id=device_finger_id, 
                    success=False,
                    message=f"Context missing. Device sent {event} but server wasn't waiting.",
                    timestamp=ts
                )
                return

            # 2. Giải nén dữ liệu từ Context
            saved_employee_id = ctx.get("employee_id")
            saved_finger_id = ctx.get("finger_id") 
            
            # [LOGIC QUAN TRỌNG]:
            # Nếu device gửi finger_id lên thì dùng, nếu gửi None (do lỗi) thì lấy từ Context
            final_finger_id = device_finger_id if device_finger_id is not None else saved_finger_id

            # Xử lý Logic
            if event == "fp_enroll_done" and success:
                # Thành công -> Lưu vân tay vào bảng fingerprints
                fingerprint_service.add(
                    device_id=device_id,
                    employee_id=saved_employee_id,
                    finger_id=final_finger_id
                )
                msg_log = "Enrollment successful"
                log_success = True
            else:
                # Thất bại
                msg_log = f"Enrollment failed: {message}"
                log_success = False

            # Ghi Log vào DB (để API Polling đọc được kết quả)
            device_log_service.add(
                device_id=device_id,
                event_type="enroll_resp",
                finger_id=final_finger_id,  # <--- Đảm bảo ID này luôn có giá trị
                employee_id=saved_employee_id,
                success=log_success,
                message=msg_log,
                timestamp=ts
            )
            
            logger.info(f"[FP][ENROLL] {device_id} success={log_success} msg={msg_log} id={final_finger_id}")

        # ---------------------------------------------------------
        # CASE 3: Kết quả xóa (Delete Done)
        # ---------------------------------------------------------
        elif event == "fp_delete_done":
            device_log_service.add(
                device_id=device_id,
                event_type="delete_resp",
                finger_id=device_finger_id,
                success=success,
                message=message or "Fingerprint deleted on device",
                timestamp=ts
            )

        # ---------------------------------------------------------
        # CASE 4: Các lỗi khác (Error)
        # ---------------------------------------------------------
        elif event == "error":
             device_log_service.add(
                device_id=device_id,
                event_type="device_error",
                finger_id=device_finger_id,
                success=False,
                message=message,
                timestamp=ts
            )
    def handle_status_event(self, device_id: str, data):
        # Topic: base/device_id/status
        # Payload mẫu: {"status":"online", "ts":"...", "event":"device_status"}
        
        # Lấy status, nếu data là dict thì lấy key 'status', nếu string thì dùng luôn
        if isinstance(data, dict):
            status_val = data.get("status", "unknown")
        else:
            status_val = str(data)

        logger.info(f"[STATUS] {device_id} → {status_val}")

        # [UPDATE] Nếu thiết bị báo online -> Cập nhật heartbeat vào DB
        if status_val == "online":
            device_service.update_heartbeat(device_id)

    def handle_command_debug(self, device_id: str, data: dict):
        logger.debug(f"[CMD-DEBUG] {device_id} ← {data}")

    # ---------- PUBLIC API ----------

    def connect(self):
        host = settings.MQTT_BROKER.replace("mqtt://", "").replace("tcp://", "").strip()
        logger.info(f"[MQTT] Connecting to {host}:{settings.MQTT_PORT}")
        self.client.connect(host, settings.MQTT_PORT, 60)
        self.client.loop_start()

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

    def send_command(self, device_id: str, cmd: str, finger_id: int | None = None):
        topic = f"{settings.MQTT_BASE_TOPIC}/{device_id}/command"
        payload = {"cmd": cmd}
        if finger_id is not None:
            payload["id"] = finger_id
        
        self.client.publish(topic, json.dumps(payload))
        logger.info(f"[CMD] → {topic} | {payload}")

mqtt_client = MQTTClient()