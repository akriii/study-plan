from fastapi import FastAPI,APIRouter, HTTPException
from Database.database import SUPABASE
from Model.models import   Summary, StudentCourseAdd, ReadSemesterCourse, UpdateStudentCourse, SemesterRemove, Gpa
from Services.utils import Calc_Cgpa, Calc_Gpa
from uuid import UUID

router = APIRouter()
#route to get sepcific student_course data
@router.get("/get/{student_id}/{course_code}", response_model=list[ReadSemesterCourse]) #@router is a sub mdodule of FastAPI to handle routes
async def read_student_course_specific(student_id:UUID, course_code:str):
    response = SUPABASE.table("STUDENT_COURSE").select("*, COURSE(course_code,course_name, credit_hour, course_type,pre_requisite)").eq("student_id",student_id).eq("course_code",course_code).execute() #query to get student_course and course data based on course_code
    if not response.data:
        raise HTTPException(status_code=404, detail="Record not found")
    return response.data

#route to get all student_course data
@router.get("/get/{student_id}", response_model=list[ReadSemesterCourse]) 
async def read_student_course_all(student_id:UUID):
    response = SUPABASE.table("STUDENT_COURSE").select("*, COURSE(course_code,course_name, credit_hour, course_type, pre_requisite)").eq("student_id",student_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Record not found")
    return response.data

#get list of course taken by each semester
@router.get("/get/SemesterCourse/{student_id}/{semester}", response_model=list[ReadSemesterCourse])
async def get_semester_course(student_id: str, semester: int):
    response = SUPABASE.table("STUDENT_COURSE") \
    .select("*, COURSE(course_code ,course_name, credit_hour, course_type)")  \
    .eq("student_id", student_id) \
    .eq("semester", semester) \
    .execute()
    if not response.data:
        return []
    return response.data

#add new student_course based on pre-requisite
@router.post("/add")
async def add_student_course(course: StudentCourseAdd):
    course_query = SUPABASE.table("COURSE").select("pre_requisite").eq("course_code", course.course_code).single().execute()
    
    if not course_query.data:
        raise HTTPException(status_code=404, detail="Course code not found in system")
    pre_reqs = course_query.data.get("pre_requisite")

    if isinstance(pre_reqs, str):
        pre_reqs = [pre_reqs]
    elif pre_reqs is None:
        pre_reqs = []

    if pre_reqs:
        for pre_code in pre_reqs:
            if not pre_code: continue 

            history = SUPABASE.table("STUDENT_COURSE").select("grade, status") \
                .eq("student_id", course.student_id) \
                .eq("course_code", pre_code).execute()
            
            if not history.data:
                raise HTTPException(status_code=400, detail=f"Cannot enroll. Prerequisite {pre_code} has not been taken.")
            
            record = history.data[0]
            
            is_failed = record["grade"] in ["F", "f", "Fail", "FAIL"]
            is_not_finished = record["status"] != "Completed"

            if is_failed or is_not_finished:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Requirement Unmet: {pre_code} must be 'Completed' and 'Passed' first."
                )
            
    if course.grade:
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
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail="Failed to add course. It might already exist in your records.")

async def get_courses(student_id: UUID, status: str):
    response = SUPABASE.table("STUDENT_COURSE").select("*").eq("student_id",student_id).eq("status",status).execute()

    if not response.data:
        return []
    return response.data

#route to get completed course
@router.get("/Completed/{student_id}", response_model=list[ReadSemesterCourse]) #use list because it returns multiple items of student course
async def completed_course(student_id:UUID):
    return await get_courses(student_id, "Completed")

#route to get in progress course
@router.get("/InProgress/{student_id}", response_model=list[ReadSemesterCourse])
async def in_progress_course(student_id:UUID):
    return await get_courses(student_id, "In Progress")

#calculation
@router.get("/Summary/{student_id}", response_model=Summary)
async def get_student_summary(student_id: UUID):
    # Fetch all records for the student
    response = SUPABASE.table("STUDENT_COURSE")\
        .select("grade, status, COURSE(credit_hour)")\
        .eq("student_id", student_id)\
        .execute()

    all_data = response.data
    if not all_data:
        return {"count_course": 0, "count_completed": 0, "student_cgpa": 0.0}

    completed_list = [c for c in all_data if c["status"] == "Completed"]
    in_progress_count = len([c for c in all_data if c["status"] == "In Progress"])
    
    cgpa = Calc_Cgpa(completed_list)
    
    return {
        "count_course": in_progress_count,
        "count_completed": len(completed_list),
        "student_cgpa": cgpa
    }

@router.get("/GPA/{student_id}/{semester_id}")
async def get_semester_gpa(student_id: UUID, semester_id: int):
    response = SUPABASE.table("STUDENT_COURSE")\
        .select("grade, status, semester, COURSE(credit_hour)")\
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

#edit student course details
@router.put("/update/StudentCourse/{student_id}/{course_code}", response_model=list[UpdateStudentCourse])
async def edit_student_course(student_id:UUID, course_code:str, studentcourse_data: UpdateStudentCourse ):
    data = studentcourse_data.model_dump(exclude_unset=True)

    response = SUPABASE.table("STUDENT_COURSE").update(data).eq("student_id",student_id).eq("course_code",course_code).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Student courses not found")
    
    return response.data
#delete entire semester
@router.delete("/delete/semester/{student_id}/{semester}" ,response_model=SemesterRemove)
async def delete_semester(student_id:UUID, semester: int):
    

    response = SUPABASE.table("STUDENT_COURSE").delete().eq("student_id",student_id).eq("semester", semester).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Student not found")
    
    return {"message": f"Semester {semester} successfully deleted"}

#delete course in student_course table
@router.delete("/delete/course/{student_id}/{course_code}", response_model=SemesterRemove)
async def delete_student_coursecode(student_id:UUID, course_code:str):
    

    response = SUPABASE.table("STUDENT_COURSE").delete().eq("student_id",student_id).eq("course_code", course_code).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Student not found")
    
    return {"message": f"Course {course_code} successfully deleted"}