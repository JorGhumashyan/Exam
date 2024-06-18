# service1.py

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from database import SessionLocal, init_db, Employee
from pydantic import BaseModel
import requests
import io

app = FastAPI()

init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class EmployeeCreate(BaseModel):
    first_name: str
    last_name: str
    age: int
    position: str
    remote: bool
    employee_id: int

@app.post("/employees/new")
async def create_employee(
    first_name: str = Form(...),
    last_name: str = Form(...),
    age: int = Form(...),
    position: str = Form(...),
    remote: bool = Form(...),
    employee_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Forward the image to Service 2 to get the employee ID
    response = requests.post("http://127.0.0.1:9000/process-id/", files={"file": (file.filename, file.file, file.content_type)})
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Error processing image")

    employee_id = response.json().get("employee_id")
    if not employee_id:
        raise HTTPException(status_code=500, detail="Could not extract employee ID")

    # Create new employee record
    employee = Employee(
        first_name=first_name,
        last_name=last_name,
        age=age,
        position=position,
        remote=remote,
        employee_id=employee_id
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    
    return {"status": "success", "employee_id": employee_id}

@app.get("/employees/list")
async def list_employees(
    name: str = None,
    position: str = None,
    remote: bool = None,
    employee_id: str = None,
    db: Session = Depends(get_db)
):
    query = db.query(Employee)
    if name:
        query = query.filter(Employee.first_name.contains(name) | Employee.last_name.contains(name))
    if position:
        query = query.filter(Employee.position == position)
    if remote is not None:
        query = query.filter(Employee.remote == remote)
    if employee_id:
        query = query.filter(Employee.employee_id == employee_id)
    
    employees = query.all()
    return employees

@app.get("/employees/{id}")
async def get_employee(id: int, db: Session = Depends(get_db)):
    employee = db.query(Employee).filter(Employee.id == id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8800)
