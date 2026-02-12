from passlib.context import CryptContext
from Database.database import SUPABASE
from math import ceil
from datetime import date, timedelta
from uuid import UUID

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
    Checks the GPA of the semester immediately preceding target_semester.
    Probation is only applied if the previous semester is FULLY COMPLETED with GPA < 2.00.
    """

    target_sem_str = str(target_semester)
    semester_order = ["1", "2", "3", "4", "5", "6", "7", "Student Industrial Internship Programme", "Student Industrial Internship Programme","8", "9", "10"]

    if target_sem_str not in semester_order or target_sem_str == semester_order[0]:
        return False, 15

    current_index = semester_order.index(target_sem_str)
    prev_sem = semester_order[current_index - 1]

    # Fetch courses from the previous semester
    response = SUPABASE.table("STUDENT_COURSE") \
        .select("*, COURSE(credit_hour)") \
        .eq("student_id", student_id) \
        .eq("semester", prev_sem) \
        .execute()

    if not response.data:
        return False, 15 

    # If any course in the previous semester is NOT 'Completed', we don't apply probation yet.
    is_prev_sem_finalized = all(record.get("status") == "Completed" for record in response.data)

    if not is_prev_sem_finalized:
        return False, 15

    gpa = Calc_Gpa(response.data)
    
    if gpa < 2.00:
        return True, 11  
    
    return False, 15   



def calculate_got_details(
    intake_date: date, 
    all_student_courses: list, 
    probation_count: int, 
    total_degree_credits: int,
    defer_normal: int = 0,    # New Parameter
    defer_medical: int = 0    # New Parameter
):
    # 1. Constants and UTP Standards
    NORMAL_CAPACITY = 15
    PROBATION_CAPACITY = 11
    TOTAL_SEMS_BASE = 12
    RESIDENCY_MAX_LIMIT = 21  # The "Hard Limit"
    INTERN_CREDITS = 14
    STUDY_SEMS = 10 

    # 2. Analyze Course History for Retakes
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

    # 3. Track Timeline & Account for Deferment
    today = date.today()
    start_month, start_year = intake_date.month, intake_date.year
    months_passed = (today.year - start_year) * 12 + (today.month - start_month)
    
    # Total semesters used so far includes actual study time plus all deferments
    total_sems_passed = months_passed // 4
    
    # 4. Calculate 'Academic Work' Left
    study_credits_needed = (total_degree_credits - INTERN_CREDITS - 
                            min(completed_credits, total_degree_credits - INTERN_CREDITS)) + total_failed_credits

    # 5. Calculate Capacity
    # We only have 10 study semesters to work with.
    remaining_study_sems = max(0, STUDY_SEMS - (total_sems_passed - defer_normal - defer_medical))
    probation_penalty = probation_count * (NORMAL_CAPACITY - PROBATION_CAPACITY)
    available_study_slots = (remaining_study_sems * NORMAL_CAPACITY) - probation_penalty

    # 6. Determine Extension
    extra_semesters = ceil(max(0, study_credits_needed - available_study_slots) / NORMAL_CAPACITY)

    # 7. Residency Validation (The 21-Sem Rule)
    # residency_count = Base(12) + academic_extensions + normal_deferment
    # Medical deferment does NOT count toward this limit
    total_residency_sems = TOTAL_SEMS_BASE + extra_semesters + defer_normal

    if total_residency_sems > RESIDENCY_MAX_LIMIT:
        return {
            "is_valid_degree": False,
            "message": f"Degree Invalid: Total semesters ({total_residency_sems}) exceeds the 21-semester limit due to excessive deferment/delays.",
            "total_semesters": total_residency_sems
        }

    # 8. Final Results (Expected Grad Date)
    # The actual date includes BOTH types of deferment
    total_duration_sems = TOTAL_SEMS_BASE + extra_semesters + defer_normal + defer_medical
    total_months = total_duration_sems * 4
    
    end_total_months = start_month + total_months - 1
    end_month = (end_total_months % 12) + 1
    end_year = start_year + (end_total_months // 12)
    
    percentage = (months_passed / total_months) * 100 if total_months > 0 else 0
    month_names = {1: "Jan", 5: "May", 9: "Sept"}

    return {
        "is_valid_degree": True,
        "graduate_on_time_date": f"{month_names.get(end_month, 'Unknown')} {end_year}",
        "progress_percentage": max(0, min(100, round(percentage, 2))),
        "extra_semesters_needed": extra_semesters,
        "total_deferment_taken": defer_normal + defer_medical,
        "residency_count": total_residency_sems,
        "meta": {
            "deferment_normal": defer_normal,
            "deferment_medical": defer_medical,
            "study_credits_remaining": study_credits_needed
        }
    }