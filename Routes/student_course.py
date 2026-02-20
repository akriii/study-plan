from fastapi import FastAPI,APIRouter, HTTPException
from Database.database import SUPABASE
from Model.models import   Summary, StudentCourseAdd, ReadSemesterCourse, UpdateStudentCourse, SemesterRemove, Gpa
from Services.utils import Calc_Cgpa, Get_Probation_Status, calculate_points_and_credits
from uuid import UUID
import copy

router = APIRouter()
#get list of course taken by each semester
@router.get("/get/SemesterCourse/{student_id}/{semester}", response_model=list[ReadSemesterCourse])
async def get_semester_course(student_id: UUID, semester: int):
    response = SUPABASE.table("STUDENT_COURSE") \
    .select("*, COURSE(course_code ,course_name, credit_hour, course_type, course_semester, course_desc, course_department)")  \
    .eq("student_id", student_id) \
    .eq("semester", semester) \
    .execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Record not found")


    final_results = []

    for record in response.data:
        # 1. Grab the grade and the nested COURSE dict
        grade = record.get("grade")
        course_info = record.get("COURSE")

        # 2. If grade is F, we modify the dictionary directly inside the record
        if course_info and grade == "F":
            course_info["credit_hour"] = 0.0
            # Optional Debug: print(f"DEBUG: Setting {record['course_code']} credits to 0")

        final_results.append(record)

    return final_results

@router.get("/get/Standing/{student_id}/{semester}")
async def get_academic_standing(student_id: UUID, semester: int):
    """
    Checks the previous semester's results to determine the credit limit 
    for the requested semester.
    """
    is_probation, max_limit = Get_Probation_Status(str(student_id), semester)
    
    current_sem_res = SUPABASE.table("STUDENT_COURSE") \
        .select("*, COURSE(credit_hour)") \
        .eq("student_id", student_id) \
        .eq("semester", semester).execute()
    
    _, enrolled_credits = calculate_points_and_credits(current_sem_res.data)

    return {
        "semester": semester,
        "academic_meta": {
            "is_probation": is_probation,
            "max_limit": max_limit,
            "enrolled_credits": enrolled_credits,
            "remaining_credits": max(0, max_limit - enrolled_credits),
            "status_label": "Probation" if is_probation else "Normal"
        }
    }

@router.get("/get/{student_id}/{course_code}/{semester}", response_model=list[ReadSemesterCourse])
async def read_student_course_specific(student_id: UUID, course_code: str, semester: int):
    response = SUPABASE.table("STUDENT_COURSE")\
        .select("*, COURSE(course_code,course_name, credit_hour, course_type,pre_requisite, course_semester, course_desc, course_department)")\
        .eq("student_id", student_id)\
        .eq("course_code", course_code)\
        .eq("semester", semester)\
        .execute() 
        
    if not response.data:
        raise HTTPException(status_code=404, detail="Record not found")


    final_results = []

    for record in response.data:
        # 1. Grab the grade and the nested COURSE dict
        grade = record.get("grade")
        course_info = record.get("COURSE")

        # 2. If grade is F, we modify the dictionary directly inside the record
        if course_info and grade == "F":
            course_info["credit_hour"] = 0.0
            # Optional Debug: print(f"DEBUG: Setting {record['course_code']} credits to 0")

        final_results.append(record)

    return final_results


#route to get all course student_course data
@router.get("/get/{student_id}", response_model=list[ReadSemesterCourse]) 
async def read_student_course_all(student_id: UUID):
    response = SUPABASE.table("STUDENT_COURSE") \
        .select("*, COURSE(course_code, course_name, credit_hour, course_type, pre_requisite, course_semester, course_desc, course_department)") \
        .eq("student_id", student_id) \
        .execute()
    
    if not response.data:
        raise HTTPException(status_code=404, detail="Record not found")


    final_results = []

    for record in response.data:
        # 1. Grab the grade and the nested COURSE dict
        grade = record.get("grade")
        course_info = record.get("COURSE")

        # 2. If grade is F, we modify the dictionary directly inside the record
        if course_info and grade == "F":
            course_info["credit_hour"] = 0.0
            # Optional Debug: print(f"DEBUG: Setting {record['course_code']} credits to 0")

        final_results.append(record)

    return final_results

#add new student_course based on pre-requisite
@router.post("/add")
async def add_student_course(course: StudentCourseAdd):
    # 1. Fetch Course Info
    course_query = SUPABASE.table("COURSE").select("*").eq("course_code", course.course_code).maybe_single().execute()
    if not course_query.data:
        raise HTTPException(status_code=404, detail="Course code not found")
    
    new_course_credits = course_query.data.get("credit_hour", 0)
    raw_pre_reqs = course_query.data.get("pre_requisite")
    
    # 2. Normalize Pre-reqs
    if isinstance(raw_pre_reqs, str):
        pre_reqs = [raw_pre_reqs.strip()] if raw_pre_reqs.strip() else []
    elif isinstance(raw_pre_reqs, list):
        pre_reqs = [p.strip() for p in raw_pre_reqs if p.strip()]
    else:
        pre_reqs = []

    # 3. Check Academic Status & Limits
    is_probation, max_limit = Get_Probation_Status(str(course.student_id), course.semester)
    
    current_sem_res = SUPABASE.table("STUDENT_COURSE") \
        .select("*, COURSE(credit_hour)") \
        .eq("student_id", course.student_id) \
        .eq("semester", course.semester).execute()
    
    _, current_credits = calculate_points_and_credits(current_sem_res.data)
    
    # 4. Prerequisite Logic
    has_passed_all_prereqs = True
    missing_prereqs = []

    if pre_reqs:
        for pre_code in pre_reqs:
            # Fetch ALL attempts for this prerequisite
            history = SUPABASE.table("STUDENT_COURSE").select("grade, status") \
                .eq("student_id", course.student_id) \
                .eq("course_code", pre_code).execute()
            
            # Check if ANY of the attempts were successful
            passed = False
            if history.data:
                # We loop through all records to see if a pass exists
                for record in history.data:
                    if record["status"] == "Completed" and record["grade"] not in ["F", "Fail", None]:
                        passed = True
                        break # Found a pass, no need to check other attempts
            
            if not passed:
                has_passed_all_prereqs = False
                missing_prereqs.append(pre_code)

    # 5. Insert Record
    if course.grade and course.grade.strip():
        course.status = "Completed"
    
    new_enrollment = {
        "student_id": str(course.student_id),
        "course_code": course.course_code,
        "semester": course.semester,
        "grade": course.grade,
        "status": course.status
    }
    
    try:
        response = SUPABASE.table("STUDENT_COURSE").insert(new_enrollment).execute()
        result = response.data[0]
        
        return {
            "success": True,
            "data": result,
            "academic_meta": {
                "is_probation": is_probation,
                "max_limit": max_limit,
                "current_total_credits": current_credits + new_course_credits,
                "limit_exceeded": (current_credits + new_course_credits) > max_limit,
                "prereqs_met": has_passed_all_prereqs,
                "missing_prereqs": missing_prereqs
            }
        }
    except Exception:
        raise HTTPException(status_code=400, detail="Course already exists in your records.")

async def get_courses(student_id: UUID, status: str):
    response = SUPABASE.table("STUDENT_COURSE").select("*, COURSE(course_code,course_name, credit_hour, course_type, pre_requisite, course_department)").eq("student_id",student_id).eq("status",status).execute()

    if not response.data:
        return []
    return response.data

#route to get completed course
@router.get("/CompletedCourse/{student_id}", response_model=list[ReadSemesterCourse]) #use list because it returns multiple items of student course
async def list_completed_course(student_id:UUID):
    return await get_courses(student_id, "Completed")

#route to get in progress course
@router.get("/CurrentCourse/{student_id}", response_model=list[ReadSemesterCourse])
async def list_current_course(student_id:UUID):
    return await get_courses(student_id, "Current")

@router.get("/PlannedCourse/{student_id}", response_model=list[ReadSemesterCourse])
async def list_planned_course(student_id:UUID):
    return await get_courses(student_id, "Planned")

#calculation
@router.get("/Summary/{student_id}", response_model=Summary)
async def get_student_summary(student_id: UUID):
    # Fetch records including the semester column
    response = SUPABASE.table("STUDENT_COURSE")\
        .select("course_code,semester, grade, status, COURSE(credit_hour)")\
        .eq("student_id", student_id)\
        .execute()

    all_data = response.data
    if not all_data:
        return {
            "count_completed_course": 0, 
            "count_current_course": 0, 
            "count_planned_course": 0, 
            "student_cgpa": 0.0,
            "semester_credits": {},
            "academic_meta": {
                "is_probation": False,
                "max_limit": 15,
                "current_semester": "1",
                "status_label": "Normal"
            }
        }

    # 1. Standard Status Filtering
    completed_list = [c for c in all_data if c["status"] == "Completed"]
    current_list = [c for c in all_data if c["status"] == "Current"]
    planned_list = [c for c in all_data if c["status"] == "Planned"]
    
    # 2. Semester Credit Hour Calculation
    sem_credits = {}
    for record in all_data:
        sem = str(record.get("semester")) 
        course_info = record.get("COURSE") or {}
        credits = course_info.get("credit_hour", 0)
        sem_credits[sem] = sem_credits.get(sem, 0) + credits

    # 3. CGPA Calculation
    cgpa = Calc_Cgpa(completed_list)

    try:
        # Convert keys to int to find max, then back to string
        latest_sem = str(max([int(s) for s in sem_credits.keys() if s.isdigit()] or [1]))
    except ValueError:
        latest_sem = "1"

    is_probation, max_limit = Get_Probation_Status(str(student_id), latest_sem)
    
    return {
        "count_completed_course": len(completed_list),
        "count_current_course": len(current_list),
        "count_planned_course": len(planned_list),
        "student_cgpa": cgpa,
        "semester_credits": sem_credits,
        "academic_meta": {
            "is_probation": is_probation,
            "max_limit": max_limit,
            "current_semester": latest_sem,
            "status_label": "Probation" if is_probation else "Normal"
        }
    }

@router.get("/GPA/{student_id}/{semester_id}")
async def get_semester_gpa(student_id: UUID, semester_id: int):
    response = SUPABASE.table("STUDENT_COURSE")\
        .select("course_code, grade, status, semester, COURSE(credit_hour)")\
        .eq("student_id", student_id)\
        .eq("semester", semester_id)\
        .eq("status", "Completed")\
        .execute()

    if not response.data:
        return {
            "semester": semester_id,
            "student_gpa": 0.0,
            "message": "No completed courses found for this semester"
        }

    gpa = Calc_Cgpa(response.data) 
    
    return {
        "semester": semester_id,
        "student_gpa": gpa
    }

@router.put("/update/StudentCourse/{student_id}/{course_code}/{semester}", response_model=list[UpdateStudentCourse])
async def edit_student_course(student_id: UUID, course_code: str, semester: int, studentcourse_data: UpdateStudentCourse):
    data = studentcourse_data.model_dump(exclude_unset=True)

    # Added .eq("semester", semester) to target the specific record
    response = SUPABASE.table("STUDENT_COURSE")\
        .update(data)\
        .eq("student_id", student_id)\
        .eq("course_code", course_code)\
        .eq("semester", semester)\
        .execute()
        
    if not response.data:
        raise HTTPException(status_code=404, detail="Specific student course record not found")
    
    return response.data
#delete entire semester
@router.delete("/delete/semester/{student_id}/{semester}" ,response_model=SemesterRemove)
async def delete_semester(student_id:UUID, semester: int):
    

    response = SUPABASE.table("STUDENT_COURSE").delete().eq("student_id",student_id).eq("semester", semester).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Student not found")
    
    return {"message": f"Semester {semester} successfully deleted"}

#delete course in student_course table
# Updated route to include semester
@router.delete("/delete/course/{student_id}/{course_code}/{semester}", response_model=SemesterRemove)
async def delete_student_coursecode(student_id: UUID, course_code: str, semester: int):
    
    # Added .eq("semester", semester)
    response = SUPABASE.table("STUDENT_COURSE")\
        .delete()\
        .eq("student_id", student_id)\
        .eq("course_code", course_code)\
        .eq("semester", semester)\
        .execute()
        
    if not response.data:
        raise HTTPException(status_code=404, detail="Record not found")
    
    return {"message": f"Course {course_code} in Semester {semester} successfully deleted"}
