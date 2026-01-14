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
from app.services.daily_attendance_service import daily_attendance_service 
from app.services.fingerprint_service import fingerprint_service # Cần để tìm employee_id

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
        ts_str = data.get("ts") 
        
        message = data.get("payload") or data.get("msg", "")

        # [SỬA ĐOẠN NÀY]: Xử lý thời gian "cứng"
        ts_obj = datetime.now() # Fallback nếu lỗi
        
        if ts_str:
            try:
                # 1. Cắt bỏ chữ 'Z' để Python không hiểu nhầm là UTC
                # Input: "2026-01-14T08:09:52Z" -> "2026-01-14T08:09:52"
                clean_ts = ts_str.replace("Z", "")
                
                # 2. Parse chuỗi ISO thuần
                ts_obj = datetime.fromisoformat(clean_ts)
                
                # ts_obj lúc này là: 2026-01-14 08:09:52 (Naive - không múi giờ)
            except ValueError:
                ts_obj = datetime.now()

        logger.info(
            f"[FP] {device_id} | event={event} | finger_id={device_finger_id}"
        )

        # ---------------------------------------------------------
        # CASE 1: Chấm công / Quẹt vân tay (Match)
        # ---------------------------------------------------------
        if event == "fp_match":
            employee_found = None

            if success and device_finger_id is not None:
                # Tìm Employee ID
                fp_record = fingerprint_service.get_by_device_and_finger(
                    device_id=device_id, 
                    finger_id=device_finger_id
                )

                if fp_record:
                    employee_found = fp_record.employee_id
                    
                    # Gọi Service chấm công
                    # Lưu ý: Truyền ts_obj (đã là giờ VN chuẩn) vào
                    action = daily_attendance_service.process_attendance(
                        employee_id=employee_found,
                        timestamp_vn=ts_obj 
                    )
                    logger.info(f"[ATTENDANCE] Emp {employee_found} -> {action}")
                else:
                    logger.warning(f"[ATTENDANCE] Unknown finger {device_finger_id} on {device_id}")

            # Ghi log thiết bị
            device_log_service.add(
                device_id=device_id,
                event_type="fp_match",
                finger_id=device_finger_id,
                employee_id=employee_found,
                success=success,
                message=message or ("Finger matched" if success else "Match failed"),
                timestamp=ts_obj
            )

        # ---------------------------------------------------------
        # CASE 2 & 2.5: Xử lý phản hồi Enroll (Done hoặc Fail)
        # ---------------------------------------------------------
        elif event in ["fp_enroll_success", "fp_enroll_fail"]:
            # 1. Lấy context để biết ai (employee_id) đang đăng ký
            ctx = enroll_context.pop(device_id)

            if not ctx:
                logger.warning(f"[ENROLL] Context missing for {device_id}. Event ignored.")
                device_log_service.add(
                    device_id=device_id,
                    event_type="enroll_resp",
                    finger_id=device_finger_id if device_finger_id is not None else 0, 
                    success=False,
                    message=f"Context missing (Timeout?). Device sent {event}.",
                    timestamp=ts_obj
                )
                return

            saved_employee_id = ctx.get("employee_id")
            saved_finger_id = ctx.get("finger_id") 
            
            # 2. Xác định ID cuối cùng: Ưu tiên lấy từ Device trả về, nếu không thì lấy từ Context lúc gửi lệnh
            final_finger_id = device_finger_id if device_finger_id is not None else saved_finger_id

            msg_log = ""
            log_success = False

            # 3. Logic Lưu DB (Chỉ thực hiện khi Device báo thành công)
            if event == "fp_enroll_success" and success:
                # Kiểm tra ràng buộc dữ liệu quan trọng
                if final_finger_id is not None and saved_employee_id is not None:
                    try:
                        logger.info(f"[ENROLL] Saving to DB: Dev={device_id}, Emp={saved_employee_id}, Finger={final_finger_id}")
                        
                        # [FIX] Ép kiểu int để đảm bảo an toàn khi lưu vào DB
                        fingerprint_service.add(
                            device_id=device_id,
                            employee_id=int(saved_employee_id),
                            finger_id=int(final_finger_id)
                        )
                        
                        msg_log = f"Enrollment successful. Assigned Finger ID: {final_finger_id}"
                        log_success = True
                        
                    except Exception as e:
                        # Lỗi này thường do trùng lặp ID (Unique Constraint) hoặc lỗi kết nối DB
                        logger.error(f"[ENROLL] DB Error: {str(e)}")
                        msg_log = f"Device enrolled OK but DB Save Failed: {str(e)}"
                        log_success = False 
                else:
                    # Trường hợp hiếm: Device báo thành công nhưng không có ID
                    msg_log = "Enrollment successful on device but ID is missing/invalid."
                    log_success = False
            else:
                # Trường hợp Device báo thất bại
                msg_log = f"Enrollment failed on device: {message}"
                log_success = False

            # 4. Ghi Log kết quả cuối cùng vào bảng device_logs
            device_log_service.add(
                device_id=device_id,
                event_type="enroll_resp",
                # Nếu final_finger_id là None (trường hợp lỗi nặng), để tạm là 0 hoặc null tuỳ DB
                finger_id=final_finger_id if final_finger_id is not None else 0,
                employee_id=saved_employee_id,
                success=log_success,
                message=msg_log,
                timestamp=ts_obj
            )
            
            logger.info(f"[FP][ENROLL] {device_id} | Success={log_success} | Msg={msg_log}")

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
                timestamp=ts_obj
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
                timestamp=ts_obj
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