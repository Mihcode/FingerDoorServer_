# app/services/fingerprint_service.py

from typing import Optional
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.models import Fingerprint, Employee


class FingerprintService:

    def get_db(self) -> Session:
        return SessionLocal()

    def get_by_device(
        self,
        device_id: str,
        employee_id: int | None = None
    ):
        with self.get_db() as db:
            query = (
                db.query(Fingerprint, Employee.emp_code)
                .join(Employee, Fingerprint.employee_id == Employee.id)
                .filter(Fingerprint.device_id == device_id)
            )

            if employee_id is not None:
                query = query.filter(Fingerprint.employee_id == employee_id)

            results = query.all()

            return [
                {
                    "id": fp.id,               # <--- THÊM DÒNG NÀY (Primary Key của bảng fingerprints)
                    "finger_id": fp.finger_id,
                    "device_id": fp.device_id,
                    "employee_id": fp.employee_id,
                    "emp_code": emp_code,
                    "enrolled_at": fp.enrolled_at
                }
                for fp, emp_code in results
            ]

    def get_by_device_and_finger(
        self,
        device_id: str,
        finger_id: int
    ) -> Optional[Fingerprint]:
        with self.get_db() as db:
            return db.query(Fingerprint).filter(
                Fingerprint.device_id == device_id,
                Fingerprint.finger_id == finger_id
            ).first()

    def add(self, device_id: str, employee_id: int, finger_id: int):
        with self.get_db() as db:
            new_fp = Fingerprint(
                device_id=device_id,
                employee_id=employee_id,
                finger_id=finger_id
            )
            db.add(new_fp)
            db.commit()
            db.refresh(new_fp)
            return new_fp

    def mark_deleted(self, fp_id: int):
        with self.get_db() as db:
            fp = db.query(Fingerprint).filter(Fingerprint.id == fp_id).first()
            if fp:
                db.delete(fp)
                db.commit()

    def get_next_available_id(self, device_id: str) -> Optional[int]:
        MAX_FINGERS = 128

        with self.get_db() as db:
            used_ids = {
                row[0]
                for row in db.query(Fingerprint.finger_id)
                .filter(Fingerprint.device_id == device_id)
                .all()
            }

            for candidate in range(MAX_FINGERS):
                if candidate not in used_ids:
                    return candidate

            return None


fingerprint_service = FingerprintService()
