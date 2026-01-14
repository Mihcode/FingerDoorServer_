
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import extract
from app.database import get_db
import app.models.models as models, app.schema.schemas as schemas
from datetime import datetime, time, date
import calendar 


router = APIRouter()

# Login
@router.post("/login", response_model=schemas.UserResponse)
def login(user_in: schemas.UserLogin, db: Session = Depends(get_db)):
	user = db.query(models.User).filter(
		models.User.username == user_in.username,
		models.User.password == user_in.password
	).first()

	if not user:
		raise HTTPException(status_code=401, detail="Invalid username or password")
    
	return {
		"id": user.id,
		"username": user.username,
		"role": user.role,
		"full_name": user.employee.full_name if user.employee else "Unknown"
	}

# Profile nhân viên
@router.get("/profile/{user_id}", response_model=schemas.ProfileResponse)
def get_profile(user_id: int, db: Session = Depends(get_db)):
	user = db.query(models.User).filter(models.User.id == user_id).first()
	if not user:
		raise HTTPException(status_code=404, detail="User not found")
	employee = user.employee
	if not employee:
		 raise HTTPException(status_code=404, detail="User này chưa liên kết hồ sơ nhân viên")
	
	emp_dict = {
		"id": employee.id,
		"emp_code": employee.emp_code,
		"full_name": employee.full_name,
		"gender": employee.gender,
		"dob": str(employee.dob),
		"position": employee.position,
		"phone_number": employee.phone_number,
		"email": employee.email,
		"start_date": str(employee.start_date)
	}
	salary_dict = {
		"position": employee.salary_info.position,
		"monthly_salary": employee.salary_info.monthly_salary,
		"bonus_salary": employee.salary_info.bonus_salary
	}
	return {
		"employee": emp_dict,
		"salary": salary_dict
	}

# Lịch sử chấm công
@router.get("/history", response_model=list[schemas.AttendanceResponse])
def get_history(user_id: int, month: int, year: int, db: Session = Depends(get_db)):
	user = db.query(models.User).filter(models.User.id == user_id).first()
	if not user or not user.employee_id:
		return []
	emp_id = user.employee_id
	records = db.query(models.DailyAttendance).filter(
		models.DailyAttendance.employee_id == emp_id,
		extract('month', models.DailyAttendance.work_date) == month,
		extract('year', models.DailyAttendance.work_date) == year
	).order_by(models.DailyAttendance.work_date.desc()).all()
	history_list = []
	for row in records:
		date_id = int(row.work_date.strftime("%Y%m%d"))
		ot_min = 0
		if row.check_out:
			out_minutes = row.check_out.hour * 60 + row.check_out.minute
			standard_end = 17 * 60
			if out_minutes > standard_end:
				ot_min = out_minutes - standard_end
		history_list.append({
			"id": date_id,
			"employee_id": emp_id,
			"work_date": str(row.work_date),
			"check_in": str(row.check_in) if row.check_in else None,
			"check_out": str(row.check_out) if row.check_out else None,
			"total_minutes": row.session_minutes or 0,
			"ot_minutes": ot_min
		})
	return history_list

# API xóa nhân viên
@router.delete("/employees/{emp_code}")
def delete_employee(emp_code: str, db: Session = Depends(get_db)):
    # Tìm nhân viên
    employee = db.query(models.Employee).filter(models.Employee.emp_code == emp_code).first()
    if not employee:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy nhân viên có mã {emp_code}")
    emp_id = employee.id

    try:
        # 2. Xóa Tài khoản User 
        db.query(models.User).filter(models.User.employee_id == emp_id).delete()

        # 3. Xóa Vân tay (Fingerprints)
        db.query(models.Fingerprint).filter(models.Fingerprint.employee_id == emp_id).delete()

        # 4. Xóa Lịch sử chấm công (DailyAttendance) // Hưng bảo trả lương rồi mới xóa?
        db.query(models.DailyAttendance).filter(models.DailyAttendance.employee_id == emp_id).delete()

        # 5. Xóa Log thiết bị (DeviceLog)
        db.query(models.DeviceLog).filter(models.DeviceLog.employee_id == emp_id).delete()

        # 6. Cuối cùng: Xóa Hồ sơ nhân viên (Employee)
        db.delete(employee)

        db.commit()
        
        return {
            "status": "success",
            "message": f"Đã xóa vĩnh viễn nhân viên {employee.full_name} ({emp_code}) và toàn bộ dữ liệu liên quan."
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi xóa dữ liệu: {str(e)}")


# API CẬP NHẬT THÔNG TIN NHÂN VIÊN
@router.put("/employees/{emp_code}")
def update_employee(emp_code: str, emp_in: schemas.EmployeeUpdate, db: Session = Depends(get_db)):
    # 1. Tìm nhân viên cần sửa
    employee = db.query(models.Employee).filter(models.Employee.emp_code == emp_code).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy nhân viên có mã {emp_code}")

    try:
        #  Cập nhật từng trường
        employee.full_name = emp_in.full_name
        employee.gender = emp_in.gender
        employee.position = emp_in.position
        employee.phone_number = emp_in.phone_number
        employee.email = emp_in.email
        
        # Xử lý ngày tháng (Convert từ String sang Date object)
        # Giả sử Web gửi "2003-01-01"
        if emp_in.dob:
            employee.dob = datetime.strptime(emp_in.dob, "%Y-%m-%d").date()
        
        # Lưu vào DB
        db.commit()
        db.refresh(employee) # Lấy lại dữ liệu mới nhất

        return {
            "status": "success",
            "message": f"Cập nhật thành công cho nhân viên {emp_code}",
            "data": {
                "emp_code": employee.emp_code,
                "full_name": employee.full_name,
                "position": employee.position
            }
        }

    except Exception as e:
        db.rollback()
        # Lỗi thường gặp: Position không tồn tại trong bảng Salary
        raise HTTPException(status_code=400, detail=f"Lỗi cập nhật (Kiểm tra lại chức vụ có đúng không): {str(e)}")

# Tính thu nhập
@router.get("/salary-stats", response_model=schemas.SalaryStatsResponse)
def get_salary_stats(
    user_id: int, 
    month: int, 
    year: int, 
    db: Session = Depends(get_db)
):
    # 1. Lấy thông tin Nhân viên & Bảng lương
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user or not user.employee:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ nhân viên")
    
    employee = user.employee
    salary_info = employee.salary_info

    if not salary_info:
        raise HTTPException(status_code=400, detail="Nhân viên chưa được xếp hạng lương")

    # 2. Lấy dữ liệu chấm công trong tháng
    records = db.query(models.DailyAttendance).filter(
        models.DailyAttendance.employee_id == employee.id,
        extract('month', models.DailyAttendance.work_date) == month,
        extract('year', models.DailyAttendance.work_date) == year
    ).all()

    # 3. XỬ LÝ LOGIC NGHIÊM NGẶT 
    
    # Cấu hình giờ giấc (Hardcode theo quy định công ty)
    TIME_DEADLINE_IN = time(9, 0, 0)    # 09:00:00
    TIME_DEADLINE_OUT = time(17, 0, 0)  # 17:00:00
    TIME_OT_START = time(19, 0, 0)      # 19:00:00 (Sau 19h mới tính OT)
    STANDARD_WORK_DAYS_IN_MONTH = 22    # Quy ước chia lương tháng

    valid_work_days = 0
    ot_days = 0

    for row in records:
        # Nếu thiếu check-in hoặc check-out thì coi như bỏ, không tính gì cả
        if not row.check_in or not row.check_out:
            continue

        # Lấy thứ trong tuần (0=Thứ 2, ..., 5=Thứ 7, 6=Chủ nhật)
        weekday = row.work_date.weekday()

        # TÍNH NGÀY CÔNG CHUẨN
        # Điều kiện: 
        # 1. Không phải T7, CN (weekday < 5)
        # 2. Check-in <= 09:00
        # 3. Check-out >= 17:00
        if weekday < 5: 
            if row.check_in <= TIME_DEADLINE_IN and row.check_out >= TIME_DEADLINE_OUT:
                valid_work_days += 1
            else:
                # Log debug 
                print(f"Ngày {row.work_date}: Mất công (Vào {row.check_in}, Ra {row.check_out})")

        # TÍNH OT (Độc lập với ngày công) 
        # Điều kiện: Check-out >= 19:00
        # (Kể cả T7, CN hay đi muộn, miễn về sau 19h là tính OT)
        if row.check_out >= TIME_OT_START and row.check_in <= TIME_DEADLINE_OUT:
            ot_days += 1

    # 4. TÍNH TIỀN
    monthly_salary_base = float(salary_info.monthly_salary)
    ot_salary_unit = float(salary_info.bonus_salary)
    
    # Lương 1 ngày công chuẩn
    daily_salary_unit = monthly_salary_base / STANDARD_WORK_DAYS_IN_MONTH

    # Tổng thu nhập = (Ngày công * Lương ngày) + (Ngày OT * Lương OT)
    total_income = (valid_work_days * daily_salary_unit) + (ot_days * ot_salary_unit)

    return {
        "emp_code": employee.emp_code,
        "full_name": employee.full_name,
        "month": month,
        "year": year,
		"position": employee.position, 
        "valid_work_days": valid_work_days,
        "ot_days": ot_days,
        "month_salary": monthly_salary_base,
        "ot_salary_per_day": ot_salary_unit,
        "total_income": round(total_income, 0) # Làm tròn số tiền
    }
