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
        # Get credits from nested COURSE join
        course_info = item.get("COURSE", {})
        credits = course_info.get("credit_hour", 0)
        
        # Get letter grade
        raw_grade = item.get("grade")

        # Convert to points
        if isinstance(raw_grade, str):
            quality_points = GRADE_MAP.get(raw_grade.upper().strip(), 0.00)
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

