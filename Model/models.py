from pydantic import BaseModel, EmailStr, Field
from datetime import date
from typing import Optional, Any, Union
from uuid import UUID


class StudentLogin(BaseModel):
    student_email: EmailStr
    student_password: str

class StudentCreate(BaseModel):
    student_name: str 
    student_email: EmailStr
    student_password: str 
    student_image: Optional[str] = None
    student_GOT: Optional[Any] = None
    
class StudentCalcGOT(BaseModel):
    intake_session: Optional[Any]

class StudentRead(BaseModel):
    student_id: Optional[UUID]
    student_email: Optional[EmailStr]
    student_name: Optional[str]
    student_image: Optional[str] = None
    student_GOT: Optional[date] = None
    intake_session: Optional[date] = None
    
class Summary(BaseModel):
    count_completed_course: Optional[int]
    count_current_course: Optional[int]
    count_planned_course: Optional[int]
    student_cgpa: Optional[float]
    
   
class Gpa(BaseModel):
    semester: int
    gpa: Optional[float]

class StudentUpdate(BaseModel):
    student_image: Optional[str] = None
    student_name: Optional[str] = None
    intake_session: Optional[Union[date, str]] = None

class StudentRemove(BaseModel):
    student_id: UUID
    student_name: str 
    student_email: Optional[EmailStr]
    student_password: str 
    student_image: Optional[str] = None
    student_GOT: Optional[date] = None
    
class StudentCourseAdd(BaseModel):
    student_id: UUID
    course_code: str = ""
    semester: int
    grade: Optional[str] = ""
    status: Optional[str] = "Null"

class CourseRead(BaseModel):
    course_name: Optional[str] 
    course_code: Optional[str] 
    credit_hour: Optional[float] = 0.0 
    pre_requisite: Optional[list[str]] = []
    
class ReadSemesterCourse(BaseModel):
    semester: Optional[int]
    course_code: Optional[str]
    student_id: Optional[UUID]
    grade: Optional[str]
    status: Optional[str]
    COURSE: Optional[CourseRead] = None

class UpdateStudentCourse(BaseModel):
    course_code: Optional[str]
    grade: Optional[str]
    status: Optional[str]
    semester: Optional[int]

class SemesterRemove(BaseModel):
    message:str