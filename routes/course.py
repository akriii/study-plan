from fastapi import FastAPI,APIRouter, HTTPException
from database import SUPABASE
from models import CourseCreate, CourseRead,Summary
from utils import CountInProgress,Calc_Cgpa

router = APIRouter()
@router.get("/{student_id}/{semester_id}", response_model=list[CourseRead]) #@router is a sub mdodule of FastAPI to handle routes
async def read_course(student_id:str, semester_id:str):
    response = SUPABASE.table("COURSE").select("*").eq("student_id",student_id).eq("semester_id",semester_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Student not found")
    return response.data

@router.post("/add") 
async def add_course(course: CourseCreate): 
    new_course = {
        "course_name": course.course_name,
        "credit_hour": course.credit_hour,
        "student_grade": course.student_grade,
        "course_code": course.course_code,
        "semester_id": course.semester_id, # fk semester id
        "student_id": course.student_id,   # fk student id
        "prerequisite": course.prerequisite
    }
    #pre requisite logic calc
    
    response = SUPABASE.table("COURSE").insert(new_course).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Course not found")
    
    return response.data

#route to get completed course
@router.get("/Completed/{student_id}", response_model=list[CourseRead])
async def completed_course(student_id:str):
    response = SUPABASE.table("COURSE").select("*").eq("student_id",student_id).not_.eq("student_grade","In Progress").execute()

    if not response.data:
        raise HTTPException(status_code=404, detail="Course not found")
    
    return response.data

#route to get in progress course
@router.get("/InProgress/{student_id}", response_model=list[CourseRead])
async def in_progress_course(student_id:str):

    response = SUPABASE.table("COURSE").select("*").eq("student_id",student_id).eq("student_grade","In Progress").execute()

    if not response.data:
        raise HTTPException(status_code=404, detail="Course not found")
    
    return response.data

#calculation
@router.get("/Summary/{student_id}", response_model=Summary)
async def summary(student_id:str):

    
    response = SUPABASE.table("COURSE").select("*").eq("student_id",student_id).execute()

    course = response.data
    if not response.data :
        raise HTTPException(status_code=404, detail="Course not found")
    in_progress_list = [c for c in course if c["student_grade"] == "In Progress"]
    completed_list = [c for c in course if c["student_grade"] != "In Progress"]
    
    cgpa = Calc_Cgpa(completed_list)
    count_in_progress = CountInProgress(in_progress_list)
    return {"count_course":count_in_progress,
            "student_cgpa":cgpa}




