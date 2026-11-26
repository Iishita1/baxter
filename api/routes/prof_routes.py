from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime, timezone, timedelta
from api.database import get_db
from api.auth import get_current_prof
from api.schemas import AcademicRecord, AttendanceBulkUpdate

router = APIRouter(prefix="/api/prof", tags=["Professor Operations"])

def get_prof_subject(prof):
    subj = prof.get("subject")
    if not subj:
        raise HTTPException(status_code=400, detail="Professor is not assigned to a subject by Admin.")
    return subj

@router.get("/students")
async def get_all_students(db=Depends(get_db), prof=Depends(get_current_prof)):
    subject = get_prof_subject(prof)
    students = list(db.users.find({"role": "student"}, {"_id": 0, "hashed_password": 0}))
    for student in students:
        record = db.academics.find_one({"roll_no": student["roll_no"], "subject": subject}, {"_id": 0})
        student["academics"] = record if record else None
    return students

# Replace your update_marks route:
@router.post("/marks")
async def update_marks(record: AcademicRecord, db=Depends(get_db), prof=Depends(get_current_prof)):
    subject = get_prof_subject(prof)
    record.subject = subject
    
    existing = db.academics.find_one({"roll_no": record.roll_no, "subject": subject})
    now = datetime.now(timezone.utc)
    
    if existing:
        last_updated = existing.get("last_updated")
        if last_updated:
            if last_updated.tzinfo is None:
                last_updated = last_updated.replace(tzinfo=timezone.utc)
            if now - last_updated > timedelta(hours=24):
                raise HTTPException(status_code=403, detail="24-hour limit exceeded.")
        db.academics.update_one({"roll_no": record.roll_no, "subject": subject}, {"$set": record.model_dump() | {"last_updated": now}})
    else:
        db.academics.insert_one(record.model_dump() | {"last_updated": now})
    return {"message": f"Marks for {record.roll_no} updated."}

# Update config routes:
@router.get("/config")
async def get_class_config(db=Depends(get_db), prof=Depends(get_current_prof)):
    subject = get_prof_subject(prof)
    config = db.config.find_one({"subject": subject}, {"_id": 0})
    return config if config else {"subject": subject, "max_mst1": 20.0, "max_mst2": 20.0, "max_finals": 60.0}

@router.get("/attendance/{date_str}")
async def get_attendance_register(date_str: str, db=Depends(get_db), prof=Depends(get_current_prof)):
    subject = get_prof_subject(prof)
    students = list(db.users.find({"role": "student"}, {"_id": 0, "hashed_password": 0}))
    
    existing_logs = list(db.attendance.find({"date": date_str, "subject": subject}, {"_id": 0}))
    log_map = {log["roll_no"]: log["status"] for log in existing_logs}
    
    all_class_dates = db.attendance.distinct("date", {"subject": subject})
    total_classes_held = len(all_class_dates)
    
    register = []
    for s in students:
        rno = s["roll_no"]
        present_count = db.attendance.count_documents({"roll_no": rno, "subject": subject, "status": "Present"})
        leave_count = db.attendance.count_documents({"roll_no": rno, "subject": subject, "status": "Leave"})
        absent_count = max(0, total_classes_held - present_count - leave_count)
        
        if total_classes_held > 0:
            att_percent = ((present_count + leave_count) / total_classes_held) * 100
        else:
            att_percent = 100.0
            
        register.append({
            "roll_no": rno, "name": s["name"], "status": log_map.get(rno, "Not Marked"),
            "total_classes": total_classes_held, "present": present_count,
            "absent": absent_count, "leaves": leave_count, "overall_attendance": round(att_percent, 1)
        })
    return register

@router.post("/attendance/{date_str}")
async def save_attendance_register(date_str: str, payload: AttendanceBulkUpdate, db=Depends(get_db), prof=Depends(get_current_prof)):
    subject = get_prof_subject(prof)
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format.")
        
    if datetime.now(timezone.utc) > target_date + timedelta(hours=48):
        raise HTTPException(status_code=403, detail="48-hour limit exceeded.")
        
    for record in payload.records:
        record.subject = subject # Force subject
        if record.status in ["Present", "Absent", "Leave"]:
            db.attendance.update_one(
                {"roll_no": record.roll_no, "date": date_str, "subject": subject},
                {"$set": {"status": record.status, "marked_by": prof["roll_no"]}},
                upsert=True
            )
        elif record.status == "Not Marked":
            db.attendance.delete_one({"roll_no": record.roll_no, "date": date_str, "subject": subject})
    return {"message": f"Attendance saved for {date_str} ({subject})"}

@router.post("/config")
async def update_class_config(config: dict, db=Depends(get_db), prof=Depends(get_current_prof)):
    subject = get_prof_subject(prof)
    config["subject"] = subject
    db.config.update_one({"subject": subject}, {"$set": config}, upsert=True)
    return {"message": "Configuration updated."}