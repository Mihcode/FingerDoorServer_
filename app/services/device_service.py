# app/services/device_service.py

# TẠM THỜI hardcode / in-memory

_device_cache = set()
_device_status = {}


class DeviceService:

    def exists(self, device_id: str) -> bool:
        # TẠM: cho phép mọi device
        return True

    def set_status(self, device_id: str, status: str):
        _device_status[device_id] = status
        _device_cache.add(device_id)

    def get_status(self, device_id: str) -> str | None:
        return _device_status.get(device_id)


device_service = DeviceService()
