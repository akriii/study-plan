from passlib.context import CryptContext



pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
def HashPassword(password:str):
    safe_password = password[:72] #72 bytes of password hashed only
    return pwd_context.hash(safe_password)

def VerifyPassword(plain_password:str, hashed_password:str):
    return pwd_context.verify(plain_password,hashed_password)

def CountCourses(course_list:list):
    count = len(course_list)
    return count

def Calc_Cgpa(courses: list):
    total_credits = sum(course["credit_hour"] for course in courses)
    total_grade = sum(course["student_grade"]for course in courses)
    cgpa = total_grade / total_credits

    return cgpa
