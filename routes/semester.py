from fastapi import FastAPI,APIRouter
from database import SUPABASE
from models import SemesterRead, SemesterCreate

router = APIRouter()
@router.get("/{student_id}", response_model=SemesterRead) #@router is a sub mdodule of FastAPI to handle routes
async def read_semester(student_id:str):
    response = SUPABASE.table("SEMESTER").select("*").eq("student_id",student_id).execute()
    return response.data

@router.post("/add" )  # Route to add a new semester
async def add_semester(semester:SemesterCreate):
    new_semester = {
        "semester_name": semester.semester_name,
        "semester_gpa": semester.semester_gpa,
        "sudent_id": semester.student_id
    }
    response = SUPABASE.table("SEMESTER").insert(new_semester).execute()
    return response.data