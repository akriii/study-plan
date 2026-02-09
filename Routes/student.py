from fastapi import FastAPI,APIRouter, HTTPException, UploadFile, File
from Database.database import SUPABASE
from Model.models import StudentCreate, StudentRead,StudentLogin, StudentUpdate, StudentCalcGOT
from uuid import UUID
from fastapi.encoders import jsonable_encoder
from datetime import date, datetime
from dotenv import load_dotenv
from Services.utils import calculate_got_details
import os

load_dotenv()

BUCKET = os.getenv("SUPABASE_BUCKET")

router = APIRouter() #defining a router for student-related routes

#route to fetch student based on student id sent by react
@router.get("/{student_id}", response_model=StudentRead) #@router is a sub mdodule of FastAPI to handle routes
async def read_students(student_id:UUID):
    response = SUPABASE.table("STUDENT").select("*").eq("student_id",student_id).single().execute() #query for get all students data
    if not response.data:
        raise HTTPException(status_code=404, detail="Student not found")
        
    return response.data

@router.post("/register")
async def register_student(student: StudentCreate):
    try:
        auth_response = SUPABASE.auth.sign_up({
            "email": student.student_email,
            "password": student.student_password,
            
        })

        if not auth_response.user:
            raise HTTPException(
                status_code=400, 
                detail="Registration cannot be completed. If you already have an account, please check your email."
            )

        new_profile = {
            "student_id": auth_response.user.id, 
            "student_name": student.student_name,
            "student_email": student.student_email,
        }
        
        profile_response = SUPABASE.table("STUDENT").insert(new_profile).execute()
        
        if not profile_response.data:
             raise HTTPException(status_code=500, detail="User created but profile sync failed.")

        return {"message": "Success! Please check your email for a verification link."}

    except Exception as e:
        error_msg = str(e)
        if "User already registered" in error_msg:
             raise HTTPException(status_code=400, detail="This email is already taken.")
        
        raise HTTPException(status_code=400, detail=error_msg)

#update image to student table
@router.put("/upload-profile-image/{student_id}")
async def upload_student_image(student_id: UUID, file: UploadFile = File(...)):
    try:
        # 1. Read the image file content
        file_content = await file.read()
        
        # 2. Extract extension and create a standardized path
        # Using student_id as the filename ensures each user has only one file
        file_extension = file.filename.split(".")[-1]
        file_path = f"profiles/{student_id}.{file_extension}"
        
        # 3. Upload to Supabase Storage with 'upsert=True'
        # This replaces the existing file if it exists at that path
        storage_response = SUPABASE.storage.from_(BUCKET).upload(
            path=file_path,
            file=file_content,
            file_options={
                "content-type": file.content_type,
                "x-upsert": "true"  # Crucial for updating existing files
            }
        )

        # 4. Generate the Public URL
        # Ensure the bucket is set to 'Public' in Supabase dashboard
        image_url = SUPABASE.storage.from_(BUCKET).get_public_url(file_path)

        # 5. Update only the student_image column in the STUDENT table
        db_response = SUPABASE.table("STUDENT")\
            .update({"student_image": image_url})\
            .eq("student_id", student_id)\
            .execute()

        if not db_response.data:
            raise HTTPException(status_code=404, detail="Student record not found")

        return {
            "status": "success",
            "message": "Profile image updated",
            "student_image_url": image_url
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image upload failed: {str(e)}")

# Route for student login
@router.post("/login")
async def login_student(student: StudentLogin):
    try:
        auth_response = SUPABASE.auth.sign_in_with_password({
            "email": student.student_email,
            "password": student.student_password,
        })

        if not auth_response.user:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        profile_query = SUPABASE.table("STUDENT")\
            .select("student_id, student_name")\
            .eq("student_id", auth_response.user.id)\
            .single()\
            .execute()

        if not profile_query.data:
            raise HTTPException(status_code=404, detail="Student profile not found")

        user_record = profile_query.data

        return {
            "message": "Login successful",
            "student_name": user_record["student_name"],
            "student_id": user_record["student_id"]
        }

    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid email or password")

#route for update all student information
@router.put("/update/{student_id}" ,response_model=StudentUpdate)
async def update_student(student_id:UUID, student_data:StudentUpdate):
    data = student_data.model_dump(exclude_unset=True)

    response = SUPABASE.table("STUDENT").update(data).eq("student_id",student_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Student not found")
    
    return response.data[0]

#route for delete student id
@router.delete("/delete/{student_id}")
async def delete_student(student_id:UUID):
    

    response = SUPABASE.table("STUDENT").delete().eq("student_id",student_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Student not found")
    
    return {"message": f"Student {student_id} successfully deleted"}


@router.get("/get/graduate-on-time/{student_id}")
async def get_student_got_status(student_id: UUID):
    # 1. Get Intake Date
    student_query = SUPABASE.table("STUDENT")\
        .select("intake_session")\
        .eq("student_id", student_id)\
        .maybe_single().execute()
    
    if not student_query.data or not student_query.data.get("intake_session"):
        raise HTTPException(status_code=404, detail="Intake session date missing.")

    intake_date = date.fromisoformat(student_query.data["intake_session"])

    # 2. Sum Unresolved Failed Credits
    failed_courses = SUPABASE.table("STUDENT_COURSE")\
        .select("COURSE(credit_hour)")\
        .eq("student_id", student_id)\
        .eq("grade", "F")\
        .execute()
    
    total_failed_credits = sum(
        item.get("COURSE", {}).get("credit_hour", 0) 
        for item in failed_courses.data if item.get("COURSE")
    )

    # 3. Get Analysis with Percentage
    analysis = calculate_got_details(intake_date, total_failed_credits)

    return {
        "success": True,
        "analysis": analysis
    }