from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# --- Auth & User Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    name: str

class TokenData(BaseModel):
    roll_no: Optional[str] = None
    role: Optional[str] = None


class UserBase(BaseModel):
    roll_no: str
    name: str
    role: str = Field(..., description="Must be 'student', 'prof', or 'admin'")
    email: Optional[str] = None
    subject: Optional[str] = None
    metadata: Optional[dict] = None # NEW: Holds DNN baseline features

class UserCreate(UserBase):
    password: str

class UserInDB(UserBase):
    hashed_password: str

# --- Attendance Schemas ---
class AttendanceRecord(BaseModel):
    roll_no: str
    subject: Optional[str] = None  # <-- CHANGED TO OPTIONAL
    status: str 

class AttendanceBulkUpdate(BaseModel):
    records: List[AttendanceRecord]

# --- Student Schemas ---
class StudentGoalLog(BaseModel):
    date: str
    subject: str # NEW
    study_hours: float
    expected_grade: str
    daily_goal: str
    weekly_goal: str
    monthly_goal: str
    daily_review: Optional[str] = None

class AdminOverrideAttendance(BaseModel):
    roll_no: str
    subject: str # NEW
    date: str
    status: str

# ... (keep other schemas)

class AcademicRecord(BaseModel):
    roll_no: str
    subject: Optional[str] = None
    mst1_marks: float
    mst2_marks: float
    finals_marks: float # This is G3
    absences: int
    failures: int
    studytime: int
    attendance_percent: Optional[float] = 0.0
    last_updated: Optional[datetime] = None

class ClassConfig(BaseModel):
    subject: str
    max_mst1: float = 20.0
    max_mst2: float = 20.0
    max_finals: float = 60.0

class AdminOverrideMarks(BaseModel):
    roll_no: str
    subject: str
    mst1_marks: float
    mst2_marks: float
    finals_marks: float

class WhatIfRequest(BaseModel):
    subject: str
    current_mst1: float
    current_mst2: float
    target_grade: str