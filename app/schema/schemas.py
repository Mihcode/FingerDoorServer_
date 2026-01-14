from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date

class UserLogin(BaseModel):
    username: str
    password: str

# client sẽ gửi json dạng { "username": "minh", "password": "123456" }

class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    full_name: Optional[str] = None

class SalarySchema(BaseModel):
    position: str
    monthly_salary: float
    bonus_salary: float

class EmployeeSchema(BaseModel):
    id: int
    emp_code: str
    full_name: str
    gender: str
    dob: str
    position: str
    phone_number: str
    email: str
    start_date: str

class ProfileResponse(BaseModel):
    employee: EmployeeSchema
    salary: SalarySchema

class AttendanceResponse(BaseModel):
    id: int
    employee_id: int
    work_date: str
    check_in: str
    check_out: Optional[str]
    total_minutes: int
    ot_minutes: int

# Class dùng cho API Update (Web gửi lên)
class EmployeeUpdate(BaseModel):
    full_name: str
    gender: str
    dob: str          # Web gửi dạng chuỗi "YYYY-MM-DD"
    position: str     # Chức vụ (phải khớp với bảng Salary)
    phone_number: str
    email: str
    
class SalaryStatsResponse(BaseModel):
    emp_code: str
    full_name: str
    month: int
    year: int
    position: str    
    # Các con số thống kê
    valid_work_days: float    # Số ngày công hợp lệ
    ot_days: float            # Số ngày có OT
    # Tiền
    monthly_salary: float     # Lương cứng
    ot_salary_per_day: float  # Lương OT/ngày
    total_income: float       # Tổng thu nhập tính đến hiện tại

# Input tạo nhân viên từ Web
class EmployeeCreate(BaseModel):
    full_name: str
    gender: str
    dob: str          # YYYY-MM-DD
    position: str     # Phải khớp bảng salary
    phone_number: str
    email: EmailStr   # Tự validate định dạng email
    start_date: str   # YYYY-MM-DD
