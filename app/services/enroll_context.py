# app/services/enroll_context.py

_enroll_context = {}


class EnrollContext:
    def __init__(self):
        self.device_id: str | None = None
        self.employee_id: str | None = None
        self.finger_id: int | None = None

    def set(self, device_id: str, employee_id: str, finger_id: int):
        self.device_id = device_id
        self.employee_id = employee_id
        self.finger_id = finger_id

    def clear(self):
        self.device_id = None
        self.employee_id = None
        self.finger_id = None

    def dump(self):
        return {
            "device_id": self.device_id,
            "employee_id": self.employee_id,
            "finger_id": self.finger_id,
        }



# 🔥 SINGLE INSTANCE
enroll_context = EnrollContext()



enroll_context = EnrollContext()
