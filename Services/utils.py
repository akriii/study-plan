from passlib.context import CryptContext
from Database.database import SUPABASE
from math import ceil
from datetime import date, timedelta

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

def Calc_Cgpa(completed_count: list):
    """Calculates CGPA across all semesters."""
    points, credits = calculate_points_and_credits(completed_count)
    return round(points / credits, 2) if credits > 0 else 0.00

def Get_Probation_Status(student_id: str, target_semester: str):
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

def calculate_got_details(intake_date: date, total_failed_credits: int, probation_count: int, total_degree_credits: int, completed_credits: int):
    # 1. Constants and UTP Standards
    NORMAL_CAPACITY = 15
    PROBATION_CAPACITY = 11
    TOTAL_SEMS = 12
    INTERN_SEMS = 2
    INTERN_CREDITS = 14  # 7 credits x 2 semesters
    STUDY_SEMS = TOTAL_SEMS - INTERN_SEMS  # 10 study semesters

    # 2. Track Timeline
    today = date.today()
    start_month, start_year = intake_date.month, intake_date.year
    months_passed = (today.year - start_year) * 12 + (today.month - start_month)
    sems_passed = min(TOTAL_SEMS, months_passed // 4)
    
    # 3. Calculate 'Academic Work' Left
    # We subtract intern credits from the total degree credits because they are handled separately
    # Work left = (Remaining study credits) + (Credits from failed subjects to retake)
    study_credits_needed = (total_degree_credits - INTERN_CREDITS - (completed_credits if completed_credits < (total_degree_credits - INTERN_CREDITS) else (total_degree_credits - INTERN_CREDITS))) + total_failed_credits

    # 4. Calculate Available Study Capacity
    # Remaining study semesters = Total study sems - (Study sems already passed)
    # (Assuming the student isn't currently in an internship semester)
    remaining_study_sems = max(0, STUDY_SEMS - min(STUDY_SEMS, sems_passed))
    
    # Every past probation semester "stole" 4 credits of capacity from the 150-credit study bucket
    probation_penalty = probation_count * (NORMAL_CAPACITY - PROBATION_CAPACITY)
    
    # Total available slots left in the standard 10 study semesters
    available_study_slots = (remaining_study_sems * NORMAL_CAPACITY) - probation_penalty

    # 5. Determine Extension (The 'Overflow' Logic)
    if study_credits_needed > available_study_slots:
        overflow_credits = study_credits_needed - available_study_slots
        # Exceeding capacity by even 1 credit hour adds a semester
        extra_semesters = ceil(overflow_credits / NORMAL_CAPACITY)
    else:
        extra_semesters = 0

    # 6. Final Results
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
        "meta": {
            "study_credits_remaining": study_credits_needed,
            "study_capacity_left": available_study_slots,
            "intern_credits_handled": INTERN_CREDITS
        }
    }