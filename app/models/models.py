# mỗi class ánh xạ 1 bảng trong db

from sqlalchemy import Column, Integer, String, Float, Date, Time, ForeignKey, TIMESTAMP, Numeric, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base  

class Salary(Base):
    __tablename__ = "salary"  
    position = Column(String(50),primary_key=True)
    monthly_salary = Column(Numeric(15, 2), nullable=False)
    bonus_salary = Column(Numeric(15, 2), default=0)

class Employee(Base):
    __tablename__ = "employees"
    id = Column(Integer, primary_key=True)
    emp_code = Column(String(20))
    full_name = Column(String(100))
    gender = Column(String(10))
    dob = Column(Date)
    position = Column(String(50), ForeignKey("salary.position"))
    phone_number = Column(String(20))
    email = Column(String(100))
    start_date = Column(Date)
    created_at = Column(TIMESTAMP, server_default="CURRENT_TIMESTAMP")
    updated_at = Column(TIMESTAMP, server_default="CURRENT_TIMESTAMP")

    salary_info = relationship("Salary")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50))
    password = Column(String(255))
    role = Column(String(20))
    employee_id = Column(Integer, ForeignKey("employees.id"))
    
    employee = relationship("Employee")

class DailyAttendance(Base):
    __tablename__ = "daily_attendance"
    id = Column(Integer, primary_key=True,autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.id"))
    work_date = Column(Date)
    check_in = Column(Time)
    check_out = Column(Time)
    session_minutes = Column(Integer)

class Fingerprint(Base):
    __tablename__ = "fingerprints"
    __table_args__ = (
        UniqueConstraint("device_id", "finger_id", name="uq_device_finger"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    device_id = Column(String(50), nullable=False)
    finger_id = Column(Integer, nullable=False)
    enrolled_at = Column(TIMESTAMP, server_default="CURRENT_TIMESTAMP")
    updated_at = Column(TIMESTAMP, server_default="CURRENT_TIMESTAMP")

    employee = relationship("Employee")

class DeviceLog(Base):
    __tablename__ = "device_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)

    device_id = Column(String(50))          # nếu có nhiều thiết bị
    finger_id = Column(Integer)

    timestamp = Column(TIMESTAMP, nullable=False)
    event_type = Column(String(20))          # match, enroll, delete, error...
    success = Column(Integer)                # 1 = true, 0 = false (hoặc Boolean nếu DB support)
    message = Column(String(255))

    created_at = Column(
        TIMESTAMP,
        server_default="CURRENT_TIMESTAMP"
    )

    employee = relationship("Employee")
