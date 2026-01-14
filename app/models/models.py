# mỗi class ánh xạ 1 bảng trong db
import enum
from sqlalchemy import Column, Integer, String, Float, Date, Time, ForeignKey, TIMESTAMP, Numeric, UniqueConstraint, Enum
from sqlalchemy.orm import relationship
from app.database import Base  

# ===== Enum trạng thái cửa =====
class DoorStateEnum(str, enum.Enum):
    LOCKED = "LOCKED"
    WAITING_TO_OPEN = "WAITING_TO_OPEN"
    OPEN = "OPEN"

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
    device_id = Column(String(50), ForeignKey("devices.device_id"), nullable=False)
    finger_id = Column(Integer, nullable=False)
    enrolled_at = Column(TIMESTAMP, server_default="CURRENT_TIMESTAMP")
    updated_at = Column(TIMESTAMP, server_default="CURRENT_TIMESTAMP")

    employee = relationship("Employee")

    device = relationship("Device", back_populates="fingerprints")

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

class Device(Base):
    __tablename__ = "devices"

    # Thông tin cơ bản
    device_id = Column(String(50), primary_key=True)  # VD: "DEV_01"
    name = Column(String(100))                        # VD: "Cửa chính"
    status = Column(String(20), default="offline")    # "online"/"offline"
    last_seen = Column(TIMESTAMP, nullable=True)      # Thời điểm online cuối
    
    door_state = Column(
        Enum(
            DoorStateEnum,
            name="door_state_enum"
        ),
        nullable=False,
        default=DoorStateEnum.LOCKED
    )
    # [QUAN TRỌNG] Dòng này tạo ra thuộc tính "ảo" chứa danh sách vân tay
    # Khi gọi device.fingerprints -> nó sẽ trả về một list [Fingerprint, Fingerprint...]
    fingerprints = relationship("Fingerprint", back_populates="device")