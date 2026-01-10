# app/services/fingerprint_service.py

from typing import List, Optional


# MOCK DATA (sau thay DB)
_fingerprints = []


class FingerprintService:

    def get_by_device(self, device_id: str) -> List[dict]:
        return [
            fp for fp in _fingerprints
            if fp["device_id"] == device_id and not fp.get("deleted")
        ]

    def get_by_device_and_finger(
        self, device_id: str, finger_id: int
    ) -> Optional[dict]:
        for fp in _fingerprints:
            if (
                fp["device_id"] == device_id
                and fp["finger_id"] == finger_id
                and not fp.get("deleted")
            ):
                return fp
        return None

    def add(self, device_id: str, employee_id: int, finger_id: int):
        _fingerprints.append({
            "id": len(_fingerprints) + 1,
            "device_id": device_id,
            "employee_id": employee_id,
            "finger_id": finger_id,
            "deleted": False
        })

    def mark_deleted(self, fp_id: int):
        for fp in _fingerprints:
            if fp["id"] == fp_id:
                fp["deleted"] = True
                return


fingerprint_service = FingerprintService()
