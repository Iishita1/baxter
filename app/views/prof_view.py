import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
from app.api_client import (get_all_students_prof, update_student_marks, 
                            predict_student, get_attendance_register, 
                            save_attendance_register, get_class_config, 
                            update_class_config, evaluate_and_log_feedback)

def get_ai_insights(token, student, academics, max_mst1, max_mst2, max_finals):
    """Helper to call the DNN for both Risk Classification and Score Regression."""
    if not academics or academics.get("mst1_marks") is None:
        return "No Data", "-"
        
    # 1. Map dynamic marks to the UCI 0-20 scale (G1 and G2)
    g1 = (academics.get("mst1_marks", 0) / max_mst1) * 20 if max_mst1 > 0 else 0
    g2 = (academics.get("mst2_marks", 0) / max_mst2) * 20 if max_mst2 > 0 else 0
    
    # 2. Start with default fallback data
    payload = {
        "age": 17, "absences": 0, "failures": 0, "Medu": 2, "Fedu": 2,
        "famrel": 4, "freetime": 3, "goout": 3, "Dalc": 1, "Walc": 2, "health": 3,
        "school": "GP", "sex": "F", "address": "U", "famsize": "GT3", "Pstatus": "T",
        "Mjob": "at_home", "Fjob": "teacher", "reason": "course", "guardian": "mother",
        "schoolsup": "no", "famsup": "yes", "paid": "no", "activities": "yes",
        "nursery": "yes", "higher": "yes", "internet": "yes", "romantic": "no"
    }
    
    # 3. Override with uploaded metadata (Admin's static data)
    if student.get("metadata"):
        for k, v in student["metadata"].items():
            if k in payload:
                payload[k] = v
                
    # 4. Override with live academic data (Prof's dynamic data)
    payload["G1"] = int(g1)
    payload["G2"] = int(g2)
    payload["absences"] = academics.get("absences", payload.get("absences", 0))
    
    res = predict_student(token, payload)
    if res.status_code == 200:
        data = res.json()
        risk = data.get("risk_level", "Unknown")
        
        # FIX: Scale the 0-20 prediction to the max_finals scale
        raw_score = data.get("predicted_score")
        if raw_score is not None and max_finals > 0:
            scaled_score = round((raw_score / 20.0) * max_finals, 1)
        else:
            scaled_score = "-"
            
        return risk, scaled_score
    return "Error", "-"

def render():
    # --- Header ---
    st.markdown("<h2 style='margin-bottom: 0;'>Professor Dashboard</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #a0a0b0;'>Monitor class performance and manage academic records.</p>", unsafe_allow_html=True)
    st.write("")
    
    token = st.session_state.token
    
    # Fetch dynamic config for the Professor's subject
    config = get_class_config(token)
    max_mst1 = float(config.get("max_mst1", 20.0))
    max_mst2 = float(config.get("max_mst2", 20.0))
    max_finals = float(config.get("max_finals", 60.0))
    subject = config.get("subject", "General")
    
    # Load students
    students = get_all_students_prof(token)
    
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Class Overview", "📝 Update Marks", "🗓️ Attendance", "⚙️ Settings"])
    
    # ==========================================
    # TAB 1: Class Overview
    # ==========================================
    with tab1:
        st.subheader(f"Class Performance ({subject})")
        if not students:
            st.info("No students found in the system.")
        else:
            table_data = []
            for s in students:
                acad = s.get("academics") or {}
                risk, pred_score = get_ai_insights(token, s, acad, max_mst1, max_mst2, max_finals)
                
                table_data.append({
                    "Roll No": s["roll_no"],
                    "Name": s["name"],
                    f"MST1 ({max_mst1})": acad.get("mst1_marks", 0.0),
                    f"MST2 ({max_mst2})": acad.get("mst2_marks", 0.0),
                    f"Finals ({max_finals})": acad.get("finals_marks", 0.0),
                    "Attendance %": f"{acad.get('attendance_percent', 0):.1f}%",
                    "AI Risk (Classification)": risk,
                    "AI Expected Score (Regression)": pred_score
                })
                
            df = pd.DataFrame(table_data)
            
            # Plotly Bar Chart for AI Expected Score
            if not df.empty:
                with st.container(border=True):
                    # Create a copy for plotting to safely handle the "-" values
                    df_plot = df.copy()
                    df_plot["AI Expected Score (Regression)"] = pd.to_numeric(
                        df_plot["AI Expected Score (Regression)"], errors='coerce'
                    ).fillna(0)
                    
                    fig = px.bar(
                        df_plot, 
                        x="Name", 
                        y="AI Expected Score (Regression)", 
                        title=f"AI Predicted Final Scores (Regression Model) out of {max_finals}", 
                        template="plotly_dark", 
                        color="AI Expected Score (Regression)", 
                        color_continuous_scale="Purples"
                    )
                    # FIX: Set the Y-axis max to the Professor's configured max_finals
                    fig.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)', 
                        plot_bgcolor='rgba(0,0,0,0)', 
                        margin=dict(t=40, b=0, l=0, r=0),
                        yaxis=dict(range=[0, max_finals]) 
                    )
                    st.plotly_chart(fig, use_container_width=True)

            # Data Table with Highlighting
            with st.container(border=True):
                st.markdown("### Student Risk Analysis")
                def highlight_risk(row):
                    if row["AI Risk (Classification)"] == "High":
                        return ['background-color: rgba(239, 68, 68, 0.2)'] * len(row) # Subtle red
                    elif row["AI Risk (Classification)"] == "Medium":
                        return ['background-color: rgba(245, 158, 11, 0.2)'] * len(row) # Subtle orange
                    return [''] * len(row)
                    
                st.dataframe(df.style.apply(highlight_risk, axis=1), use_container_width=True)
            
    # ==========================================
    # TAB 2: Update Marks
    # ==========================================
    with tab2:
        st.subheader("Update Student Marks")
        st.info("⚠️ Marks can only be updated within 24 hours of the first entry.")
        
        if students:
            # Search Bar + Dropdown
            col_search, col_drop = st.columns([2, 3])
            with col_search:
                search_query = st.text_input("🔍 Search by Name or Roll No", placeholder="e.g. John or 2410")
            with col_drop:
                filtered_students = [
                    s for s in students 
                    if search_query.lower() in s['name'].lower() or search_query in s['roll_no']
                ] if search_query else students
                
                if not filtered_students:
                    st.warning("No students match your search.")
                    selected_student_key = None
                else:
                    student_options = {f"{s['name']} ({s['roll_no']})": s for s in filtered_students}
                    selected_student_key = st.selectbox("Select Student", options=list(student_options.keys()))
            
            if selected_student_key:
                selected_student = student_options[selected_student_key]
                acad = selected_student.get("academics") or {}
                
                with st.container(border=True):
                    st.markdown(f"### Marks Entry: {selected_student['name']}")
                    with st.form("update_marks_form"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            mst1 = st.number_input(f"MST1 (out of {max_mst1})", 0.0, max_mst1, float(acad.get("mst1_marks", 0.0)))
                        with col2:
                            mst2 = st.number_input(f"MST2 (out of {max_mst2})", 0.0, max_mst2, float(acad.get("mst2_marks", 0.0)))
                        with col3:
                            finals = st.number_input(f"Finals (out of {max_finals})", 0.0, max_finals, float(acad.get("finals_marks", 0.0)))
                            
                        st.divider()
                        col_abs, col_fail, col_study = st.columns(3)
                        with col_abs:
                            absences = st.number_input("Total Absences", 0, 100, int(acad.get("absences", 0)))
                        with col_fail:
                            failures = st.number_input("Past Failures", 0, 4, int(acad.get("failures", 0)))
                        with col_study:
                            studytime = st.slider("Study Time (1-4)", 1, 4, int(acad.get("studytime", 2)))
                        
                        submit = st.form_submit_button("Save Marks & Run AI Feedback", use_container_width=True)
                        
                        if submit:
                            payload = {
                                "roll_no": selected_student["roll_no"],
                                "mst1_marks": mst1,
                                "mst2_marks": mst2,
                                "finals_marks": finals,
                                "absences": absences,
                                "failures": failures,
                                "studytime": studytime,
                                "attendance_percent": float(acad.get("attendance_percent", 100.0))
                            }
                            res = update_student_marks(token, payload)
                            
                            if res.status_code == 200:
                                # Trigger Continuous Feedback Loop (Logs G3 / Finals)
                                eval_payload = {
                                    "roll_no": selected_student["roll_no"],
                                    "subject": subject,
                                    "mst1_marks": mst1,
                                    "mst2_marks": mst2,
                                    "finals_marks": finals,
                                    "max_mst1": max_mst1,
                                    "max_mst2": max_mst2,
                                    "max_finals": max_finals,
                                    "metadata": selected_student.get("metadata", {})
                                }
                                evaluate_and_log_feedback(token, eval_payload)
                                
                                st.success("Marks updated and AI Feedback logged successfully!")
                                st.rerun()
                            else:
                                st.error(f"Error: {res.json().get('detail')}")
        else:
            st.warning("No students available.")

    # ==========================================
    # TAB 3: Attendance Register
    # ==========================================
    with tab3:
        st.subheader(f"Daily Attendance Register ({subject})")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            selected_date = st.date_input("Select Class Date", datetime.today())
            date_str = selected_date.strftime("%Y-%m-%d")
        
        with col2:
            st.write("") 
            st.write("")
            if selected_date < (datetime.today().date() - timedelta(days=2)):
                st.error("⚠️ This date is older than 48 hours. Editing is disabled (Admin override required).")
            
        register_data = get_attendance_register(token, date_str)
        
        if not register_data:
            st.info("No students found in the system.")
        else:
            with st.container(border=True):
                df = pd.DataFrame(register_data)
                df = df.rename(columns={
                    "roll_no": "Roll No", "name": "Name", "status": "Mark",
                    "total_classes": "Total", "present": "Present", "absent": "Absent",
                    "leaves": "Leaves", "overall_attendance": "Overall %"
                })
                
                edited_df = st.data_editor(
                    df[["Roll No", "Name", "Mark", "Total", "Present", "Absent", "Leaves", "Overall %"]],
                    column_config={
                        "Roll No": st.column_config.TextColumn(disabled=True),
                        "Name": st.column_config.TextColumn(disabled=True),
                        "Total": st.column_config.NumberColumn(disabled=True),
                        "Present": st.column_config.NumberColumn(disabled=True),
                        "Absent": st.column_config.NumberColumn(disabled=True),
                        "Leaves": st.column_config.NumberColumn(disabled=True),
                        "Overall %": st.column_config.NumberColumn(disabled=True, format="%.1f%%"),
                        "Mark": st.column_config.SelectboxColumn(
                            options=["Present", "Absent", "Leave", "Not Marked"], required=True
                        )
                    },
                    hide_index=True,
                    use_container_width=True
                )
                
                if st.button("Save Attendance", type="primary", use_container_width=True):
                    records = [{"roll_no": row["Roll No"], "status": row["Mark"]} for _, row in edited_df.iterrows()]
                    res = save_attendance_register(token, date_str, records)
                    if res.status_code == 200:
                        st.success(f"Attendance successfully saved for {date_str}!")
                        st.rerun()
                    else:
                        st.error(f"Error: {res.json().get('detail')}")

    # ==========================================
    # TAB 4: Settings
    # ==========================================
    with tab4:
        with st.container(border=True):
            st.subheader(f"Class Configuration ({subject})")
            st.write("Set the maximum marks for this subject. This updates calculations across the system.")
            with st.form("config_form"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    new_max_mst1 = st.number_input("Max MST1 Marks", 0.0, 100.0, float(max_mst1))
                with col2:
                    new_max_mst2 = st.number_input("Max MST2 Marks", 0.0, 100.0, float(max_mst2))
                with col3:
                    new_max_finals = st.number_input("Max Finals Marks", 0.0, 100.0, float(max_finals))
                    
                if st.form_submit_button("Save Configuration", use_container_width=True):
                    update_class_config(token, {"max_mst1": new_max_mst1, "max_mst2": new_max_mst2, "max_finals": new_max_finals})
                    st.success("Configuration saved! Refreshing...")
                    st.rerun()