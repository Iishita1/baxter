import pandas as pd
import streamlit as st
from app.api_client import get_mlflow_runs, predict_student, download_feedback_csv, get_audit_logs # get_audit_logs to fetch feedback

def render():
    st.title("🧪 Experiment Lab")
    st.write("Monitor MLflow training runs and test the DNN model.")
    
    token = st.session_state.token
    tab1, tab2, tab3 = st.tabs(["📊 MLflow Runs", "🧠 Test Prediction", "🔄 Continuous Feedback"])
    
    # --- TAB 1: MLflow Runs ---
    with tab1:
        st.subheader("Model Comparison")
        if st.button("🔄 Refresh Runs"):
            st.rerun()
            
        runs = get_mlflow_runs(token)
        
        if not runs:
            st.info("No runs found. Make sure MLflow is running and a model has been trained.")
        else:
            data = []
            for r in runs:
                data.append({
                    "Run Name": r.get("run_name"),
                    "Status": r.get("status"),
                    "Accuracy": r.get("metrics", {}).get("accuracy", r.get("metrics", {}).get("test_accuracy")),
                    "F1 Score": r.get("metrics", {}).get("f1_score", r.get("metrics", {}).get("test_f1_score")),
                    "Model Type": r.get("params", {}).get("model_type", "DNN")
                })
            
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
            
    # --- TAB 2: Test Prediction ---
    with tab2:
        st.subheader("Test the DNN Prediction")
        st.write("Enter student details to see the model's prediction.")
        
        with st.form("test_predict_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                G1 = st.number_input("G1 (0-20)", 0, 20, 10)
                G2 = st.number_input("G2 (0-20)", 0, 20, 10)
                absences = st.number_input("Absences", 0, 50, 0)
                age = st.number_input("Age", 15, 22, 17)
            with col2:
                failures = st.slider("Past Failures", 0, 4, 0)
                Medu = st.slider("Mother Edu (0-4)", 0, 4, 2)
                Fedu = st.slider("Father Edu (0-4)", 0, 4, 2)
                goout = st.slider("Go out (1-5)", 1, 5, 3)
            with col3:
                Dalc = st.slider("Workday Alcohol (1-5)", 1, 5, 1)
                Walc = st.slider("Weekend Alcohol (1-5)", 1, 5, 2)
                health = st.slider("Health (1-5)", 1, 5, 3)
            
            st.write("*(Using default values for remaining categorical features)*")
            submit = st.form_submit_button("Predict Risk")
            
            if submit:
                # We use defaults for the categorical features to keep the form short
                payload = {
                    "age": age, "absences": absences, "failures": failures,
                    "Medu": Medu, "Fedu": Fedu, "famrel": 4, "freetime": 3,
                    "goout": goout, "Dalc": Dalc, "Walc": Walc, "health": health,
                    "G1": G1, "G2": G2, "school": "GP", "sex": "F",
                    "address": "U", "famsize": "GT3", "Pstatus": "T",
                    "Mjob": "at_home", "Fjob": "teacher", "reason": "course",
                    "guardian": "mother", "schoolsup": "no", "famsup": "yes",
                    "paid": "no", "activities": "yes", "nursery": "yes",
                    "higher": "yes", "internet": "yes", "romantic": "no"
                }
                res = predict_student(token, payload)
                
                if res.status_code == 200:
                    result = res.json()
                    if result["prediction"] == "Pass":
                        st.success(f"**Prediction: PASS** (Probability: {result['probability']:.2%})")
                    else:
                        st.error(f"**Prediction: FAIL** (Probability: {1-result['probability']:.2%})")
                else:
                    st.error(f"Error: {res.json().get('detail')}")

    with tab3:
        st.subheader("Live Model Feedback (Continuous Learning)")
        st.write("This section shows how the deployed DNN is performing on actual student outcomes.")
        
        # In a real app, you'd have an endpoint to get this data as JSON.
        # For now, let's just use the Audit logs endpoint logic (or fetch it directly)
        # We'll use st.download_button to grab the CSV
        res = download_feedback_csv(token)
        
        if res.status_code == 200:
            st.success("Feedback data is available for download.")
            st.download_button(
                label="📥 Download Live Feedback CSV",
                data=res.content,
                file_name="baxter_feedback_data.csv",
                mime="text/csv",
                help="Download the log of predictions vs actual results to retrain the model."
            )
            
            # Display a quick preview (we can parse the CSV content)
            import io
            df = pd.read_csv(io.StringIO(res.content.decode('utf-8')))
            
            # Calculate live accuracy
            if not df.empty:
                accuracy = (df['is_correct'].sum() / len(df)) * 100
                st.metric("Live Accuracy on New Data", f"{accuracy:.1f}%")
                st.dataframe(df.head(10), use_container_width=True)
        else:
            st.info("No feedback data logged yet. Go to the Professor view, update some marks, and come back!")