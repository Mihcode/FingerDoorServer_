# app/services/daily_attendance_service.py
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models.models import DailyAttendance

class DailyAttendanceService:
    def get_db(self):
        return SessionLocal()

    def process_attendance(self, employee_id: int, timestamp_vn: datetime):
        """
        Xử lý logic chấm công:
        - Input: timestamp_vn (Giờ VN chuẩn, không cần cộng trừ nữa)
        """
        
        # [QUAN TRỌNG]: Bỏ đoạn code + timedelta(hours=7) đi
        # Dùng trực tiếp thời gian nhận được
        vn_time = timestamp_vn 
        
        work_date = vn_time.date()
        current_time = vn_time.time()

        with self.get_db() as session:
            # Tìm bản ghi chấm công của nhân viên trong ngày hôm nay
            attendance = session.query(DailyAttendance).filter(
                DailyAttendance.employee_id == employee_id,
                DailyAttendance.work_date == work_date
            ).first()

            if not attendance:
                # [CASE 1] Check-in
                new_att = DailyAttendance(
                    employee_id=employee_id,
                    work_date=work_date,
                    check_in=current_time,
                    check_out=current_time,
                    session_minutes=0
                )
                session.add(new_att)
                session.commit()
                return "check_in"
            else:
                # [CASE 2] Update Check-out
                attendance.check_out = current_time
                
                # Tính toán số phút
                dt_in = datetime.combine(work_date, attendance.check_in)
                dt_out = datetime.combine(work_date, current_time)
                
                duration = dt_out - dt_in
                total_minutes = int(duration.total_seconds() / 60)
                
                attendance.session_minutes = total_minutes
                
                session.commit()
                return "update_check_out"

daily_attendance_service = DailyAttendanceService()