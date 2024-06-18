# service2.py

from fastapi import FastAPI, UploadFile, File
import pytesseract
from PIL import Image
import io
import random

app = FastAPI()

@app.post("/process-id/")
async def process_id(file: UploadFile = File(...)):
    image = Image.open(io.BytesIO(await file.read()))
    try:
        employee_id = pytesseract.image_to_string(image, config='--psm 8').strip()
    except Exception as e:
        return {"error": str(e)}

    # If no ID was detected, generate a random one
    if not employee_id:
        employee_id = ''.join([str(random.randint(0, 9)) for _ in range(3)])
    
    # Ensure the employee_id is exactly 3 digits
    employee_id = employee_id.zfill(3)
    
    return {"employee_id": employee_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
