import os
import joblib
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from tensorflow.keras.models import load_model
from api.auth import get_current_user

router = APIRouter(prefix="/api/predict", tags=["Predictions"])

MODEL_PATH = "models/baxter_dnn.keras"
PREPROCESSOR_PATH = "models/baxter_preprocessor.pkl"

model = None
preprocessor = None

def load_artifacts():
    global model, preprocessor
    if model is None:
        if not os.path.exists(MODEL_PATH) or not os.path.exists(PREPROCESSOR_PATH):
            raise HTTPException(status_code=500, detail="Model artifacts missing. Run training first.")
        model = load_model(MODEL_PATH)
        preprocessor = joblib.load(PREPROCESSOR_PATH)

# These exactly match the columns used in ml_engine/preprocess.py
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
    
    # Convert input to DataFrame
    input_df = pd.DataFrame([data.model_dump()])
    
    try:
        # Preprocess
        X_processed = preprocessor.transform(input_df)
        
        # Predict
        prob = float(model.predict(X_processed, verbose=0)[0][0])
        pred_class = "Pass" if prob >= 0.5 else "Fail"
        
        return {
            "prediction": pred_class,
            "probability": prob,
            "risk_level": "High" if prob < 0.4 else ("Medium" if prob < 0.6 else "Low")
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))