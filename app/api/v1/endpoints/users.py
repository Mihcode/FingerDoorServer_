
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import extract
from app.database import get_db
import app.models.models as models, app.schema.schemas as schemas

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
    emp_id = employee.emp_code

    try:
        # 2. Xóa Tài khoản User 
        db.query(models.User).filter(models.User.employee_id == emp_id).delete()

        # 3. Xóa Vân tay (Fingerprints)
        db.query(models.Fingerprint).filter(models.Fingerprint.employee_id == emp_id).delete()

        # 4. Xóa Lịch sử chấm công (DailyAttendance)
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


# =======================================================
# 2. API CẬP NHẬT THÔNG TIN NHÂN VIÊN
# =======================================================
from datetime import datetime # Nhớ import datetime để convert ngày tháng

@router.put("/employees/{emp_code}")
def update_employee(emp_code: str, emp_in: schemas.EmployeeUpdate, db: Session = Depends(get_db)):
    """
    Nhận emp_code và thông tin mới -> Cập nhật vào DB
    """
    # 1. Tìm nhân viên cần sửa
    employee = db.query(models.Employee).filter(models.Employee.emp_code == emp_code).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy nhân viên có mã {emp_code}")

    try:
        # 2. Cập nhật từng trường
        employee.full_name = emp_in.full_name
        employee.gender = emp_in.gender
        employee.position = emp_in.position
        employee.phone_number = emp_in.phone_number
        employee.email = emp_in.email
        
        # Xử lý ngày tháng (Convert từ String sang Date object)
        # Giả sử Web gửi "2003-01-01"
        if emp_in.dob:
            employee.dob = datetime.strptime(emp_in.dob, "%Y-%m-%d").date()
        if emp_in.start_date:
            employee.start_date = datetime.strptime(emp_in.start_date, "%Y-%m-%d").date()
        
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
