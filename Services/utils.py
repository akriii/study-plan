from passlib.context import CryptContext
from Database.database import SUPABASE

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
    Returns (is_probation, credit_limit)
    """
    # Define the chronological order of your semesters
    # Adjust this list to match exactly how they are named in your database
    semester_order = ["1", "2", "3", "4", "5", "6", "7", "Student Industrial Internship Programme", "8", "9", "10"]

    # If the current semester isn't in our list or is the first one, no probation check needed
    if target_semester not in semester_order or target_semester == semester_order[0]:
        return False, 15

    # Find the index of the current semester and get the one before it
    current_index = semester_order.index(target_semester)
    prev_sem = semester_order[current_index - 1]

    # Query Supabase using the string value for prev_sem
    response = SUPABASE.table("STUDENT_COURSE") \
        .select("*, COURSE(credit_hour)") \
        .eq("student_id", student_id) \
        .eq("semester", prev_sem) \
        .eq("status", "Completed") \
        .execute()

    if not response.data:
        return False, 15 

    gpa = Calc_Gpa(response.data)
    
    # Check if GPA is below 2.00
    if gpa < 2.00:
        return True, 11  # Probation Limit
    return False, 15   # Normal Limit