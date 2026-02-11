from pydantic import BaseModel, EmailStr, Field
from datetime import date
from typing import Optional, Any, Union, Dict
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
    student_department: Optional[str] = None
    
class StudentCalcGOT(BaseModel):
    intake_session: Optional[Any]

class StudentRead(BaseModel):
    student_id: Optional[UUID]
    student_email: Optional[EmailStr]
    student_name: Optional[str]
    student_image: Optional[str] = None
    student_GOT: Optional[date] = None
    intake_session: Optional[date] = None
    student_department: Optional[str] = None
    deferment_normal: Optional[int] = 0
    deferment_medical: Optional[int] = 0
    
class AcademicMeta(BaseModel):
    is_probation: bool
    max_limit: int
    current_semester: str
    status_label: str

class Summary(BaseModel):
    count_completed_course: int
    count_current_course: int
    count_planned_course: int
    student_cgpa: float
    semester_credits: dict[str, int]
    academic_meta: AcademicMeta 

class SemesterSummary(BaseModel):
    total_credits: int
    status_counts: Dict[str, int]


class Gpa(BaseModel):
    semester: int
    gpa: Optional[float]

class StudentUpdate(BaseModel):
    student_image: Optional[str] = None
    student_name: Optional[str] = None
    intake_session: Optional[Union[date, str]] = None
    student_department: Optional[str] = None
    deferment_normal: Optional[int] = 0
    deferment_medical: Optional[int] = 0

class StudentRemove(BaseModel):
    student_id: UUID
    student_name: str 
    student_email: Optional[EmailStr]
    student_password: str 
    student_image: Optional[str] = None
    student_GOT: Optional[date] = None
    student_department: Optional[str] = None
    deferment_normal: Optional[int] = 0
    deferment_medical: Optional[int] = 0
    
class StudentCourseAdd(BaseModel):
    student_id: UUID
    course_code: str = ""
    semester: int
    grade: Optional[str] = ""
    status: Optional[str] = "Null"

class CourseRead(BaseModel):
    course_name: Optional[str] 
    course_code: Optional[str] 
    course_semester: Optional[str] = None
    course_desc: Optional[str] = None
    credit_hour: Optional[float] = 0.0 
    pre_requisite: Optional[Union[list[str], str]] = []
    course_department: Optional[Union[list[str], str]] = []
    
class ReadSemesterCourse(BaseModel):
    semester: Optional[int] 
    course_code: Optional[str] = None
    student_id: Optional[UUID]
    grade: Optional[str] = None
    status: Optional[str] = None
    COURSE: Optional[CourseRead] = None

class UpdateStudentCourse(BaseModel):
    course_code: Optional[str]
    grade: Optional[str]
    status: Optional[str]
    semester: Optional[int]

class SemesterRemove(BaseModel):
    message:str

class CourseCreate(BaseModel):
    course_name: str  
    course_code: str  
    course_semester: Optional[str] = None
    course_desc: Optional[str] = None
    course_type: str  
    credit_hour: float = 0.0
    pre_requisite: Optional[Union[list[str], str]] = []
    course_department: Optional[Union[list[str], str]] = []