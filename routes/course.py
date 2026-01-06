from fastapi import FastAPI,APIRouter, HTTPException
from database import SUPABASE
from models import CourseCreate, CourseRead,Summary
from utils import CountInProgress,Calc_Cgpa

router = APIRouter()
@router.get("/get/{course_code}", response_model=list[CourseRead]) #@router is a sub mdodule of FastAPI to handle routes
async def read_student_course(student_id:str, course_code:str):
    response = SUPABASE.table("COURSE").select("*").eq("course_code",course_code).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Course not found")
    return response.data



