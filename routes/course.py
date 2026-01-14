from fastapi import FastAPI,APIRouter, HTTPException
from Database.database import SUPABASE
from Model.models import CourseCreate, CourseRead, CourseType


router = APIRouter()
@router.get("/get/{course_code}", response_model=list[CourseRead]) #@router is a sub mdodule of FastAPI to handle routes
async def read_course(course_code:str):
    response = SUPABASE.table("COURSE").select("*").eq("course_code",course_code).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Course not found")
    return response.data

@router.get("/get/CoreDiscipline", response_model=list[CourseType])
async def read_core_discipline_course():
    response = SUPABASE.table("COURSE").select("*").eq("course_type","CD").execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Course discipline not found")
    return response.data

@router.get("/get/CoreSpecialization", response_model=list[CourseType])
async def read_core_specialization_course():
    response = SUPABASE.table("COURSE").select("*").eq("course_type","CSp").execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Course specialization not found")
    return response.data

@router.get("/get/UniversityRequirement", response_model=list[CourseType])
async def read_core_university_requirement():
    response = SUPABASE.table("COURSE").select("*").eq("course_type","UR").execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="University Requirement not found")
    return response.data

@router.get("/get/NationalRequirement", response_model=list[CourseType])
async def read_core_national_requirement():
    response = SUPABASE.table("COURSE").select("*").eq("course_type","NR").execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="National Requirement not found")
    return response.data

@router.get("/get/CommonCourse", response_model=list[CourseType])
async def read_core_discipline_course():
    response = SUPABASE.table("COURSE").select("*").eq("course_type","CC").execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Common Course not found")
    return response.data