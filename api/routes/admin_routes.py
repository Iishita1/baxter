from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from datetime import datetime, timezone
from api.database import get_db
from api.auth import get_current_admin, get_password_hash
from api.schemas import UserCreate, UserBase, AdminOverrideMarks, AdminOverrideAttendance

router = APIRouter(prefix="/api/admin", tags=["Admin Operations"])

def log_audit(db, admin_id, target_roll_no, action_type, old_value, new_value):
    """Helper function to write to the audit log."""
    db.audit_logs.insert_one({
        "admin_id": admin_id,
        "target_roll_no": target_roll_no,
        "action_type": action_type,
        "old_value": str(old_value),
        "new_value": str(new_value),
        "timestamp": datetime.now(timezone.utc)
    })

@router.get("/users")
async def get_all_users(db=Depends(get_db), admin=Depends(get_current_admin)):
    users = list(db.users.find({}, {"_id": 0, "hashed_password": 0}))
    return users

@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(new_user: UserCreate, db=Depends(get_db), admin=Depends(get_current_admin)):
    if db.users.find_one({"roll_no": new_user.roll_no}):
        raise HTTPException(status_code=400, detail="Roll number already registered")
    user_dict = new_user.model_dump()
    password = user_dict.pop("password")
    user_dict["hashed_password"] = get_password_hash(password)
    db.users.insert_one(user_dict)
    return {"message": f"User {new_user.roll_no} created successfully"}

@router.delete("/users/{roll_no}")
async def delete_user(roll_no: str, db=Depends(get_db), admin=Depends(get_current_admin)):
    if roll_no == admin["roll_no"]:
        raise HTTPException(status_code=400, detail="Cannot delete yourself.")
    result = db.users.delete_one({"roll_no": roll_no})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    # Clean up related data
    db.academics.delete_one({"roll_no": roll_no})
    db.attendance.delete_many({"roll_no": roll_no})
    return {"message": f"User {roll_no} and associated data deleted."}

@router.get("/audit-logs")
async def get_audit_logs(db=Depends(get_db), admin=Depends(get_current_admin)):
    # Get latest logs first
    logs = list(db.audit_logs.find({}, {"_id": 0}).sort("timestamp", -1))
    return logs

@router.post("/override/marks")
async def override_marks(payload: AdminOverrideMarks, db=Depends(get_db), admin=Depends(get_current_admin)):
    existing = db.academics.find_one({"roll_no": payload.roll_no})
    
    old_mst = existing.get("mst_marks", "None") if existing else "None"
    old_finals = existing.get("finals_marks", "None") if existing else "None"
    
    # Log the override
    log_audit(
        db, admin["roll_no"], payload.roll_no, "MARKS_OVERRIDE",
        f"MST: {old_mst}, Finals: {old_finals}",
        f"MST: {payload.mst_marks}, Finals: {payload.finals_marks}"
    )
    
    # Update database (bypassing the 24h check)
    db.academics.update_one(
        {"roll_no": payload.roll_no},
        {"$set": {
            "mst_marks": payload.mst_marks,
            "finals_marks": payload.finals_marks,
            "last_updated": datetime.now(timezone.utc)
        }},
        upsert=True
    )
    return {"message": f"Marks overridden for {payload.roll_no}"}

@router.post("/override/attendance")
async def override_attendance(payload: AdminOverrideAttendance, db=Depends(get_db), admin=Depends(get_current_admin)):
    existing = db.attendance.find_one({"roll_no": payload.roll_no, "date": payload.date})
    old_status = existing.get("status", "Not Marked") if existing else "Not Marked"
    
    log_audit(
        db, admin["roll_no"], payload.roll_no, "ATTENDANCE_OVERRIDE",
        f"{payload.date}: {old_status}",
        f"{payload.date}: {payload.status}"
    )
    
    db.attendance.update_one(
        {"roll_no": payload.roll_no, "date": payload.date},
        {"$set": {"status": payload.status, "marked_by": f"ADMIN-{admin['roll_no']}"}},
        upsert=True
    )
    return {"message": f"Attendance overridden for {payload.roll_no} on {payload.date}"}

# Add this to api/routes/admin_routes.py

@router.get("/summary")
async def get_system_summary(db=Depends(get_db), admin=Depends(get_current_admin)):
    total_students = db.users.count_documents({"role": "student"})
    total_profs = db.users.count_documents({"role": "prof"})
    total_overrides = db.audit_logs.count_documents({})
    
    # Calculate Average Attendance across all records
    pipeline = [
        {"$match": {"status": {"$in": ["Present", "Leave"]}}},
        {"$group": {"_id": None, "count": {"$sum": 1}}}
    ]
    # Note: For a real system, you'd calculate a proper percentage, 
    # but for the UI card, we'll just show total logs processed.
    total_attendance_logs = db.attendance.count_documents({})
    
    return {
        "students": total_students,
        "profs": total_profs,
        "overrides": total_overrides,
        "attendance_logs": total_attendance_logs
    }