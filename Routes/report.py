from fastapi import FastAPI,APIRouter, HTTPException
from Database.database import SUPABASE
from uuid import UUID
from Services.utils import Calc_Cgpa, Calc_Gpa

router = APIRouter()


@router.get("/report-data/{student_id}")
async def get_report_data(student_id: UUID):
    student = SUPABASE.table("STUDENT").select("student_email, student_name, intake_session").eq("student_id", student_id).single().execute()
    
    courses_res = SUPABASE.table("STUDENT_COURSE")\
        .select("*, COURSE(course_name, course_code, credit_hour)")\
        .eq("student_id", student_id).execute()
    
    data = courses_res.data
    
    report_structure = {}
    all_completed = []
    
    for record in data:
        sem = record["semester"]
        if sem not in report_structure:
            report_structure[sem] = {"courses": [], "total_credits": 0, "gpa": 0.0}
        
        report_structure[sem]["courses"].append(record)
        report_structure[sem]["total_credits"] += record["COURSE"]["credit_hour"]
        
        if record["status"] == "Completed":
            all_completed.append(record)

    for sem, details in report_structure.items():
        sem_completed = [c for c in details["courses"] if c["status"] == "Completed"]
        details["gpa"] = Calc_Gpa(sem_completed)

    return {
        "student_info": student.data,
        "academic_record": report_structure,
        "final_cgpa": Calc_Cgpa(all_completed),
        "total_credits_accumulated": sum(d["total_credits"] for d in report_structure.values())
    }