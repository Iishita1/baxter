import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
from app.api_client import (get_all_students_prof, update_student_marks, 
                            predict_student, get_attendance_register, 
                            save_attendance_register, get_class_config, 
                            update_class_config, evaluate_and_log_feedback)

def get_dnn_risk(token, student, academics, max_mst, max_finals):
    """Helper to call the DNN for a student's risk level, merging static and dynamic data."""
    if not academics or academics.get("mst_marks") is None:
        return "No Data"
        
    # 1. Map dynamic marks to the UCI 0-20 scale
    g1 = (academics.get("mst_marks", 0) / max_mst) * 20 if max_mst > 0 else 0
    g2 = (academics.get("finals_marks", 0) / max_finals) * 20 if max_finals > 0 else 0
    
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
        return res.json().get("risk_level", "Unknown")
    return "Error"

def render():
    # --- Header ---
    st.markdown("<h1 style='margin: 0; padding-bottom: 0;'>Professor Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #a0a0b0; margin-top: 5px;'>Monitor class performance and manage academic records.</p>", unsafe_allow_html=True)
    
    token = st.session_state.token
    
    # Fetch dynamic config for the Professor's subject
    config = get_class_config(token)
    max_mst = float(config.get("max_mst", 30.0))
    max_finals = float(config.get("max_finals", 70.0))
    subject = config.get("subject", "General")
    
    # Load students
    students = get_all_students_prof(token)
    
        # ==========================================
    # TOP ROW: METRIC CARDS
    # ==========================================
    if students:
        # FIX: Use `or {}` to handle students who have no academic records yet
        avg_mst = sum([(s.get("academics") or {}).get("mst_marks", 0) for s in students]) / len(students)
        
        # Calculate high risk students
        high_risk_count = 0
        for s in students:
            # FIX: Use `or {}` here too
            acad = s.get("academics") or {}
            risk = get_dnn_risk(token, s, acad, max_mst, max_finals)
            if risk == "High":
                high_risk_count += 1
                
        col1, col2, col3 = st.columns(3)
        with col1:
            with st.container(border=True):
                st.metric("Total Students", len(students))
        with col2:
            with st.container(border=True):
                st.metric(f"Class Avg MST", f"{avg_mst:.1f} / {max_mst}")
        with col3:
            with st.container(border=True):
                st.metric("High Risk Students", high_risk_count, delta="Requires Attention", delta_color="inverse")
        
        st.write("") # Spacing

    # ==========================================
    # TABS
    # ==========================================
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Class Overview", "📝 Update Marks", "🗓️ Attendance", "⚙️ Settings"])
    
    # --- TAB 1: Class Overview ---
    with tab1:
        if not students:
            st.info("No students found in the system.")
        else:
            table_data = []
            for s in students:
                acad = s.get("academics") or {}
                risk = get_dnn_risk(token, s, acad, max_mst, max_finals)
                
                table_data.append({
                    "Roll No": s["roll_no"],
                    "Name": s["name"],
                    f"MST ({max_mst})": acad.get("mst_marks", 0.0),
                    f"Finals ({max_finals})": acad.get("finals_marks", 0.0),
                    "Attendance %": f"{acad.get('attendance_percent', 0):.1f}%",
                    "DNN Risk Level": risk
                })
                
            df = pd.DataFrame(table_data)
            
            col_chart, col_table = st.columns([1, 1.5])
            
            # Chart Card
            with col_chart:
                with st.container(border=True):
                    st.markdown("### Performance Distribution")
                    fig = px.bar(df, x="Name", y=f"Finals ({max_finals})", 
                                 template="plotly_dark", color=f"Finals ({max_finals})", 
                                 color_continuous_scale="Purples")
                    fig.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)', 
                        plot_bgcolor='rgba(0,0,0,0)', 
                        margin=dict(t=30, b=0, l=0, r=0),
                        xaxis_title="",
                        yaxis_title="Finals Marks"
                    )
                    st.plotly_chart(fig, use_container_width=True)

            # Table Card
            with col_table:
                with st.container(border=True):
                    st.markdown("### Student Risk Analysis")
                    
                    def highlight_risk(row):
                        if row["DNN Risk Level"] == "High":
                            return ['background-color: rgba(239, 68, 68, 0.2)'] * len(row)
                        elif row["DNN Risk Level"] == "Medium":
                            return ['background-color: rgba(245, 158, 11, 0.2)'] * len(row)
                        return [''] * len(row)
                        
                    st.dataframe(df.style.apply(highlight_risk, axis=1), use_container_width=True, hide_index=True)
            
    # --- TAB 2: Update Marks ---
    with tab2:
        if students:
            with st.container(border=True):
                st.markdown("### Update Student Marks")
                st.info("⚠️ Marks can only be updated within 24 hours of the first entry.")
                
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
                    
                    st.divider()
                    
                    with st.form("update_marks_form"):
                        col1, col2 = st.columns(2)
                        with col1:
                            mst = st.number_input(f"MST Marks (out of {max_mst})", 0.0, max_mst, float(acad.get("mst_marks", 0.0)))
                            finals = st.number_input(f"Finals Marks (out of {max_finals})", 0.0, max_finals, float(acad.get("finals_marks", 0.0)))
                        with col2:
                            absences = st.number_input("Total Absences", 0, 100, int(acad.get("absences", 0)))
                            failures = st.number_input("Past Failures", 0, 4, int(acad.get("failures", 0)))
                            studytime = st.slider("Study Time (1-4)", 1, 4, int(acad.get("studytime", 2)))
                        
                        submit = st.form_submit_button("Save Marks")
                        
                        if submit:
                            payload = {
                                "roll_no": selected_student["roll_no"],
                                "mst_marks": mst,
                                "finals_marks": finals,
                                "absences": absences,
                                "failures": failures,
                                "studytime": studytime,
                                "attendance_percent": float(acad.get("attendance_percent", 100.0))
                            }
                            res = update_student_marks(token, payload)
                            
                            if res.status_code == 200:
                                # Trigger Continuous Feedback Loop
                                eval_payload = {
                                    "roll_no": selected_student["roll_no"],
                                    "subject": subject,
                                    "mst_marks": mst,
                                    "finals_marks": finals,
                                    "max_mst": max_mst,
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

    # --- TAB 3: Attendance Register ---
    with tab3:
        with st.container(border=True):
            st.markdown("### Daily Attendance Register")
            
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
                
                st.write("")
                if st.button("Save Attendance", type="primary"):
                    records = [{"roll_no": row["Roll No"], "status": row["Mark"]} for _, row in edited_df.iterrows()]
                    res = save_attendance_register(token, date_str, records)
                    if res.status_code == 200:
                        st.success(f"Attendance successfully saved for {date_str}!")
                        st.rerun()
                    else:
                        st.error(f"Error: {res.json().get('detail')}")

    # --- TAB 4: Settings ---
    with tab4:
        with st.container(border=True):
            st.markdown("### Class Configuration")
            st.write(f"Set the maximum marks for **{subject}**. This updates calculations across the system.")
            
            with st.form("config_form"):
                col1, col2 = st.columns(2)
                with col1:
                    new_max_mst = st.number_input("Max MST Marks", 0.0, 100.0, float(max_mst))
                with col2:
                    new_max_finals = st.number_input("Max Finals Marks", 0.0, 100.0, float(max_finals))
                    
                st.write("")
                if st.form_submit_button("Save Configuration"):
                    update_class_config(token, {"max_mst": new_max_mst, "max_finals": new_max_finals})
                    st.success("Configuration saved! Refreshing...")
                    st.rerun()