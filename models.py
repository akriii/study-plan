from pydantic import BaseModel, EmailStr, Field
from datetime import date
from typing import Optional

class StudentLogin(BaseModel):
    student_email: EmailStr
    student_password: str

class CourseCreate(BaseModel):
    course_name: str = Field(..., max_length=100)
    credit_hour: float
    student_grade: Optional[str] = "In Progress"
    course_code: str = Field(..., max_length=10)
    semester_id: int
    student_id: str
    prerequisite: str = Field(None, max_length=100)

class SemesterRead(BaseModel):
    semester_id: int
    semester_name: str 
    semester_gpa: float
    student_id: str

class StudentCreate(BaseModel):
    student_id: str
    student_name: str 
    student_email: EmailStr
    student_password: str 
    student_GOT: Optional[date] = None
    

class StudentRead(BaseModel):
    student_id: str
    student_email: EmailStr
    student_name: str
    student_image: Optional[str] = None
    student_GOT: Optional[date] = None
    
class CourseRead(BaseModel):
    course_id: str
    course_name: str 
    credit_hour: float
    student_grade: str 
    course_code: str = Field(..., max_length=10)
    semester_id: int
    student_id: str
    prerequisite: str 

class SemesterCreate(BaseModel):
    semester_id: str
    semester_name: str
    semester_gpa: str
    student_id:str

class Summary(BaseModel):
    
    count_course: int
    student_grade: float
   
class StudentUpdate(BaseModel):
    student_id: str
    student_image: str
    student_name: str

class StudentRemove(BaseModel):
    student_id: str
    student_name: str 
    student_email: EmailStr
    student_password: str 
    student_image: Optional[str] = None
    student_GOT: Optional[date] = None
    