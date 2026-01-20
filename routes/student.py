from fastapi import FastAPI,APIRouter, HTTPException
from Database.database import SUPABASE
from Model.models import StudentCreate, StudentRead,StudentLogin, StudentUpdate, StudentCalcGOT
from Services.utils import HashPassword, VerifyPassword
from uuid import UUID
from fastapi.encoders import jsonable_encoder
from datetime import date, datetime

router = APIRouter() #defining a router for student-related routes

#route to fetch student based on student id sent by react
@router.get("/{student_id}", response_model=StudentRead) #@router is a sub mdodule of FastAPI to handle routes
async def read_students(student_id:UUID):
    response = SUPABASE.table("STUDENT").select("*").eq("student_id",student_id).single().execute() #query for get all students data
    if not response.data:
        raise HTTPException(status_code=404, detail="Student not found")
        
    return response.data

# Route to add a new student
@router.post("/register")  
async def register_student(student: StudentCreate):
    raw_password = student.student_password
    hashed = HashPassword(raw_password)
    new_student = {
        "student_name": student.student_name,
        "student_email": student.student_email,
        "student_password": hashed,
    }
    
    response = SUPABASE.table("STUDENT").insert(new_student).execute() 
    
    # FIX: Return the first item of the list
    if response.data:
        return response.data[0]
    
    raise HTTPException(status_code=400, detail="Registration failed")


@router.put("/update_got/{student_id}") 
async def update_got(student_id: UUID, data: StudentCalcGOT):
    
    clean_payload = data.model_dump(mode='json')
    
    response = SUPABASE.table("STUDENT") \
        .update(clean_payload) \
        .eq("student_id", student_id) \
        .execute()

    return jsonable_encoder(response.data)

# Route for student login
@router.post("/login")  
async def login_student(student:StudentLogin):


    response = SUPABASE.table("STUDENT").select("*").eq("student_email", student.student_email).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Email not found")
    
    user_record = response.data[0]
    hashed_db_password = user_record["student_password"]

    is_password_correct = VerifyPassword(student.student_password, hashed_db_password)
    if not is_password_correct:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    return {
        "message": "Login successful",
        "student_name": user_record["student_name"],
        "student_id": user_record["student_id"]
    }

#route for update all student information
@router.put("/update/{student_id}" ,response_model=StudentUpdate)
async def update_student(student_id:UUID, student_data:StudentUpdate):
    data = student_data.model_dump(exclude_unset=True)

    response = SUPABASE.table("STUDENT").update(data).eq("student_id",student_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Student not found")
    
    return response.data[0]

#route for delete student id
@router.delete("/delete/{student_id}")
async def delete_student(student_id:UUID):
    

    response = SUPABASE.table("STUDENT").delete().eq("student_id",student_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Student not found")
    
    return {"message": f"Student {student_id} successfully deleted"}

