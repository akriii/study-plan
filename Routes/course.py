from fastapi import FastAPI,APIRouter, HTTPException, Depends
from Database.database import SUPABASE
from Model.models import  CourseRead, CourseCreate
from Services.utils import authenticate_admin
from uuid import UUID
import json 

router = APIRouter()

@router.get("/get/all/{student_id}")
async def read_all_course(student_id: UUID):
    student_query = SUPABASE.table("STUDENT") \
        .select("student_department") \
        .eq("student_id", student_id) \
        .maybe_single() \
        .execute()
    
    if not student_query.data or not student_query.data.get("student_department"):
        raise HTTPException(
            status_code=404, 
            detail="Student department not found. Please set your department in your profile."
        )
    
    dept_name = student_query.data["student_department"]

    json_dept_query = json.dumps([dept_name])

    response = SUPABASE.table("COURSE") \
        .select("*") \
        .contains("course_department", json_dept_query) \
        .execute()

    if not response.data:
        raise HTTPException(
            status_code=404, 
            detail=f"No courses found for the {dept_name} department."
        )
    
    # 3. Data Normalization
    for course in response.data:
        pre_req = course.get("pre_requisite")
        course["pre_requisite"] = [pre_req] if isinstance(pre_req, str) else (pre_req or [])
        
    return response.data

async def get_courses_by_student_context(student_id: UUID, course_type: str):
    """
    Smarter helper that looks up the student's department first, 
    then filters the global COURSE table.
    """
    # 1. Fetch Student's Department
    student_query = SUPABASE.table("STUDENT") \
        .select("student_department") \
        .eq("student_id", student_id) \
        .maybe_single() \
        .execute()
    
    if not student_query.data or not student_query.data.get("student_department"):
        raise HTTPException(
            status_code=404, 
            detail="Student department not found. Please set your department in your profile."
        )
    
    dept_name = student_query.data["student_department"]

    # 2. Query COURSE table using Type and Department JSONB filter
    # We manually stringify the JSON list for PostgreSQL
    json_dept_query = json.dumps([dept_name])

    response = SUPABASE.table("COURSE") \
        .select("*") \
        .ilike("course_type", course_type.strip()) \
        .contains("course_department", json_dept_query) \
        .execute()

    if not response.data:
        raise HTTPException(
            status_code=404, 
            detail=f"No {course_type} courses found for the {dept_name} department."
        )
    
    # 3. Data Normalization
    for course in response.data:
        pre_req = course.get("pre_requisite")
        course["pre_requisite"] = [pre_req] if isinstance(pre_req, str) else (pre_req or [])
        
    return response.data

# --- Simplified Routes ---

@router.get("/get/CoreDiscipline/{student_id}")
async def read_core_discipline(student_id: UUID):
    return await get_courses_by_student_context(student_id, "CD")

@router.get("/get/CoreSpecialization/{student_id}")
async def read_core_specialization(student_id: UUID):
    return await get_courses_by_student_context(student_id, "CSp")

@router.get("/get/UniversityRequirement/{student_id}")
async def read_university_requirement(student_id: UUID):
    return await get_courses_by_student_context(student_id, "UR")

@router.get("/get/NationalRequirement/{student_id}")
async def read_national_requirement(student_id: UUID):
    return await get_courses_by_student_context(student_id, "NR")

@router.get("/get/CommonCourse/{student_id}")
async def read_common_courses(student_id: UUID):
    return await get_courses_by_student_context(student_id, "CC")

@router.get("/get/ElectiveMinor/{student_id}")
async def read_elective_minor(student_id: UUID):
    return await get_courses_by_student_context(student_id, "EM")

@router.get("/get/CourseIntern/{student_id}")
async def read_course_intern(student_id: UUID):
    return await get_courses_by_student_context(student_id, "CI")



#get specific course information
@router.get("/get/{course_code}", response_model=list[CourseRead]) #@router is a sub mdodule of FastAPI to handle routes
async def get_specific_course(course_code:str):
    response = SUPABASE.table("COURSE").select("*").eq("course_code",course_code).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Course not found")
    return response.data

async def get_available_courses_by_type(student_id: UUID, course_type: str):
    # 1. Fetch Student's Department using the correct column name
    student_info = SUPABASE.table("STUDENT") \
        .select("student_department") \
        .eq("student_id", student_id) \
        .maybe_single() \
        .execute()
    
    if not student_info.data or not student_info.data.get("student_department"):
        raise HTTPException(status_code=404, detail="Student department not found. Please update profile.")
    
    dept_name = student_info.data["student_department"]

    # 2. Fetch Student History (To check prerequisites and duplicates)
    history_res = SUPABASE.table("STUDENT_COURSE") \
        .select("course_code, status") \
        .eq("student_id", student_id) \
        .execute()
    
    planning_eligibility = {
        record["course_code"] for record in history_res.data 
        if record["status"] in ["Completed", "Current", "Planned"]
    }

    taken_or_planned = {
        record["course_code"] for record in history_res.data 
        if record["status"] in ["Current", "Completed", "Planned"]
    }

    # 3. Fetch Department-Specific Courses by Type using JSONB filter
    json_dept_query = json.dumps([dept_name])
    
    all_courses_res = SUPABASE.table("COURSE") \
        .select("*") \
        .eq("course_type", course_type) \
        .contains("course_department", json_dept_query) \
        .execute()
    
    if not all_courses_res.data:
        return []

    processed_courses = []
    for course in all_courses_res.data:
        code = course["course_code"]
        if code in taken_or_planned:
            continue
            
        # 4. Prerequisite and Status Logic
        pre_reqs = course.get("pre_requisite")
        cleaned_pre_reqs = [pre_reqs] if isinstance(pre_reqs, str) else (pre_reqs or [])
        course["pre_requisite"] = cleaned_pre_reqs

        # Eligibility Check (is_unlocked)
        course["is_unlocked"] = not cleaned_pre_reqs or all(pre in planning_eligibility for pre in cleaned_pre_reqs)
        processed_courses.append(course)

    return processed_courses
    
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

@router.get("/get/CourseAvailable/ElectiveMinor/{student_id}", response_model=list[CourseRead])
async def read_available_em(student_id: UUID):
    return await get_available_courses_by_type(student_id, "EM")

@router.get("/get/CourseAvailable/CourseIntern/{student_id}", response_model=list[CourseRead])
async def read_available_ci(student_id: UUID):
    return await get_available_courses_by_type(student_id, "CI")


#get all courses by department
@router.get("/get/all/CourseDepartment/{course_department}")
async def read_all_course_by_department(course_department:str):
    json_course_department = json.dumps([course_department.strip()])

    response = SUPABASE.table("COURSE").select("*").contains("course_department", json_course_department).execute()

    if not response.data:
        raise HTTPException(status_code=404, detail=f"No courses found for department: {course_department}")
    
    for course in response.data:
        pre_req = course.get("pre_requisite")
        course["pre_requisite"] = [pre_req] if isinstance(pre_req, str) else (pre_req or [])
    
    return response.data

@router.post("/upsert")
async def upsert_course_to_department(course: CourseCreate, department: str, username: str = Depends(authenticate_admin)):
    """
    Updates course details and appends a new department to the jsonb list 
    without overwriting existing departments.
    """
    # 1. Check if the course already exists globally
    existing = SUPABASE.table("COURSE") \
        .select("course_department") \
        .eq("course_code", course.course_code) \
        .maybe_single() \
        .execute()
    
    if existing and existing.data:
        # COURSE EXISTS: Prepare the merged department list
        current_depts = existing.data.get("course_department")
        
        # Normalize current_depts to a list
        if isinstance(current_depts, str):
            current_depts = [current_depts]
        elif current_depts is None:
            current_depts = []
            
        # Add the new department if it's not already there
        if department not in current_depts:
            current_depts.append(department)
            
        # 2. Prepare the update payload
        # We dump the new course details but override the department list with our merged one
        update_data = course.model_dump()
        update_data["course_department"] = current_depts

        # 3. Execute the update
        update_res = SUPABASE.table("COURSE") \
            .update(update_data) \
            .eq("course_code", course.course_code) \
            .execute()
        
        return {
            "message": f"Course details updated and linked to {department}.", 
            "data": update_res.data[0]
        }

    else:
        # COURSE IS NEW: Insert with the initial department list
        new_course_data = course.model_dump()
        new_course_data["course_department"] = [department]
        
        insert_res = SUPABASE.table("COURSE").insert(new_course_data).execute()
        
        if not insert_res.data:
            raise HTTPException(status_code=400, detail="Failed to create new course.")
            
        return {
            "message": "New course created and assigned to department.", 
            "data": insert_res.data[0]
        }