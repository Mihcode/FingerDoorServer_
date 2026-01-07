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
@app.get("/api/profile/{employee_id}", response_model=schemas.ProfileResponse)
def get_profile(employee_id: int, db : Session = Depends(get_db)):
    Employee = db.query(models.Employee).filter(models.Employee.id == employee_id).first()
    if not Employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    # chuyển date sang str
    emp_dict = Employee.__dict__.copy()
    emp_dict['dob'] = str(Employee.dob)
    emp_dict['start_date'] = str(Employee.start_date)

    return {
        "employee": emp_dict,
        "salary": Employee.salary_info
    }

# lịch sử chấm công

    
