from fastapi import FastAPI,APIRouter, HTTPException
from Database.database import SUPABASE
from Model.models import  CourseRead, Summary, StudentCourseAdd, ReadSemesterCourse, UpdateStudentCourse, SemesterRemove
from Services.utils import Calc_Cgpa, CountInProgress

router = APIRouter()
@router.get("/get/{student_id}/{course_code}", response_model=list[CourseRead]) #@router is a sub mdodule of FastAPI to handle routes
async def read_student_course(student_id:str, course_code:str):
    response = SUPABASE.table("STUDENT_COURSE").select("*").eq("student_id",student_id).eq("course_code",course_code).execute()
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
    
    if course.grade == "F":
        raise HTTPException(status_code=400, detail="Cannot enroll with a failing grade")
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
@router.get("/Completed/{student_id}", response_model=list[CourseRead]) #use list because it returns multiple items of student course
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
#get list of course taken by each semester
@router.get("/get/SemesterCourse/{student_id}/{semester}", response_model=list[ReadSemesterCourse])
async def get_semester_course(student_id: str, semester: int):
    response = SUPABASE.table("STUDENT_COURSE") \
    .select("*, COURSE(course_name, credit_hours, course_type)")  \
    .eq("student_id", student_id) \
    .eq("semester", semester) \
    .execute()
    if not response.data:
        return []
    return response.data

#edit student course details
@router.put("/update/StudentCourse/{student_id}/{course_code}", response_model=list[UpdateStudentCourse])
async def edit_student_course(student_id:str, course_code:int, studentcourse_data: UpdateStudentCourse ):
    data = studentcourse_data.model_dump(exclude_unset=True)

    response = SUPABASE.table("STUDENT_COURSE").update(data).eq("student_id",student_id).eq("course_code",course_code).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Student courses not found")
    
    return response.data
#delete entire semester
@router.delete("/delete/{student_id}/{semester}" ,response_model=SemesterRemove)
async def delete_semester(student_id:str, semester: int):
    

    response = SUPABASE.table("STUDENT_COURSE").delete().eq("student_id",student_id).eq("semester", semester).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Student not found")
    
    return {"message": f"Semester {semester} successfully deleted"}

#delete course based on semester
@router.delete("/delete/{student_id}/{semester}/{course_code}", response_model=SemesterRemove)
async def delete_semester_course(student_id:str, course_code:str, semester: int):
    

    response = SUPABASE.table("STUDENT_COURSE").delete().eq("student_id",student_id).eq("course_code", course_code).eq("semester",semester).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Student not found")
    
    return {"message": f"Course {course_code} from semester {semester} successfully deleted"}