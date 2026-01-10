import json
import time
import logging
import paho.mqtt.client as mqtt
from app.core.config import settings

from app.services.enroll_context import enroll_context
from app.services.fingerprint_service import fingerprint_service
from app.services.device_log_service import device_log_service
from app.services.enroll_context import enroll_context

def handle_fingerprint_event(self, device_id: str, data: dict):

    event = data.get("event")
    finger_id = data.get("finger_id")
    ts = data.get("ts")

    if event == "fp_enroll_done":
        employee_id = enroll_context.pop(device_id)

        if employee_id is None:
            # Trường hợp nguy hiểm: device enroll nhưng backend không biết
            device_log_service.add(
                device_id=device_id,
                event_type="fp_enroll_done",
                finger_id=finger_id,
                success=False,
                message="No enroll context found",
                timestamp=ts
            )
            return

        # ✅ INSERT FINGERPRINT
        fingerprint_service.add(
            device_id=device_id,
            employee_id=employee_id,
            finger_id=finger_id
        )

        # ✅ LOG
        device_log_service.add(
            device_id=device_id,
            event_type="enroll",
            finger_id=finger_id,
            employee_id=employee_id,
            success=True,
            timestamp=ts
        )

        return

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
        """
        {base_topic}/{device_id}/{category}
        """
        parts = topic.split("/")
        if len(parts) < 4:
            raise ValueError(f"Invalid topic: {topic}")

        return parts[2], parts[3]

    @staticmethod
    def parse_payload(payload: bytes):
        raw = payload.decode("utf-8")

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw  # status: "online" | "offline"

    # ---------- HANDLERS ----------

    def handle_door_event(self, device_id: str, data: dict):
        state = data.get("state")
        ts = data.get("ts")

        logger.info(f"[DOOR] {device_id} → {state}")

        # TODO:
        # insert device_logs(event_type="door_state", ...)
        # không ảnh hưởng attendance

    def handle_fingerprint_event(self, device_id: str, data: dict):
        event = data.get("event")
        finger_id = data.get("finger_id")
        success = data.get("success", True)
        ts = data.get("ts")

        logger.info(
            f"[FP] {device_id} | event={event} | finger_id={finger_id}"
        )

        if event == "fp_match" and success:
            # TODO:
            # 1. map finger_id → employee_id
            # 2. xử lý attendance_daily
            # 3. publish open_door nếu hợp lệ
            pass

        # insert device_logs (match / enroll / delete ...)
        elif event == "fp_enroll_done":
            # print("[DEBUG] enroll_context =", enroll_context.dump())

            employee_id = enroll_context.pop(device_id)

            if employee_id is None:
                # Trường hợp nguy hiểm: device enroll nhưng backend không biết
                device_log_service.add(
                    device_id=device_id,
                    event_type="fp_enroll_done",
                    finger_id=finger_id,
                    success=False,
                    message="No enroll context found",
                    timestamp=ts
                )
                return

            # ✅ INSERT FINGERPRINT
            fingerprint_service.add(
                device_id=device_id,
                employee_id=employee_id,
                finger_id=finger_id
            )

            # ✅ LOG
            device_log_service.add(
                device_id=device_id,
                event_type="enroll",
                finger_id=finger_id,
                employee_id=employee_id,
                success=True,
                timestamp=ts
            )
            logger.info(
    f"[FP][ENROLL DONE] device={device_id} employee={employee_id} finger_id={finger_id}"
)
    def handle_status_event(self, device_id: str, data):
        logger.info(f"[STATUS] {device_id} → {data}")

        # data có thể là "online" / "offline"
        # KHÔNG cần ghi DB

    def handle_command_debug(self, device_id: str, data: dict):
        logger.debug(f"[CMD-DEBUG] {device_id} ← {data}")

    # ---------- PUBLIC API ----------

    def connect(self):
        host = settings.MQTT_BROKER.replace(
            "mqtt://", ""
        ).replace(
            "tcp://", ""
        ).strip()

        logger.info(f"[MQTT] Connecting to {host}:{settings.MQTT_PORT}")
        self.client.connect(host, settings.MQTT_PORT, 60)
        self.client.loop_start()

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

    def send_command(self, device_id: str, cmd: str, id: int | None = None):
        topic = f"{settings.MQTT_BASE_TOPIC}/{device_id}/command"

        payload = {"cmd": cmd}

        if id is not None:
            payload["id"] = id

        self.client.publish(topic, json.dumps(payload))
        logger.info(f"[CMD] → {topic} | {payload}")


mqtt_client = MQTTClient()
