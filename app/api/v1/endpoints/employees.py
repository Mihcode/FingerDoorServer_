from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional  # Import thêm Optional
from datetime import date          # Import thêm date để lọc ngày

from app.database import get_db 
from app.models import models      # Đảm bảo import đúng đường dẫn models của bạn

router = APIRouter()

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