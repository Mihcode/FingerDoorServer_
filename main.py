from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, case, text
from database import get_db, engine
import models, schemas

app = FastAPI()

#Login

@app.post("/api/login", response_model=schemas.UserResponse)
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
@app.get("/api/profile/{user_id}", response_model=schemas.ProfileResponse)
def get_profile(user_id: int, db: Session = Depends(get_db)):
    # 1. Tra cứu User trước
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 2. Lấy Employee từ User đó
    employee = user.employee
    if not employee:
         raise HTTPException(status_code=404, detail="User này chưa liên kết hồ sơ nhân viên")

    # 3. Map dữ liệu 
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
@app.get("/api/history", response_model=list[schemas.AttendanceResponse])
def get_history(user_id: int, month: int, year: int, db: Session = Depends(get_db)):
    
    # TRA CỨU USER ĐỂ LẤY EMP_ID 
    user = db.query(models.User).filter(models.User.id == user_id).first()

    # Nếu không tìm thấy user hoặc user này chưa liên kết với nhân viên nào
    if not user or not user.employee_id:
        return [] # Trả về danh sách rỗng

    records = db.query(models.DailyAttendance).filter(
        models.DailyAttendance.employee_id == emp_id, # Dùng emp_id vừa tìm được
        extract('month', models.DailyAttendance.work_date) == month,
        extract('year', models.DailyAttendance.work_date) == year
    ).order_by(models.DailyAttendance.work_date.desc()).all()
    
    # Map sang JSON
    history_list = []
    
    for row in records:
        # Tạo ID giả cho RecyclerView Android (VD: 20251224) vì row.work_date là kiểu Date, convert sang chuỗi rồi sang Int
        date_id = int(row.work_date.strftime("%Y%m%d"))
        
        # Tính OT (Logic cứng: Sau 17h00 là OT)
        ot_min = 0
        if row.check_out:
            # check_out trong DB là kiểu Time (VD: 18:30:00)
            out_minutes = row.check_out.hour * 60 + row.check_out.minute
            standard_end = 17 * 60 # 17:00 = 1020 phút
            
            if out_minutes > standard_end:
                ot_min = out_minutes - standard_end
        
        # Tạo object response
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
    
