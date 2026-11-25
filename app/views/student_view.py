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
                # Give it a subtle sticky-note look using a colored border/markdown
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
        col1, col2, col3 = st.columns(3)
        with col1:
            with st.container(border=True):
                st.metric("MST Marks", acad.get('mst_marks', '-'))
        with col2:
            with st.container(border=True):
                st.metric("Finals Marks", acad.get('finals_marks', '-'))
        with col3:
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
                st.markdown("### 🧠 AI Risk Analysis")
                st.write("Powered by the Baxter Deep Neural Network.")
                
                if acad.get("mst_marks") is not None:
                    g1 = min(20, (acad.get("mst_marks", 0) / 30.0) * 20) 
                    g2 = min(20, (acad.get("finals_marks", 0) / 70.0) * 20)
                    
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
                    
                    if dash.get("metadata"):
                        for k, v in dash["metadata"].items():
                            if k in payload:
                                payload[k] = v
                                
                    payload["absences"] = att.get("absent", payload.get("absences", 0))
                    payload["G1"] = int(g1)
                    payload["G2"] = int(g2)
                    
                    res = predict_student(token, payload)
                    if res.status_code == 200:
                        risk = res.json().get("risk_level")
                        
                        if risk == "High":
                            st.error(f"🚨 **Current Risk Level: {risk}**\n\nYour current trajectory suggests a high risk of failing. Please focus on your studies and attend classes.")
                        elif risk == "Medium":
                            st.warning(f"⚠️ **Current Risk Level: {risk}**\n\nYou are on the borderline. There is room for improvement.")
                        else:
                            st.success(f"✅ **Current Risk Level: {risk}**\n\nYou are on track to pass. Keep up the great work!")
                else:
                    st.info("Marks have not been updated by your professor yet.")

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
                # Expanded columns to show everything
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
            
            config = get_student_subject_config(token, subject)
            max_mst = float(config.get("max_mst", 30.0))
            max_finals = float(config.get("max_finals", 70.0))
            
            st.write(f"Calculating based on class totals: **MST ({max_mst})**, **Finals ({max_finals})**.")
            
            with st.form("what_if_form"):
                default_mst = float(acad.get("mst_marks", 0.0))
                
                # Safety check to prevent Streamlit crash if marks exceed max config
                safe_max = max(float(max_mst), default_mst)
                
                current_mst = st.number_input(
                    f"Your MST Marks (out of {max_mst})", 
                    min_value=0.0, 
                    max_value=safe_max, 
                    value=min(default_mst, safe_max)
                )
                
                target_grade = st.selectbox("Target Grade", ["O", "A+", "A", "B+", "B", "C", "P"])
                
                if st.form_submit_button("Calculate"):
                    res = calculate_what_if(token, {
                        "subject": subject, 
                        "mst_marks": current_mst, 
                        "target_grade": target_grade
                    })
                    
                    if res.status_code == 200:
                        st.success(f"### {res.json()['message']}")
                    else:
                        st.error("Error calculating. Please try again.")