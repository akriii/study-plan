from passlib.context import CryptContext
from Database.database import SUPABASE
from math import ceil
from datetime import date, timedelta
from uuid import UUID
import os
import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

router = APIRouter()
security = HTTPBasic()

def authenticate_admin(credentials: HTTPBasicCredentials = Depends(security)):
    """
    Checks the pop-up credentials against the Master Admin info.
   
    """
    # 1. Fetch the master admin info from Render Env
    correct_username = os.getenv("ADMIN_USER")
    correct_password = os.getenv("ADMIN_PASS")

    # 2. Securely compare the strings to prevent 'timing attacks'
    is_user_ok = secrets.compare_digest(credentials.username, str(correct_username))
    is_pass_ok = secrets.compare_digest(credentials.password, str(correct_password))

    if not (is_user_ok and is_pass_ok):
        # 3. This specific error + header triggers the browser pop-up
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized Access",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
def HashPassword(password:str):
    safe_password = password[:72] #72 bytes of password hashed only
    return pwd_context.hash(safe_password)

def VerifyPassword(plain_password:str, hashed_password:str):
    return pwd_context.verify(plain_password,hashed_password)


def calculate_points_and_credits(courses: list):
    """Calculates total grade points and credits for a given list of courses."""
    GRADE_MAP = {
        "A": 4.00, "A-": 3.75, "B+": 3.50, "B": 3.00,
        "C+": 2.50, "C": 2.00, "D+": 1.50, "D": 1.00, "F": 0.00
    }

    total_credits = 0
    total_grade_points = 0

    for item in courses:
        # Get credit hour from nested COURSE join
        course_info = item.get("COURSE") or {}
        credits = item.get("credit_hour") or course_info.get("credit_hour", 0)
        
        raw_grade = item.get("grade")

        # --- FIXED LOGIC ---
        # 1. If it's a non-empty string, check the GRADE_MAP
        if isinstance(raw_grade, str) and raw_grade.strip():
            quality_points = GRADE_MAP.get(raw_grade.upper().strip(), 0.00)
        # 2. If it's an empty string or None, it's 0.00 points
        elif raw_grade == "" or raw_grade is None:
            quality_points = 0.00
        # 3. Otherwise, try converting to float (for numeric grades)
        else:
            try:
                quality_points = float(raw_grade)
            except (ValueError, TypeError):
                quality_points = 0.00
        # -------------------

        
        total_credits += credits
        total_grade_points += (quality_points * credits)
            
    return total_grade_points, total_credits
    
def Calc_Gpa(courses: list):
    """Calculates GPA for a specific set of courses (e.g., one semester)."""
    points, credits = calculate_points_and_credits(courses)
    return round(points / credits, 2) if credits > 0 else 0.00

def Calc_Cgpa(completed_list: list):
    """
    Calculates CGPA across all semesters, ensuring only the latest attempt 
    of a repeated course is counted.
    """
    if not completed_list:
        return 0.00

    # 1. Group by course_code to find all attempts
    latest_attempts = {}
    for record in completed_list:
        code = record.get("course_code")
        # Ensure semester is treated as an integer for comparison
        sem = int(record.get("semester", 0))
        
        if code not in latest_attempts or sem > int(latest_attempts[code].get("semester", 0)):
            latest_attempts[code] = record

    # 2. Extract only the latest unique attempts
    unique_latest_courses = list(latest_attempts.values())

    # 3. Standard calculation using your existing utility
    points, credits = calculate_points_and_credits(unique_latest_courses)
    return round(points / credits, 2) if credits > 0 else 0.00

def Get_Probation_Status(student_id: UUID, target_semester: str):
    """
    Checks the GPA of the semester logically preceding target_semester.
    Works for any department or semester naming convention.
    """
    # 1. Fetch all unique semesters this student has records for
    all_sems_query = SUPABASE.table("STUDENT_COURSE") \
        .select("semester") \
        .eq("student_id", student_id) \
        .execute()
    
    if not all_sems_query.data:
        return False, 15

    # 2. Create a sorted unique list of semesters
    # We use a helper to ensure "Internship" comes after "7" but before "8"
    def sem_sorter(sem):
        try:
            return float(sem) # Numeric sems (1, 2, 3...)
        except ValueError:
            return 7.5 # Place text-based internship between 7 and 8

    unique_sems = sorted(list(set(str(r['semester']) for r in all_sems_query.data)), key=sem_sorter)

    # 3. Identify the previous semester
    target_sem_str = str(target_semester)
    if target_sem_str not in unique_sems or target_sem_str == unique_sems[0]:
        return False, 15

    current_index = unique_sems.index(target_sem_str)
    prev_sem = unique_sems[current_index - 1]

    # 4. Fetch and Calculate GPA for that specific previous semester
    # NOTE: Use .eq("semester", prev_sem) directly if the DB column is text. 
    # If DB is smallint, use int(prev_sem) inside a try/except.
    response = SUPABASE.table("STUDENT_COURSE") \
        .select("*, COURSE(credit_hour)") \
        .eq("student_id", student_id) \
        .eq("semester", prev_sem) \
        .execute()

    if not response.data or not all(r.get("status") == "Completed" for r in response.data):
        return False, 15

    gpa = Calc_Gpa(response.data)
    return (True, 11) if gpa < 2.00 else (False, 15)

def calculate_got_details(
    intake_date: date, 
    all_student_courses: list, 
    probation_count: int, 
    total_degree_credits: int,
    defer_normal: int = 0,    
    defer_medical: int = 0    
):
    # 1. Constants
    NORMAL_CAPACITY = 15
    PROBATION_CAPACITY = 11
    TOTAL_SEMS_BASE = 12 # Standard 4-year duration
    RESIDENCY_MAX_LIMIT = 21 # Hard University Limit
    INTERN_CREDITS = 14
    STUDY_SEMS_TOTAL = 10 # 12 total - 2 internship

    # 2. Analyze Course History
    history = {}
    for c in all_student_courses:
        code = c.get("course_code")
        if code:
            if code not in history: history[code] = []
            history[code].append(c)

    total_failed_credits = 0
    completed_credits = 0

    for code, attempts in history.items():
        attempts.sort(key=lambda x: int(x.get("semester", 0)), reverse=True)
        latest = attempts[0]
        has_passed = any(a.get("status") == "Completed" and a.get("grade") not in ["F", "Fail", None] for a in attempts)
        
        course_info = latest.get("COURSE") or {}
        credits = latest.get("credit_hour") or course_info.get("credit_hour", 0)
        
        if has_passed:
            completed_credits += credits
        elif latest.get("grade") == "F":
            total_failed_credits += credits

    # 3. Calculate "Total Study Semesters" Needed
    # We calculate how many semesters it takes to finish the WHOLE degree
    total_targeted_study_credits = total_degree_credits - INTERN_CREDITS
    
    # Probation reduces efficiency. We treat it as "Lost Credit Slots"
    probation_penalty_credits = probation_count * (NORMAL_CAPACITY - PROBATION_CAPACITY)
    
    # Total semesters needed = (Required Credits + Penalty) / Capacity
    total_study_sems_needed = ceil((total_targeted_study_credits + total_failed_credits + probation_penalty_credits) / NORMAL_CAPACITY)
    
    # 4. Determine Extensions
    # Academic extension is only if they need more than the standard 10 study semesters
    extra_semesters = max(0, total_study_sems_needed - STUDY_SEMS_TOTAL)

    # 5. Residency Validation (The 21-Sem Rule)
    # Residency = Standard Base (12) + Extensions + Normal Deferment
    total_residency_sems = TOTAL_SEMS_BASE + extra_semesters + defer_normal

    if total_residency_sems > RESIDENCY_MAX_LIMIT:
        return {
            "is_valid_degree": False,
            "message": f"Degree Invalid: Estimated residency ({total_residency_sems} sems) exceeds the 21-semester limit.",
            "total_semesters": total_residency_sems
        }

    # 6. Final Results & Graduation Date
    today = date.today()
    months_passed = (today.year - intake_date.year) * 12 + (today.month - intake_date.month)
    
    # Graduation duration includes medical deferment as well
    total_duration_sems = TOTAL_SEMS_BASE + extra_semesters + defer_normal + defer_medical
    total_months_duration = total_duration_sems * 4
    
    end_total_months = intake_date.month + total_months_duration - 1
    end_month_raw = (end_total_months - 1) % 12 + 1
    end_year = intake_date.year + (end_total_months - 1) // 12
    
    # Align to UTP Months
    if end_month_raw <= 4: final_month = 1
    elif end_month_raw <= 8: final_month = 5
    else: final_month = 9

    month_names = {1: "Jan", 5: "May", 9: "Sept"}
    progress = (months_passed / total_months_duration) * 100 if total_months_duration > 0 else 0

    return {
        "is_valid_degree": True,
        "graduate_on_time_date": f"{month_names[final_month]} {end_year}",
        "progress_percentage": max(0, min(100, round(progress, 2))),
        "current_semester_count": (months_passed // 4) + 1,
        "total_semesters_expected": total_duration_sems,
        "residency_count": total_residency_sems,
        "meta": {
            "extra_semesters": extra_semesters,
            "completed_credits": completed_credits,
            "failed_credits": total_failed_credits
        }
    }

