import streamlit as st
import pandas as pd
from datetime import date
import plotly.express as px
from app.api_client import (get_student_dashboard, save_student_goal, 
                            get_student_goals, calculate_what_if, 
                            predict_student, get_student_subject_config)

def render():
    # --- Header ---
    st.markdown(f"<h2 style='margin-bottom: 0;'>Hello, {st.session_state.get('name')}</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #a0a0b0;'>Welcome to your personal performance dashboard.</p>", unsafe_allow_html=True)
    st.write("")
    
    token = st.session_state.token
    
    # --- Subject Selector ---
    col_subj, _ = st.columns([1, 2])
    with col_subj:
        subject = st.selectbox("📚 Select Subject", ["Mathematics", "Portuguese", "English", "Physics"])
    
    st.write("")
    
    # Fetch data based on selected subject
    dash = get_student_dashboard(token, subject)
    acad = dash.get("academics") or {}
    att = dash.get("attendance") or {}
    
    # Fetch config for max marks (used in DNN mapping and What-If)
    config = get_student_subject_config(token, subject)
    max_mst1 = float(config.get("max_mst1", 20.0))
    max_mst2 = float(config.get("max_mst2", 20.0))
    max_finals = float(config.get("max_finals", 60.0))
    
    # Fetch goals early so we can use the latest one as a sticky note
    goals = get_student_goals(token, subject)
    latest_goal = goals[0] if goals else None
    
    tab1, tab2, tab3 = st.tabs(["📊 My Performance", "🎯 Goals & Logs", "🧮 What-If Calculator"])
    
    # ==========================================
    # TAB 1: Performance Overview
    # ==========================================
    with tab1:
        # --- Sticky Note (Active Goals) ---
        if latest_goal and (latest_goal.get("daily_goal") or latest_goal.get("monthly_goal")):
            with st.container(border=True):
                st.markdown("### 📌 Active Goals")
                col_d, col_w, col_m = st.columns(3)
                
                with col_d:
                    st.info(f"**Daily:**\n\n{latest_goal.get('daily_goal', 'Not set')}")
                with col_w:
                    st.warning(f"**Weekly:**\n\n{latest_goal.get('weekly_goal', 'Not set')}")
                with col_m:
                    st.success(f"**Monthly:**\n\n{latest_goal.get('monthly_goal', 'Not set')}")
            st.write("")

        # Custom Metric Cards Row
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            with st.container(border=True):
                st.metric("MST 1", acad.get('mst1_marks', '-'))
        with col2:
            with st.container(border=True):
                st.metric("MST 2", acad.get('mst2_marks', '-'))
        with col3:
            with st.container(border=True):
                st.metric("Finals", acad.get('finals_marks', '-'))
        with col4:
            with st.container(border=True):
                st.metric("Attendance", f"{att.get('percentage', 100)}%")

        st.write("") 
        
        col_chart, col_risk = st.columns([1, 1])
        
        # Plotly Donut Chart for Attendance
        with col_chart:
            with st.container(border=True):
                st.markdown(f"### Attendance Breakdown")
                if att.get("total_classes", 0) > 0:
                    labels = ['Present', 'Absent', 'Leaves']
                    values = [att['present'], att['absent'], att['leaves']]
                    
                    fig = px.pie(names=labels, values=values, hole=0.6, 
                                 template="plotly_dark",
                                 color=labels, color_discrete_map={'Present':'#3b82f6', 'Absent':'#ef4444', 'Leaves':'#f59e0b'})
                    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(t=30, b=0, l=0, r=0), showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No attendance records found yet.")
                
        # DNN Risk Analysis
        with col_risk:
            with st.container(border=True):
                st.markdown("### 🧠 AI Performance Analysis")
                
                # FIX: Check if keys exist in the dictionary to prevent false "No Data"
                if acad and "mst1_marks" in acad and "mst2_marks" in acad:
                    
                    # 1. Map dynamic marks (MST1/MST2) to UCI G1/G2 (0-20 scale)
                    g1 = min(20, (acad.get("mst1_marks", 0) / max_mst1) * 20) if max_mst1 > 0 else 0
                    g2 = min(20, (acad.get("mst2_marks", 0) / max_mst2) * 20) if max_mst2 > 0 else 0
                    
                    # 2. Start with default fallback data
                    payload = {
                        "age": 17, "absences": att.get("absent", 0), "failures": acad.get("failures", 0),
                        "Medu": 2, "Fedu": 2, "famrel": 4, "freetime": 3, "goout": 3,
                        "Dalc": 1, "Walc": 2, "health": 3, "G1": int(g1), "G2": int(g2),
                        "school": "GP", "sex": "F", "address": "U", "famsize": "GT3", 
                        "Pstatus": "T", "Mjob": "at_home", "Fjob": "teacher", "reason": "course",
                        "guardian": "mother", "schoolsup": "no", "famsup": "yes",
                        "paid": "no", "activities": "yes", "nursery": "yes",
                        "higher": "yes", "internet": "yes", "romantic": "no"
                    }
                    
                    # 3. Override with uploaded metadata (Admin's static data)
                    if dash.get("metadata"):
                        for k, v in dash["metadata"].items():
                            if k in payload:
                                payload[k] = v
                                
                    # 4. Override with live data
                    payload["absences"] = att.get("absent", payload.get("absences", 0))
                    payload["G1"] = int(g1)
                    payload["G2"] = int(g2)
                    
                    res = predict_student(token, payload)
                    if res.status_code == 200:
                        data = res.json()
                        risk = data.get("risk_level")
                        pred_score = data.get("predicted_score")
                        
                        # 1. Show Classification (Risk Level)
                        st.markdown("#### Risk Classification")
                        if risk == "High":
                            st.error(f"🚨 **Risk Level: {risk}**\n\nYour current trajectory suggests a high risk of failing. Please focus on your studies and attend classes.")
                        elif risk == "Medium":
                            st.warning(f"⚠️ **Risk Level: {risk}**\n\nYou are on the borderline. There is room for improvement.")
                        else:
                            st.success(f"✅ **Risk Level: {risk}**\n\nYou are on track to pass. Keep up the great work!")
                        
                        st.divider()
                        
                        # 2. Show Regression (Expected Score)
                        st.markdown("#### Expected Final Grade")
                        if pred_score is not None:
                            scaled_score = (pred_score / 20.0) * max_finals
                            st.info(f"Based on your current MST trajectory, the model predicts you will score around **{scaled_score:.2f} / {max_finals}** in the Finals (G3).")
                        else:
                            st.write("Regression model not found.")
                else:
                    st.info("AI Prediction requires both MST1 and MST2 to be graded by your professor.")

    # ==========================================
    # TAB 2: Goals & Logs
    # ==========================================
    with tab2:
        with st.container(border=True):
            st.markdown(f"### Daily Log & Goals ({subject})")
            with st.form("goal_form"):
                log_date = st.date_input("Date", date.today()).strftime("%Y-%m-%d")
                
                col1, col2 = st.columns(2)
                with col1:
                    study_hrs = st.number_input("Study Hours Today", 0.0, 24.0, 2.0, step=0.5)
                    expected_grade = st.selectbox("Expected Grade", ["O", "A+", "A", "B+", "B", "C", "P", "F"])
                with col2:
                    daily_goal = st.text_input("Daily Goal")
                    weekly_goal = st.text_input("Weekly Goal")
                    
                monthly_goal = st.text_area("Monthly Goal")
                daily_review = st.text_area("Daily Life Review (How was your day?)")
                
                if st.form_submit_button("Save Log"):
                    payload = {
                        "date": log_date, "subject": subject, "study_hours": study_hrs, 
                        "expected_grade": expected_grade, "daily_goal": daily_goal, 
                        "weekly_goal": weekly_goal, "monthly_goal": monthly_goal, 
                        "daily_review": daily_review
                    }
                    save_student_goal(token, payload)
                    st.success("Log saved successfully!")
                    st.rerun()
                
        st.write("")
        
        with st.container(border=True):
            st.markdown("### Recent Logs")
            
            if goals:
                df_goals = pd.DataFrame(goals)
                display_cols = ["date", "study_hours", "expected_grade", "daily_goal", "weekly_goal", "monthly_goal", "daily_review"]
                display_cols = [c for c in display_cols if c in df_goals.columns]
                st.dataframe(df_goals[display_cols], use_container_width=True)
            else:
                st.info("No logs found yet. Start tracking your progress!")

    # ==========================================
    # TAB 3: What-If Calculator
    # ==========================================
    with tab3:
        with st.container(border=True):
            st.markdown(f"### Grade Calculator ({subject})")
            
            st.write(f"Calculating based on class totals: **MST1 ({max_mst1})**, **MST2 ({max_mst2})**, **Finals ({max_finals})**.")
            
            with st.form("what_if_form"):
                default_mst1 = float(acad.get("mst1_marks", 0.0))
                default_mst2 = float(acad.get("mst2_marks", 0.0))
                
                # Safety checks to prevent Streamlit crash if marks exceed max config
                safe_max_mst1 = max(float(max_mst1), default_mst1)
                safe_max_mst2 = max(float(max_mst2), default_mst2)
                
                col1, col2 = st.columns(2)
                with col1:
                    current_mst1 = st.number_input(
                        f"Your MST 1 Marks (out of {max_mst1})", 
                        min_value=0.0, 
                        max_value=safe_max_mst1, 
                        value=min(default_mst1, safe_max_mst1)
                    )
                with col2:
                    current_mst2 = st.number_input(
                        f"Your MST 2 Marks (out of {max_mst2})", 
                        min_value=0.0, 
                        max_value=safe_max_mst2, 
                        value=min(default_mst2, safe_max_mst2)
                    )
                
                target_grade = st.selectbox("Target Grade", ["O", "A+", "A", "B+", "B", "C", "P"])
                
                if st.form_submit_button("Calculate"):
                    res = calculate_what_if(token, {
                        "subject": subject, 
                        "current_mst1": current_mst1, 
                        "current_mst2": current_mst2,
                        "target_grade": target_grade
                    })
                    
                    if res.status_code == 200:
                        st.success(f"### {res.json()['message']}")
                    else:
                        st.error("Error calculating. Please try again.")