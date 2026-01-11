from app.database import SessionLocal # Sửa import cho khớp cấu trúc
from app.models import models 

class FingerprintService:
    def add(self, device_id: str, employee_id: int, finger_id: int):
        db = SessionLocal()
        try:
            existing = db.query(models.Fingerprint).filter(
                models.Fingerprint.finger_id_on_sensor == finger_id
            ).first()
            if existing:
                existing.employee_id = employee_id
            else:
                new_fp = models.Fingerprint(employee_id=employee_id, finger_id_on_sensor=finger_id)
                db.add(new_fp)
            db.commit()
        except Exception as e:
            print(f"❌ Error: {e}")
            db.rollback()
        finally:
            db.close()

fingerprint_service = FingerprintService()
