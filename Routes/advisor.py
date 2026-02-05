from fastapi import APIRouter, HTTPException
from huggingface_hub import InferenceClient
from Database.database import SUPABASE
from uuid import UUID
import os

router = APIRouter()

# 1. Initialize with the official HF Router URL
# This ensures we use the "Conversational" task correctly
client = InferenceClient(
    base_url="https://router.huggingface.co/v1",
    api_key=os.getenv("HF_TOKEN")
)

@router.get("/ai-advisor/{student_id}")
async def get__advisor(student_id: UUID):
    try:
        # Fetch data
        db_res = SUPABASE.table("STUDENT_COURSE").select("*, COURSE(*)").eq("student_id", student_id).execute()

        if not db_res.data:
            return {"analysis": "No course records found. Please add subjects to start the analysis."}
        
        # 1. CLEAN DATA PREPARATION
        # We only send what's necessary to save tokens and keep AI focused
        transcript_summary = ""
        for record in db_res.data:
            course = record.get('COURSE', {})
            grade = record.get('grade') or "Not Graded"
            status = record.get('status', 'Unknown')
            
            transcript_summary += (
                f"- {course.get('course_name')} ({record.get('course_code')}): "
                f"Grade: {grade}, Status: {status}, Credit: {course.get('credit_hour')}, Pre-requiste: {course.get('pre_requisite')}\n"
            )

        # 2. THE "TASK-BASED" SYSTEM PROMPT
        system_instruction = (
            "You are a Senior Academic Advisor at UTP. Your goal is to provide a "
            "EXECUTIVE SUMMARY. Do not list every course individually. The paragraph can only contain around 100 to 200 words only.Instead, "
            "group your findings into three sections: \n"
            "1. Overall Academic Standing (One paragraph)\n"
            "2. Critical Priorities (Specific course code to focus on based on low grades or credit weight)\n"
            "3. Future Planning (Advice for 'Planned' course code and prerequisites)\n"
            "4. A 3-sentence motivational closing."
        )

        response = client.chat.completions.create(
            model="Qwen/Qwen2.5-7B-Instruct", 
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": f"Student Transcript Data:\n{transcript_summary}"}
            ],
            max_tokens=600,
            temperature=0.6 # Lower temperature makes it more professional and less creative
        )
        
        return {"analysis": response.choices[0].message.content}
        
    except Exception as e:
        print(f"HF ROUTER ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail="Advisor is currently offline.")
    
