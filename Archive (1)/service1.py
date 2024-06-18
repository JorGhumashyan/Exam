from fastapi import Request, FastAPI, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from database import SessionLocal, init_db, Employee
from pydantic import BaseModel
import pytesseract
import random
import io
from PIL import Image
import logging
from typing import Annotated

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    employee_id: str


def process_id(file):
    image = Image.open(io.BytesIO(file))
    try:
        employee_id = pytesseract.image_to_string(image, config='--psm 8').strip()
    except Exception as e:
        return {"error": str(e)}

    # If no ID was detected, generate a random one
    if not employee_id:
        employee_id = ''.join([str(random.randint(0, 9)) for _ in range(3)])

    # Ensure the employee_id is exactly 3 digits
    employee_id = employee_id.zfill(3)

    return employee_id


async def get_body(request: Request):
    content_type = request.headers.get('Content-Type')
    if content_type is None:
        raise HTTPException(status_code=400, detail='No Content-Type provided!')
    elif (content_type == 'application/x-www-form-urlencoded' or
          content_type.startswith('multipart/form-data')):
        try:
            return await request.form()
        except Exception:
            raise HTTPException(status_code=400, detail='Invalid Form data')
    else:
        raise HTTPException(status_code=400, detail='Content-Type not supported!')

@app.post("/employees/new")
async def create_employee(
        first_name: str = Form(..., description=""),
        last_name: str = Form(..., description=""),
        age: int = Form(..., description=""),
        position: str = Form(..., description=""),
        remote: bool = Form(..., description=""),
        file: UploadFile = File(),
        db: Session = Depends(get_db)
):

    logger.info(f"remote_bool: {remote}")

    # Forward the image to Service 2 to get the employee ID
    employee_id = process_id(file.file.read())

    logger.info(f"employee_id: {employee_id}")

    if not employee_id:
        raise HTTPException(status_code=500, detail="Could not extract employee ID")

    # Create new employee record
    employee = Employee(
        first_name= first_name,
        last_name= last_name,
        age= age,
        position= position,
        remote= remote,
        employee_id= employee_id
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
