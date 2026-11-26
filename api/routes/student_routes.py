from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from api.database import get_db
from api.auth import get_current_student
from api.schemas import StudentGoalLog, WhatIfRequest

router = APIRouter(prefix="/api/student", tags=["Student Operations"])

@router.get("/dashboard/{subject}")
async def get_student_dashboard(subject: str, db=Depends(get_db), student=Depends(get_current_student)):
    rno = student["roll_no"]
    acad = db.academics.find_one({"roll_no": rno, "subject": subject}, {"_id": 0})
    
    # Get total classes held (global across the system)
    all_class_dates = db.attendance.distinct("date", {"subject": subject})
    total = len(all_class_dates)
    
    present = db.attendance.count_documents({"roll_no": rno, "subject": subject, "status": "Present"})
    leaves = db.attendance.count_documents({"roll_no": rno, "subject": subject, "status": "Leave"})
    absent = max(0, total - present - leaves)
    att_percent = ((present + leaves) / total * 100) if total > 0 else 100.0
    
    return {
        "academics": acad,
        "attendance": {"total_classes": total, "present": present, "absent": absent, "leaves": leaves, "percentage": round(att_percent, 1)},
        "metadata": student.get("metadata", {}) # NEW: Return metadata
    }
@router.post("/goals")
async def save_student_goal(goal: StudentGoalLog, db=Depends(get_db), student=Depends(get_current_student)):
    goal_dict = goal.model_dump()
    goal_dict["roll_no"] = student["roll_no"]
    goal_dict["timestamp"] = datetime.utcnow()
    
    db.goals.update_one(
        {"roll_no": student["roll_no"], "date": goal.date, "subject": goal.subject},
        {"$set": goal_dict}, upsert=True
    )
    return {"message": "Goal log saved successfully."}

@router.get("/goals/{subject}")
async def get_student_goals(subject: str, db=Depends(get_db), student=Depends(get_current_student)):
    goals = list(db.goals.find({"roll_no": student["roll_no"], "subject": subject}, {"_id": 0}).sort("date", -1).limit(7))
    return goals

@router.post("/what-if")
async def calculate_what_if(req: WhatIfRequest, db=Depends(get_db), student=Depends(get_current_student)):
    grade_map = {"O": 80, "A+": 70, "A": 60, "B+": 55, "B": 50, "C": 45, "P": 40, "F": 0}
    target_total = grade_map[req.target_grade]
    
    config = db.config.find_one({"subject": req.subject}, {"_id": 0}) or {"max_mst1": 20.0, "max_mst2": 20.0, "max_finals": 60.0}
    max_total = config["max_mst1"] + config["max_mst2"] + config["max_finals"]
    
    # Scale target out of class max
    scaled_target = (target_total / 100.0) * max_total
    
    current_total = req.current_mst1 + req.current_mst2
    required_finals = scaled_target - current_total
    
    if required_finals <= 0:
        msg = f"You have already secured enough marks in MSTs to achieve a {req.target_grade}!"
    elif required_finals > config["max_finals"]:
        msg = f"It is mathematically impossible to get a {req.target_grade} (Requires {required_finals:.1f})."
    else:
        msg = f"You need {round(required_finals, 1)} / {config['max_finals']} in Finals to get a {req.target_grade}."
        
    return {"message": msg}

@router.get("/config/{subject}")
async def get_subject_config_public(subject: str, db=Depends(get_db), student=Depends(get_current_student)):
    config = db.config.find_one({"subject": subject}, {"_id": 0})
    # If the prof hasn't set a config yet, return the default 30/70
    return config if config else {"subject": subject, "max_mst": 30.0, "max_finals": 70.0}