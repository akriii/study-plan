from fastapi import FastAPI, HTTPException
from Database.database import SUPABASE
from Routes import student,course, student_course
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

#define origins that are allowed to make requests to this backend
origins = [
    "http://localhost:3000",  
    "http://127.0.0.1:3000",  
    "http://localhost:8000",  

]
#adding CORS middleware to handle cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(student.router, prefix="/student", tags=["student"]) #take every router from student.py and include it in main app
app.include_router(course.router, prefix="/course", tags=["course"]) #if i have routes like @router.get("/course") in course.py then it will be accessible at /course/course
app.include_router(student_course.router, prefix="/student_course", tags=["student_course"])

@app.get("/check") #@app is the main FastAPI instance which connects all routes (@router) together
def check_connection():
    try:
        
        SUPABASE.table("STUDENT").select("*").limit(1).execute() #simple query to check connection  
        
        return {"status": "Database connection successful"} 
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connection failed: {str(e)}")