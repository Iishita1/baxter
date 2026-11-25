from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
import io
import csv
from datetime import datetime, timezone
from pydantic import BaseModel
from api.database import get_db
from api.auth import get_current_prof, get_current_admin
# Import the DNN and preprocessor from your predict_routes
from api.routes.predict_routes import load_artifacts, model, preprocessor
import pandas as pd

router = APIRouter(prefix="/api/feedback", tags=["Feedback Loop"])

class EvaluateRequest(BaseModel):
    roll_no: str
    subject: str
    mst_marks: float
    finals_marks: float
    max_mst: float
    max_finals: float
    metadata: dict = {}

@router.post("/evaluate")
async def evaluate_and_log(data: EvaluateRequest, db=Depends(get_db), prof=Depends(get_current_prof)):
    load_artifacts() # Ensure model is loaded
    
    # 1. Prepare DNN Payload
    g1 = (data.mst_marks / data.max_mst) * 20 if data.max_mst > 0 else 0
    g2 = (data.finals_marks / data.max_finals) * 20 if data.max_finals > 0 else 0
    
    payload = {
        "age": 17, "absences": 0, "failures": 0, "Medu": 2, "Fedu": 2,
        "famrel": 4, "freetime": 3, "goout": 3, "Dalc": 1, "Walc": 2, "health": 3,
        "school": "GP", "sex": "F", "address": "U", "famsize": "GT3", "Pstatus": "T",
        "Mjob": "at_home", "Fjob": "teacher", "reason": "course", "guardian": "mother",
        "schoolsup": "no", "famsup": "yes", "paid": "no", "activities": "yes",
        "nursery": "yes", "higher": "yes", "internet": "yes", "romantic": "no",
        "G1": int(g1), "G2": int(g2)
    }
    
    # Override with student metadata if available
    for k, v in data.metadata.items():
        if k in payload:
            payload[k] = v
            
    input_df = pd.DataFrame([payload])
    X_processed = preprocessor.transform(input_df)
    
    # 2. DNN Prediction
    prob = float(model.predict(X_processed, verbose=0)[0][0])
    predicted_class = "Pass" if prob >= 0.5 else "Fail"
    
    # 3. Actual Result (Passing is >= 40% total)
    total_marks = data.mst_marks + data.finals_marks
    max_total = data.max_mst + data.max_finals
    actual_percentage = (total_marks / max_total * 100) if max_total > 0 else 0
    actual_class = "Pass" if actual_percentage >= 40.0 else "Fail"
    
    # 4. Log to MongoDB
    feedback_record = {
        "timestamp": datetime.now(timezone.utc),
        "roll_no": data.roll_no,
        "subject": data.subject,
        "mst": data.mst_marks,
        "finals": data.finals_marks,
        "total_percentage": round(actual_percentage, 1),
        "predicted_prob": round(prob, 4),
        "predicted_class": predicted_class,
        "actual_class": actual_class,
        "is_correct": predicted_class == actual_class
    }
    
    # Upsert (update if existing, insert if new)
    db.feedback_logs.update_one(
        {"roll_no": data.roll_no, "subject": data.subject},
        {"$set": feedback_record},
        upsert=True
    )
    
    return {"message": "Feedback logged successfully", "record": feedback_record}

@router.get("/export")
async def export_feedback_csv(db=Depends(get_db), admin=Depends(get_current_admin)):
    logs = list(db.feedback_logs.find({}, {"_id": 0}).sort("timestamp", -1))
    
    if not logs:
        return {"message": "No feedback data available yet."}
        
    # Convert to CSV
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=logs[0].keys())
    writer.writeheader()
    writer.writerows(logs)
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]), 
        media_type="text/csv", 
        headers={"Content-Disposition": "attachment; filename=baxter_feedback_data.csv"}
    )