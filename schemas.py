from pydantic import BaseModel
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
    work_date: str
    check_in: str
    check_out: Optional[str]
    total_minutes: int
    ot_minutes: int