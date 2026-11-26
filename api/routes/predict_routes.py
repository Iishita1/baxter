import os
import joblib
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from tensorflow.keras.models import load_model
from api.auth import get_current_user

router = APIRouter(prefix="/api/predict", tags=["Predictions"])

MODEL_PATH = "models/baxter_dnn.keras"
REG_MODEL_PATH = "models/baxter_dnn_regression.keras"
PREPROCESSOR_PATH = "models/baxter_preprocessor.pkl"

model = None
reg_model = None
preprocessor = None

def load_artifacts():
    global model, reg_model, preprocessor
    if model is None:
        if not os.path.exists(MODEL_PATH) or not os.path.exists(PREPROCESSOR_PATH):
            raise HTTPException(status_code=500, detail="Model artifacts missing.")
        model = load_model(MODEL_PATH)
        if os.path.exists(REG_MODEL_PATH):
            reg_model = load_model(REG_MODEL_PATH)
        preprocessor = joblib.load(PREPROCESSOR_PATH)

class StudentData(BaseModel):
    age: int
    absences: int
    failures: int
    Medu: int
    Fedu: int
    famrel: int
    freetime: int
    goout: int
    Dalc: int
    Walc: int
    health: int
    G1: int
    G2: int
    school: str
    sex: str
    address: str
    famsize: str
    Pstatus: str
    Mjob: str
    Fjob: str
    reason: str
    guardian: str
    schoolsup: str
    famsup: str
    paid: str
    activities: str
    nursery: str
    higher: str
    internet: str
    romantic: str

@router.post("/")
def predict_performance(data: StudentData, current_user: dict = Depends(get_current_user)):
    load_artifacts()
    
    input_df = pd.DataFrame([data.model_dump()])
    
    try:
        X_processed = preprocessor.transform(input_df)
        
        # 1. Classification Prediction (Pass/Fail Risk)
        prob = float(model.predict(X_processed, verbose=0)[0][0])
        pred_class = "Pass" if prob >= 0.5 else "Fail"
        risk_level = "High" if prob < 0.4 else ("Medium" if prob < 0.6 else "Low")
        
        # 2. Regression Prediction (Exact G3 Score out of 20)
        predicted_score = None
        if reg_model is not None:
            predicted_score = float(reg_model.predict(X_processed, verbose=0)[0][0])
            # Clip the score to valid 0-20 bounds
            predicted_score = max(0.0, min(20.0, predicted_score))
        
        return {
            "prediction": pred_class,
            "probability": prob,
            "risk_level": risk_level,
            "predicted_score": round(predicted_score, 1) if predicted_score is not None else None
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))