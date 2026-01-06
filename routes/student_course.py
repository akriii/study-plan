from fastapi import FastAPI,APIRouter, HTTPException
from database import SUPABASE
from models import  CourseRead, Summary, StudentCourseAdd
from utils import Calc_Cgpa, CountInProgress, Find_Prerequisite

router = APIRouter()
@router.get("/get/{student_id}/{course_code}", response_model=list[CourseRead]) #@router is a sub mdodule of FastAPI to handle routes
async def read_student_course(student_id:str, course_code:str):
    response = SUPABASE.table("COURSE").select("*").eq("student_id",student_id).eq("course_code",course_code).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Record not found")
    return response.data

@router.post("/add" )  # Route to add a new course
async def add_student_course(course:StudentCourseAdd):
    #pre requisite calc
   
    course_info = SUPABASE.table("COURSE").select("pre_requisite").eq("course_code",course.course_code).single().execute()

    if not course_info.data:
        raise HTTPException(status_code=404, detail="No pre-requisite found")
    
    prerequisite_code = course_info.data.get("pre_requisite")
    if prerequisite_code:
        history = SUPABASE.table("STUDENT_COURSE") \
            .select("grade, status") \
            .eq("student_id", course.student_id) \
            .eq("course_code", prerequisite_code) \
            .execute()
    
        if not history.data:
            raise HTTPException(status_code=400, detail=f"Prerequisite {prerequisite_code} not taken")
    
        student_history = history.data[0]
        if student_history["grade"] == "F" or student_history["status"] != "Completed":
            raise HTTPException(status_code=400, detail=f"Prerequisite {prerequisite_code} not passed")
    
    new_course = {
        "student_id": course.student_id,
        "course_code": course.course_code,
        "semester": course.semester,
        "grade": course.grade,
        "status": course.status
    }
    response = SUPABASE.table("STUDENT_COURSE").insert(new_course).execute()
    return response.data[0]

#route to get completed course
@router.get("/Completed/{student_id}", response_model=list[CourseRead])
async def completed_course(student_id:str):
    response = SUPABASE.table("STUDENT_COURSE").select("*").eq("student_id",student_id).eq("status","Completed").execute()

    if not response.data:
        raise HTTPException(status_code=404, detail="Course not found")
    
    return response.data

#route to get in progress course
@router.get("/InProgress/{student_id}", response_model=list[CourseRead])
async def in_progress_course(student_id:str):

    response = SUPABASE.table("STUDENT_COURSE").select("*").eq("student_id",student_id).eq("status","In Progress").execute()

    if not response.data:
        raise HTTPException(status_code=404, detail="Course not found")
    
    return response.data

#calculation
@router.get("/Summary/{student_id}", response_model=Summary)
async def summary(student_id:str):

    
    response = SUPABASE.table("STUDENT_COURSE").select("*").eq("student_id",student_id).execute()

    course = response.data
    if not response.data :
        return {"count_course": 0, "student_cgpa": 0.0}
    in_progress_list = [c for c in course if c["status"] == "In Progress"]
    completed_list = [c for c in course if c["status"] == "Completed"]
    
    cgpa = Calc_Cgpa(completed_list)
    count_in_progress = CountInProgress(in_progress_list)
    return {"count_course":count_in_progress,
            "student_cgpa":cgpa}
