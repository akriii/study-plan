from fastapi import FastAPI,APIRouter, HTTPException
from Database.database import SUPABASE
from Model.models import  CourseRead
from uuid import UUID


router = APIRouter()
#get all course information
@router.get("/get", response_model=list[CourseRead]) #@router is a sub mdodule of FastAPI to handle routes
async def read_all_course():
    response = SUPABASE.table("COURSE").select("*").execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Course not found")
    return response.data

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



async def get_available_courses_by_type(student_id: UUID, course_type: str):  #accept the student id and course type sent by the router

    history_res = SUPABASE.table("STUDENT_COURSE") \
        .select("course_code, grade, status") \
        .eq("student_id", student_id) \
        .execute()
    
    passed_courses = {  #create a set of passed course and check whether the student course taken is passed or not
        record["course_code"] for record in history_res.data 
        if record["grade"] not in ["F", "Fail"] and record["status"] == "Completed"
    }

    all_courses_res = SUPABASE.table("COURSE") \
        .select("*") \
        .eq("course_type", course_type) \
        .execute()
    
    if not all_courses_res.data:
        return []

    available_courses = []

    for course in all_courses_res.data: #loop for every courses based on course type
        code = course["course_code"]  #initialize course code in course table based on course type into code
        
        if code in passed_courses: #check student has passed the courses or not
            continue
            
        pre_reqs = course.get("pre_requisite")
        
        if isinstance(pre_reqs, str): #if pre reqs is in str, change to list
            pre_reqs = [pre_reqs]
        elif pre_reqs is None:
            pre_reqs = []

        if not pre_reqs or all(pre in passed_courses for pre in pre_reqs):  #check if pre reqs not exist or pre reqs is passed
            available_courses.append(course) # Returning the full course object based on course

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