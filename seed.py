#seed.py is for adding course or updating course information to the database
#to update the course information in the database, make a change in Data/courses.json
#and then, in cmd, run cd backend, run python seed.py

from Database.database import SUPABASE
import os #for file manipulation and detection
import json

def seed_courses():
    file_path = os.path.join("Data","courses.json")

    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found")
        return

    try:
        with open(file_path, "r") as file:
            courses_data = json.load(file)
            
        print(f"Read {len(courses_data)} courses from JSON.")

        response = SUPABASE.table("COURSE").upsert( #insert and update all courses info into course table
            courses_data, 
            on_conflict="course_code"
        ).execute()

        print(f"Successfully synced {len(response.data)} courses to Supabase.")

    except Exception as e:
        print(f"An error occurred during seeding: {e}")

if __name__ == "__main__":
    seed_courses()