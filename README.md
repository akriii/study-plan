# 🎓 UTP Civil Engineering Study Planner



A smart academic management system specifically engineered for UTP Civil & Enviromental Engineering students. This platform automates the complex task of degree planning by integrating real-time university policies, prerequisite tracking, and automated academic reporting.

---

## 🌟 Key Features

### 🧠 Intelligent Academic Engine
* **Dynamic Probation Logic**: Automatically calculates academic standing based on finalized results. If a student's GPA drops below **2.00**, the system restricts the next semester to an **11-credit hour limit**.
* **Soft-Block Prerequisites**: Instead of hiding courses, the system flags them. If a prerequisite is missing or failed, the student is notified that **Chair Department Approval** is required.
* **Smart Status Tracking**: Differentiates between *Planned*, *Current*, and *Completed* courses to provide a realistic roadmap toward graduation.

### 🔐 Modern Authentication & Security
* **Google OAuth 2.0 Integration**: Single-click signup and login using official UTP Webmail.
* **Automated Profile Sync**: Utilizes a PostgreSQL `SECURITY DEFINER` trigger to instantly synchronize Google metadata (Full Name, Email, and Avatar) to the public student table.
* **Granular Security (RLS)**: Implements Row-Level Security at the database level to ensure students can only access their own private academic data.

### 📊 Professional Reporting
* **PDF Report Generation**: One-click generation of academic summaries including semester-wise GPA, Cumulative GPA (CGPA), and total credit hour accumulation.
* **Visual Dashboard**: A clean interface for monitoring degree progress at a glance.

---

## 🛠️ Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Frontend** | React.js (Hooks & Router), Tailwind CSS |
| **Backend** | FastAPI (Python 3.13), Pydantic V2 |
| **Database** | Supabase (PostgreSQL 15) |
| **Auth** | Supabase Auth (OAuth 2.0) |
| **PDF Engine** | @react-pdf/renderer |

---

## 🏗️ System Architecture

The system follows a decoupled architecture designed for high availability and security:
1. **Client**: React handles the user interface and local session state.
2. **API**: FastAPI processes business logic, such as GPA calculations and prerequisite normalization.
3. **Database**: Supabase manages data persistence, automated triggers, and Row-Level Security policies.



---

## 🚀 Installation & Setup

### 1. Backend (FastAPI)
```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload