from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional  # Import thêm Optional
from datetime import date          # Import thêm date để lọc ngày
from sqlalchemy import func, case
from app.database import get_db 
from app.models import models      # Đảm bảo import đúng đường dẫn models của bạn
import calendar
from app.models.models import (
    DailyAttendance,
    Employee,
    Salary
)
router = APIRouter()
STANDARD_DAILY_MINUTES = 480
STANDARD_WORKING_DAYS = 30

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

    # ===== Query attendance =====
    attendance_subq = (
        db.query(
            DailyAttendance.employee_id.label("employee_id"),
            func.count(DailyAttendance.id).label("working_days"),
            func.sum(DailyAttendance.session_minutes).label("total_minutes"),
            func.sum(
                case(
                    (DailyAttendance.session_minutes > STANDARD_DAILY_MINUTES,
                     DailyAttendance.session_minutes - STANDARD_DAILY_MINUTES),
                    else_=0
                )
            ).label("overtime_minutes")
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
            Salary.bonus_salary,   # tiền OT / giờ
            attendance_subq.c.working_days,
            attendance_subq.c.total_minutes,
            attendance_subq.c.overtime_minutes
        )
        .join(attendance_subq, Employee.id == attendance_subq.c.employee_id)
        .join(Salary, Employee.position == Salary.position)
        .all()
    )

    result = []

    for r in rows:
        # ===== Tính toán =====
        base_salary_month = (
            float(r.monthly_salary) * r.working_days / STANDARD_WORKING_DAYS
        )

        overtime_hours = r.overtime_minutes / 60
        overtime_salary = overtime_hours * float(r.bonus_salary)

        total_salary = base_salary_month + overtime_salary

        result.append({
            "employee_id": r.employee_id,
            "emp_code": r.emp_code,
            "full_name": r.full_name,
            "position": r.position,

            "working_days": r.working_days,
            "total_work_minutes": r.total_minutes,
            "overtime_minutes": r.overtime_minutes,

            "base_salary": float(r.monthly_salary),
            "overtime_rate_per_hour": float(r.bonus_salary),

            "base_salary_month": round(base_salary_month, 2),
            "overtime_salary": round(overtime_salary, 2),
            "total_salary_estimated": round(total_salary, 2)
        })

    return {
        "year": year,
        "month": month,
        "employees": result
    }