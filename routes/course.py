from fastapi import FastAPI,APIRouter, HTTPException
from Database.database import SUPABASE
from Model.models import  CourseRead
from uuid import UUID


router = APIRouter()
#get all course information
@router.get("/get", response_model=list[CourseRead])
async def read_all_course():
    response = SUPABASE.table("COURSE").select("*").execute()
    
    if not response.data:
        raise HTTPException(status_code=404, detail="Course not found")

    cleaned_data = []
    for course in response.data:
        pre_req = course.get("pre_requisite")

        if isinstance(pre_req, str):
            course["pre_requisite"] = [pre_req]
        elif pre_req is None:
            course["pre_requisite"] = []
        
        cleaned_data.append(course)

    return cleaned_data

async def get_courses(course_type: str):
    response = SUPABASE.table("COURSE").select("*").ilike("course_type", course_type.strip()).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Courses not found")
    return response.data
#get core discipline course information
@router.get("/get/CoreDiscipline")
async def read_all_core_discipline_courses():
    return await get_courses("CD")

#get core specialization course information only
@router.get("/get/CoreSpecialization")
async def read_all_core_specialization_courses():
    return await get_courses("CSp")

#get university requirement course information only
@router.get("/get/UniversityRequirement")
async def read_all_university_requirement_courses():
    return await get_courses("UR")

#get national requirement course information only
@router.get("/get/NationalRequirement")
async def read_all_national_requirement_courses():
    return await get_courses("NR")

#get common course information only
@router.get("/get/CommonCourse")
async def read_all_common_course_courses():
    return await get_courses("CC")

#get specific course information
@router.get("/get/{course_code}", response_model=list[CourseRead]) #@router is a sub mdodule of FastAPI to handle routes
async def get_specific_course(course_code:str):
    response = SUPABASE.table("COURSE").select("*").eq("course_code",course_code).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Course not found")
    return response.data

async def get_available_courses_by_type(student_id: UUID, course_type: str):
    history_res = SUPABASE.table("STUDENT_COURSE") \
        .select("course_code, grade, status") \
        .eq("student_id", student_id) \
        .execute()
    
    passed_courses = { 
        record["course_code"] for record in history_res.data 
        if record["status"] == "Completed" and record["grade"] not in ["F", "Fail", None]
    }

    # If a course is Current, Completed, or Planned, they shouldn't "add" it again
    unavailable_statuses = ["Current", "Completed", "Planned"]
    taken_or_planned = {
        record["course_code"] for record in history_res.data 
        if record["status"] in unavailable_statuses
    }

    all_courses_res = SUPABASE.table("COURSE") \
        .select("*") \
        .eq("course_type", course_type) \
        .execute()
    
    if not all_courses_res.data:
        return []

    available_courses = []

    for course in all_courses_res.data:
        code = course["course_code"]
        
        if code in taken_or_planned:
            continue
            
        pre_reqs = course.get("pre_requisite")
        
        if isinstance(pre_reqs, str):
            cleaned_pre_reqs = [pre_reqs] if pre_reqs.strip() else []
        elif isinstance(pre_reqs, list):
            cleaned_pre_reqs = pre_reqs
        else:
            cleaned_pre_reqs = []

        # Force the field to be a list so the Pydantic model doesn't crash
        course["pre_requisite"] = cleaned_pre_reqs

        # A course is available only if:
        # - It has no prerequisites OR
        # - All its prerequisites are in the 'passed_courses' set
        if not cleaned_pre_reqs or all(pre in passed_courses for pre in cleaned_pre_reqs):
            available_courses.append(course)

    return available_courses
    
@router.get("/get/CourseAvailable/CoreDiscipline/{student_id}", response_model=list[CourseRead])
async def read_available_cd(student_id: UUID):
    return await get_available_courses_by_type(student_id, "CD")

@router.get("/get/CourseAvailable/CoreSpecialization/{student_id}", response_model=list[CourseRead])
async def read_available_csp(student_id: UUID):
    return await get_available_courses_by_type(student_id, "CSp")

@router.get("/get/CourseAvailable/NationalRequirement/{student_id}", response_model=list[CourseRead])
async def read_available_nr(student_id: UUID):
    return await get_available_courses_by_type(student_id, "NR")

@router.get("/get/CourseAvailable/UniversityRequirement/{student_id}", response_model=list[CourseRead])
async def read_available_ur(student_id: UUID):
    return await get_available_courses_by_type(student_id, "UR")

@router.get("/get/CourseAvailable/CommonCourse/{student_id}", response_model=list[CourseRead])
async def read_available_cc(student_id: UUID):
    return await get_available_courses_by_type(student_id, "CC")