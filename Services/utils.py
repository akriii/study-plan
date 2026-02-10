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
        
        course_info = item.get("COURSE", {}) # Get credit hour from nested COURSE join
        credits = course_info.get("credit_hour", 0) #based on nested COURSE join, we get credit hour
        
        raw_grade = item.get("grade")

        # Convert to points
        if isinstance(raw_grade, str):
            quality_points = GRADE_MAP.get(raw_grade.upper().strip(), 0.00) #map the grade taken based on GRADE_MAP
        else:
            quality_points = raw_grade if raw_grade is not None else 0.00

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
    semester_order = ["1", "2", "3", "4", "5", "6", "7", "Student Industrial Internship Programme", "8", "9", "10"]

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



def calculate_got_details(intake_date: date, all_student_courses: list, probation_count: int, total_degree_credits: int):
    # 1. Constants and UTP Standards
    NORMAL_CAPACITY = 15
    PROBATION_CAPACITY = 11
    TOTAL_SEMS = 12
    INTERN_SEMS = 2
    INTERN_CREDITS = 14  # 7 credits x 2 semesters
    STUDY_SEMS = TOTAL_SEMS - INTERN_SEMS  # 10 study semesters

    # 2. Analyze Course History for Retakes
    history = {}
    for c in all_student_courses:
        code = c.get("course_code")
        if code not in history: 
            history[code] = []
        history[code].append(c)

    total_failed_credits = 0
    completed_credits = 0

    for code, attempts in history.items():
        # Sort by semester descending (latest first)
        attempts.sort(key=lambda x: int(x.get("semester", 0)), reverse=True)
        latest = attempts[0]
        
        # Check if they have EVER passed this subject
        has_passed = any(a.get("status") == "Completed" and a.get("grade") not in ["F", "Fail", None] for a in attempts)
        
        credits = latest.get("COURSE", {}).get("credit_hour", 0)
        
        if has_passed:
            completed_credits += credits
        elif latest.get("grade") == "F":
            # Only count as debt if the latest attempt is still a fail
            total_failed_credits += credits

    # 3. Track Timeline
    today = date.today()
    start_month, start_year = intake_date.month, intake_date.year
    months_passed = (today.year - start_year) * 12 + (today.month - start_month)
    sems_passed = min(TOTAL_SEMS, months_passed // 4)
    
    # 4. Calculate 'Academic Work' Left
    # Work left = (Core credits not yet passed) + (Unresolved failures)
    study_credits_needed = (total_degree_credits - INTERN_CREDITS - 
                            min(completed_credits, total_degree_credits - INTERN_CREDITS)) + total_failed_credits

    # 5. Calculate Capacity
    remaining_study_sems = max(0, STUDY_SEMS - min(STUDY_SEMS, sems_passed))
    # Every probation semester reduces capacity by 4 credits
    probation_penalty = probation_count * (NORMAL_CAPACITY - PROBATION_CAPACITY)
    available_study_slots = (remaining_study_sems * NORMAL_CAPACITY) - probation_penalty

    # 6. Determine Extension
    if study_credits_needed > available_study_slots:
        overflow_credits = study_credits_needed - available_study_slots
        extra_semesters = ceil(overflow_credits / NORMAL_CAPACITY)
    else:
        extra_semesters = 0

    # 7. Final Results
    total_duration_sems = TOTAL_SEMS + extra_semesters
    total_months = total_duration_sems * 4
    
    end_total_months = start_month + total_months - 1
    end_month = (end_total_months % 12) + 1
    end_year = start_year + (end_total_months // 12)
    
    percentage = (months_passed / total_months) * 100 if total_months > 0 else 0
    percentage = max(0, min(100, round(percentage, 2)))

    month_names = {1: "Jan", 5: "May", 9: "Sept"}

    return {
        "graduate_on_time_date": f"{month_names.get(end_month, 'Unknown')} {end_year}",
        "progress_percentage": percentage,
        "extra_semesters": extra_semesters,
        "is_delayed": extra_semesters > 0,
        "meta": {
            "study_credits_remaining": study_credits_needed,
            "study_capacity_left": available_study_slots,
            "unresolved_failed_credits": total_failed_credits,
            "completed_study_credits": completed_credits
        }
    }