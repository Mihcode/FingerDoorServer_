# app/services/enroll_context.py

_enroll_context = {}


class EnrollContext:
    def __init__(self):
        self._store = {}

    def set(self, device_id: str, employee_id: int):
        self._store[device_id] = employee_id

    def pop(self, device_id: str):
        return self._store.pop(device_id, None)

    def dump(self):
        return dict(self._store)


# 🔥 SINGLE INSTANCE
enroll_context = EnrollContext()



enroll_context = EnrollContext()
