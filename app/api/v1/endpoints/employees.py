from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional  # Import thêm Optional
from datetime import date, timedelta, datetime        
from sqlalchemy import func, case
from app.database import get_db 
from app.models import models     
from app.core.config import settings
import calendar
from app.models.models import (
    DailyAttendance,
    Employee,
    Salary
)
router = APIRouter()
STANDARD_DAILY_MINUTES = 480
STANDARD_WORKING_DAYS = 22

@router.get("/", response_model=None)
def read_employees(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Lấy danh sách tất cả nhân viên.
    URL: GET /employees/
    """
    employees = db.query(models.Employee).offset(skip).limit(limit).all()
    return employees

@router.get("/daily-attendance")
def read_daily_attendance(
    work_date: Optional[date] = None,   # Cho phép lọc theo ngày (YYYY-MM-DD)
    employee_id: Optional[int] = None,  # Cho phép lọc theo ID nhân viên
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách chấm công hàng ngày.
    URL: GET /employees/daily-attendance
    
    Có thể lọc bằng query params:
    - /employees/daily-attendance?work_date=2023-10-25
    - /employees/daily-attendance?employee_id=5
    """
    # Khởi tạo query từ bảng DailyAttendance
    query = db.query(models.DailyAttendance)

    # Nếu người dùng truyền ngày, thêm điều kiện lọc theo ngày
    if work_date:
        query = query.filter(models.DailyAttendance.work_date == work_date)
    
    # Nếu người dùng truyền employee_id, thêm điều kiện lọc theo nhân viên
    if employee_id:
        query = query.filter(models.DailyAttendance.employee_id == employee_id)

    # Thực hiện lấy dữ liệu với phân trang
    attendance_records = query.offset(skip).limit(limit).all()
    
    return attendance_records

@router.get("/salary")
def preview_payroll(
    year: int,
    month: int,
    db: Session = Depends(get_db)
):
    # ===== Validate =====
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Invalid month")

    start_date = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end_date = date(year, month, last_day)

    # ===== NGƯỠNG TĂNG CA (Standard + 2 giờ) =====
    # 2 giờ = 120 phút
    ot_threshold_minutes = STANDARD_DAILY_MINUTES + 120

    # ===== Query attendance =====
    attendance_subq = (
        db.query(
            DailyAttendance.employee_id.label("employee_id"),
            func.count(DailyAttendance.id).label("working_days"),
            func.sum(DailyAttendance.session_minutes).label("total_minutes"),
            # [LOGIC MỚI]: Đếm số ngày làm việc > (Chuẩn + 2h)
            func.sum(
                case(
                    (DailyAttendance.session_minutes > ot_threshold_minutes, 1),
                    else_=0
                )
            ).label("overtime_days")
        )
        .filter(
            DailyAttendance.work_date >= start_date,
            DailyAttendance.work_date <= end_date
        )
        .group_by(DailyAttendance.employee_id)
        .subquery()
    )

    # ===== Join employee + salary =====
    rows = (
        db.query(
            Employee.id.label("employee_id"),
            Employee.full_name,
            Employee.emp_code,
            Salary.position,
            Salary.monthly_salary,
            Salary.bonus_salary,   # Lúc này đóng vai trò là tiền thưởng/ngày OT
            attendance_subq.c.working_days,
            attendance_subq.c.total_minutes,
            attendance_subq.c.overtime_days
        )
        .join(attendance_subq, Employee.id == attendance_subq.c.employee_id)
        .join(Salary, Employee.position == Salary.position)
        .all()
    )

    result = []

    for r in rows:
        # Xử lý giá trị None nếu có
        working_days = r.working_days or 0
        overtime_days = r.overtime_days or 0
        monthly_salary = float(r.monthly_salary or 0)
        bonus_salary = float(r.bonus_salary or 0)

        # 1. Tính lương cơ bản theo ngày công thực tế
        # Logic: (Lương tháng / Ngày công chuẩn) * Ngày đi làm
        base_salary_month = (monthly_salary / STANDARD_WORKING_DAYS) * working_days

        # 2. [LOGIC MỚI] Tính lương tăng ca
        # Logic: Số ngày OT hợp lệ * Tiền thưởng (bonus_salary)
        overtime_salary = overtime_days * bonus_salary

        total_salary = base_salary_month + overtime_salary

        result.append({
            "employee_id": r.employee_id,
            "emp_code": r.emp_code,
            "full_name": r.full_name,
            "position": r.position,

            "working_days": working_days,
            "total_work_minutes": r.total_minutes,
            
            # Trả về số ngày OT thay vì số phút OT để frontend dễ hiển thị
            "overtime_days": overtime_days, 

            "base_salary_fix": monthly_salary,
            "ot_bonus_per_day": bonus_salary,

            "base_salary_month": round(base_salary_month, 2),
            "overtime_salary": round(overtime_salary, 2),
            "total_salary_estimated": round(total_salary, 2)
        })

    return {
        "year": year,
        "month": month,
        "employees": result
    }

@router.get("/dashboard/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    Thống kê 7 ngày gần nhất (tính cả hôm nay lùi về trước):
    - total_employees: Tổng nhân viên nên đi làm
    - on_time: Đi làm đúng giờ (trước hoặc đúng WORK_START_TIME)
    - late: Đi muộn (sau WORK_START_TIME)
    - absent: Vắng mặt (không có dữ liệu check-in)
    """
    
    # 1. Lấy mốc giờ làm việc từ config (Ví dụ: 09:00:00)
    work_start_time = settings.get_work_start_time()
    
    stats_result = []
    today = date.today()

    # 2. Lặp qua 7 ngày (từ hôm nay lùi về 6 ngày trước)
    for i in range(7):
        current_date = today - timedelta(days=i)
        
        # --- A. Lấy tổng số nhân viên ĐANG hoạt động tính đến ngày current_date ---
        # Logic: Nhân viên phải có start_date <= ngày đang xét mới được tính là "cần đi làm"
        total_employees = db.query(func.count(models.Employee.id))\
            .filter(models.Employee.start_date <= current_date)\
            .scalar()
        
        if total_employees is None:
            total_employees = 0

        # --- B. Lấy danh sách chấm công của ngày đó ---
        daily_records = db.query(models.DailyAttendance)\
            .filter(models.DailyAttendance.work_date == current_date)\
            .all()

        on_time_count = 0
        late_count = 0
        
        # --- C. Phân loại Đi đúng giờ / Đi muộn ---
        for record in daily_records:
            if record.check_in:
                # So sánh thời gian check_in với work_start_time
                if record.check_in <= work_start_time:
                    on_time_count += 1
                else:
                    late_count += 1
        
        # Tổng số người đã đi làm (có check-in)
        present_count = on_time_count + late_count
        
        # --- D. Tính số người vắng ---
        # Vắng = Tổng nhân viên - (Đúng giờ + Đi muộn)
        # Lưu ý: Đảm bảo không âm (trường hợp DB lỗi có nhiều record hơn nhân viên)
        absent_count = max(0, total_employees - present_count)

        # Thêm vào danh sách kết quả
        stats_result.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "total_employees": total_employees,
            "on_time": on_time_count,
            "late": late_count,
            "absent": absent_count,
            "work_start_time": str(work_start_time) # Trả về để Frontend biết mốc so sánh
        })

    # Đảo ngược list để ngày cũ nhất lên đầu (cho biểu đồ vẽ từ trái sang phải: Quá khứ -> Hiện tại)
    # Nếu bạn muốn ngày mới nhất lên đầu thì bỏ dòng này.
    stats_result.reverse() 

    return stats_result