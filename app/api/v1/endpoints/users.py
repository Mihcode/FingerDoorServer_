
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import extract
from app.database import get_db
import app.models.models as models, app.schema.schemas as schemas
import random
import string
import unidecode  # Cần pip install unidecode để bỏ dấu tiếng Việt
from fastapi import BackgroundTasks # Để gửi email ngầm không treo web
from app.core.security import get_password_hash
from app.utils.email_utils import send_account_email

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
        "monthly_salary": monthly_salary_base,
        "ot_salary_per_day": ot_salary_unit,
        "total_income": round(total_income, 0) # Làm tròn số tiền
    }
	# Thêm nhân viên - đăng ký
# Tạo Username từ tên (Nguyen Van Minh -> minhnv)
def generate_base_username(full_name: str) -> str:
    # Bỏ dấu tiếng Việt (Nguyễn Văn Minh -> Nguyen Van Minh)
    text = unidecode.unidecode(full_name).lower()
    parts = text.split()
    if not parts:
        return "user"
    
    # Logic: Tên + Chữ cái đầu Họ + Chữ cái đầu Đệm
    # Ví dụ: parts = ['nguyen', 'van', 'minh']
    # last_name = 'minh'
    # initials = 'n' + 'v' => 'nv'
    # result = 'minhnv'
    last_name = parts[-1]
    initials = "".join([p[0] for p in parts[:-1]])
    return f"{last_name}{initials}"
# Hàm phụ trợ: Tạo mật khẩu ngẫu nhiên 8 ký tự
def generate_temp_password(length=8):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

# API
@router.post("/employees/create", status_code=201)
def create_new_employee(
    emp_in: schemas.EmployeeCreate, 
    background_tasks: BackgroundTasks, # Dùng cái này để gửi mail chạy ngầm
    db: Session = Depends(get_db)
):
    # 1. Kiểm tra Email đã tồn tại chưa
    if db.query(models.Employee).filter(models.Employee.email == emp_in.email).first():
        raise HTTPException(status_code=400, detail="Email này đã được sử dụng!")

    try:
        # 2. Tạo bản ghi Employee
        new_emp = models.Employee(
            emp_code="TEMP", # Tạm thời để TEMP, tí update ID vào hoặc logic sinh mã riêng
            full_name=emp_in.full_name,
            gender=emp_in.gender,
            dob=datetime.strptime(emp_in.dob, "%Y-%m-%d").date(),
            position=emp_in.position,
            phone_number=emp_in.phone_number,
            email=emp_in.email,
            start_date=datetime.strptime(emp_in.start_date, "%Y-%m-%d").date()
        )
        db.add(new_emp)
        db.flush() # Flush để lấy new_emp.id ngay lập tức (chưa commit hẳn)

        # Update lại Mã nhân viên cho đẹp (VD: NV + ID: NV005)
        new_emp.emp_code = f"NV{new_emp.id:03d}" # NV001, NV002...
        
        # 3. Tạo Username tự động & Kiểm tra trùng
        base_username = generate_base_username(emp_in.full_name)
        final_username = base_username
        counter = 1
        
        while db.query(models.User).filter(models.User.username == final_username).first():
            final_username = f"{base_username}{counter}"
            counter += 1
        
        # 4. Tạo Mật khẩu ngẫu nhiên
        temp_password = generate_temp_password()
        hashed_password = get_password_hash(temp_password)

        # 5. Tạo User (Tài khoản)
        new_user = models.User(
            username=final_username,
            password=hashed_password,
            role="employee", # Mặc định là nhân viên
            employee_id=new_emp.id
        )
        db.add(new_user)
        
        # 6. Commit toàn bộ vào DB
        db.commit()

        # 7. Gửi Email (Chạy ngầm - Background Task)
        background_tasks.add_task(
            send_account_email, 
            to_email=emp_in.email, 
            full_name=emp_in.full_name, 
            username=final_username, 
            temp_password=temp_password
        )

        return {
            "status": "success",
            "message": "Đã tạo nhân viên và gửi email cấp tài khoản.",
            "data": {
                "emp_code": new_emp.emp_code,
                "username": final_username,
                "full_name": new_emp.full_name
            }
        }

    except Exception as e:
        db.rollback()
        print(f"Lỗi tạo nhân viên: {e}")
        raise HTTPException(status_code=500, detail="Lỗi Server khi tạo nhân viên")
