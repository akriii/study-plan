from fastapi import FastAPI,APIRouter, HTTPException
from Database.database import SUPABASE
from Model.models import  CourseRead, CourseCreate
from uuid import UUID
import json 

router = APIRouter()

@router.get("/get/department/{department_name}", response_model=list[CourseRead])
async def read_courses_by_department(department_name: str):
    # Manually convert the list to a JSON string: ["CEE"]
    json_query = json.dumps([department_name]) 
    
    # Pass the stringified JSON directly to the filter
    response = SUPABASE.table("COURSE") \
        .select("*") \
        .contains("course_department", json_query) \
        .execute()
    
    if not response.data:
        raise HTTPException(
            status_code=404, 
            detail=f"No courses found for the {department_name} department."
        )

    # Standard normalization for prerequisites
    for course in response.data:
        # Handle pre_requisite cleaning
        pre_req = course.get("pre_requisite")
        if isinstance(pre_req, str):
            course["pre_requisite"] = [pre_req]
        elif pre_req is None:
            course["pre_requisite"] = []
            
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

async def get_available_courses_by_type(student_id: UUID, course_type: str):
    history_res = SUPABASE.table("STUDENT_COURSE") \
        .select("course_code, grade, status") \
        .eq("student_id", student_id) \
        .execute()
    
    # 1. These are the courses that "unlock" future ones
    planning_eligibility = {
        record["course_code"] for record in history_res.data 
        if record["status"] in ["Completed", "Current", "Planned"]
    }

    # 2. These are courses already in the student's list (don't show these at all)
    taken_or_planned = {
        record["course_code"] for record in history_res.data 
        if record["status"] in ["Current", "Completed", "Planned"]
    }

    all_courses_res = SUPABASE.table("COURSE") \
        .select("*") \
        .eq("course_type", course_type) \
        .execute()
    
    if not all_courses_res.data:
        return []

    processed_courses = []

    for course in all_courses_res.data:
        code = course["course_code"]
        
        # We still skip courses the student is ALREADY taking/planned
        if code in taken_or_planned:
            continue
            
        pre_reqs = course.get("pre_requisite")
        
        # Normalize pre_reqs to a list
        if isinstance(pre_reqs, str):
            cleaned_pre_reqs = [pre_reqs.strip()] if pre_reqs.strip() else []
        elif isinstance(pre_reqs, list):
            cleaned_pre_reqs = [p.strip() for p in pre_reqs if p.strip()]
        else:
            cleaned_pre_reqs = []

        course["pre_requisite"] = cleaned_pre_reqs

        # 3. THE KEY CHANGE: Add a status flag instead of filtering
        # Check if all prerequisites are in the planning_eligibility set
        is_eligible = not cleaned_pre_reqs or all(pre in planning_eligibility for pre in cleaned_pre_reqs)
        
        course["is_unlocked"] = is_eligible
        
        # We now append EVERYTHING that isn't already taken
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



@router.post("/upsert")
async def upsert_course_to_department(course: CourseCreate, department: str):
    """
    Adds a new course or links an existing course to a new department 
    using the jsonb course_department list.
    """
    # 1. Check if the course already exists globally by its code
    existing = SUPABASE.table("COURSE") \
        .select("course_department") \
        .eq("course_code", course.course_code) \
        .maybe_single() \
        .execute()

    if existing.data:
        # COURSE EXISTS: We only need to update the department list
        current_depts = existing.data.get("course_department")
        
        # Normalize current_depts to a list if it's a string or None
        if isinstance(current_depts, str):
            current_depts = [current_depts]
        elif current_depts is None:
            current_depts = []
            
        if department not in current_depts:
            current_depts.append(department)
            
            # Update only the department column
            update_res = SUPABASE.table("COURSE") \
                .update({"course_department": current_depts}) \
                .eq("course_code", course.course_code) \
                .execute()
            
            return {"message": f"Course linked to {department} successfully.", "data": update_res.data[0]}
        
        return {"message": "Course is already associated with this department."}

    else:
        # COURSE IS NEW
        new_course_data = course.model_dump()
        
        # Ensure course_department is a list containing the initial department
        new_course_data["course_department"] = [department]
        
        insert_res = SUPABASE.table("COURSE").insert(new_course_data).execute()
        
        if not insert_res.data:
            raise HTTPException(status_code=400, detail="Failed to create new course.")
            
        return {"message": "New course created and assigned to department.", "data": insert_res.data[0]}