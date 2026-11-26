import streamlit as st
import pandas as pd
import io
from app.api_client import get_mlflow_runs, predict_student, download_feedback_csv

def render():
    st.markdown("<h2 style='margin-bottom: 0;'>Experiment Lab</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #a0a0b0;'>Monitor MLflow training runs and test the DNN model.</p>", unsafe_allow_html=True)
    st.write("")
    
    token = st.session_state.token
    tab1, tab2, tab3 = st.tabs(["📊 MLflow Runs", "🧠 Test Prediction", "🔄 Continuous Feedback"])
    
    # ==========================================
    # TAB 1: MLflow Runs
    # ==========================================
    with tab1:
        with st.container(border=True):
            st.markdown("### Model Comparison")
            if st.button("🔄 Refresh Runs"):
                st.rerun()
                
            runs = get_mlflow_runs(token)
            if not runs:
                st.info("No runs found. Ensure MLflow is running.")
            else:
                data = []
                for r in runs:
                    metrics = r.get("metrics", {})
                    
                    # Safely extract metrics (fallback to '-' if not found)
                    acc = metrics.get("test_accuracy", metrics.get("accuracy", "-"))
                    f1 = metrics.get("test_f1_score", metrics.get("f1_score", "-"))
                    mae = metrics.get("test_mae", metrics.get("mae", "-"))
                    
                    # Round floats for display
                    acc = round(acc, 4) if isinstance(acc, float) else acc
                    f1 = round(f1, 4) if isinstance(f1, float) else f1
                    mae = round(mae, 4) if isinstance(mae, float) else mae
                    
                    data.append({
                        "Run Name": r.get("run_name"),
                        "Status": r.get("status"),
                        "Accuracy (Class)": acc,
                        "F1 Score (Class)": f1,
                        "MAE (Reg)": mae,  # NEW COLUMN for Regression
                        "Model Type": r.get("params", {}).get("model_type", "DNN")
                    })
                    
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True)
            
    # ==========================================
    # TAB 2: Test Prediction
    # ==========================================
    with tab2:
        with st.container(border=True):
            st.markdown("### Test the DNN Prediction")
            st.write("Enter student details to see the model's prediction.")
            
            with st.form("test_predict_form"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    G1 = st.number_input("G1 (0-20)", 0, 20, 10)
                    G2 = st.number_input("G2 (0-20)", 0, 20, 10)
                    absences = st.number_input("Absences", 0, 50, 0)
                with col2:
                    age = st.number_input("Age", 15, 22, 17)
                    failures = st.slider("Past Failures", 0, 4, 0)
                    Medu = st.slider("Mother Edu", 0, 4, 2)
                with col3:
                    Fedu = st.slider("Father Edu", 0, 4, 2)
                    goout = st.slider("Go out (1-5)", 1, 5, 3)
                    Dalc = st.slider("Workday Alcohol", 1, 5, 1)
                
                submit = st.form_submit_button("Predict Risk & Score")
                
                if submit:
                    payload = {
                        "age": age, "absences": absences, "failures": failures, "Medu": Medu, "Fedu": Fedu, 
                        "famrel": 4, "freetime": 3, "goout": goout, "Dalc": Dalc, "Walc": 2, "health": 3,
                        "G1": G1, "G2": G2, "school": "GP", "sex": "F", "address": "U", "famsize": "GT3", 
                        "Pstatus": "T", "Mjob": "at_home", "Fjob": "teacher", "reason": "course",
                        "guardian": "mother", "schoolsup": "no", "famsup": "yes", "paid": "no", 
                        "activities": "yes", "nursery": "yes", "higher": "yes", "internet": "yes", "romantic": "no"
                    }
                    res = predict_student(token, payload)
                    if res.status_code == 200:
                        result = res.json()
                        
                        st.markdown("#### Results")
                        c1, c2 = st.columns(2)
                        
                        with c1:
                            if result["prediction"] == "Pass": 
                                st.success(f"**Classification: PASS** (Prob: {result['probability']:.2%})")
                            else: 
                                st.error(f"**Classification: FAIL** (Prob: {1-result['probability']:.2%})")
                                
                        with c2:
                            if result.get("predicted_score") is not None:
                                st.info(f"**Regression: Expected Score {result['predicted_score']} / 20**")
                    else:
                        st.error(f"Error: {res.json().get('detail')}")

    # ==========================================
    # TAB 3: Continuous Feedback
    # ==========================================
    with tab3:
        with st.container(border=True):
            st.markdown("### Live Model Feedback (Continuous Learning)")
            st.write("This section shows how the deployed DNN is performing on actual student outcomes.")
            
            res = download_feedback_csv(token)
            if res.status_code == 200:
                st.download_button("📥 Download Live Feedback CSV", data=res.content, file_name="baxter_feedback_data.csv", mime="text/csv")
                df = pd.read_csv(io.StringIO(res.content.decode('utf-8')))
                if not df.empty:
                    accuracy = (df['is_correct'].sum() / len(df)) * 100
                    st.metric("Live Accuracy on New Data", f"{accuracy:.1f}%")
                    st.dataframe(df.head(10), use_container_width=True)
            else:
                st.info("No feedback data logged yet. Update marks in Prof view to generate data.")