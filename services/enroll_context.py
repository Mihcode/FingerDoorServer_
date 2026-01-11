class EnrollContext:
    def __init__(self):
        self._store = {}

    def set(self, device_id: str, employee_id: int):
        # Lưu: Máy device_01 đang chờ thêm vân tay cho nhân viên ID 5
        self._store[device_id] = employee_id

    def pop(self, device_id: str):
        # Lấy ra xong xóa luôn
        return self._store.pop(device_id, None)

enroll_context = EnrollContext()
