import streamlit as st
import pandas as pd
import plotly.express as px
from app.api_client import (create_user, get_all_users, delete_user, 
                            get_audit_logs, admin_override_marks, 
                            admin_override_attendance, get_admin_summary)

def render():
    # --- Header ---
    st.markdown("<h2 style='margin-bottom: 0;'>System Overview</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #a0a0b0;'>Manage users, audit logs, and system health.</p>", unsafe_allow_html=True)
    st.write("")
    
    token = st.session_state.token
    summary = get_admin_summary(token)
    
    # ==========================================
    # Top Row: Summary Cards
    # ==========================================
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        with st.container(border=True):
            st.metric("Total Students", summary.get('students', 0))
    with col2:
        with st.container(border=True):
            st.metric("Total Professors", summary.get('profs', 0))
    with col3:
        with st.container(border=True):
            st.metric("Admin Overrides", summary.get('overrides', 0))
    with col4:
        with st.container(border=True):
            st.metric("Attendance Logs", summary.get('attendance_logs', 0))

    st.write("")
    
    # ==========================================
    # Tabs
    # ==========================================
    tab_manage, tab_override, tab_logs = st.tabs(["👥 Manage Users", "⚡ Override System", "📜 Audit Logs"])

    # ==========================================
    # TAB 1: User Management
    # ==========================================
    with tab_manage:
        col_reg, col_del = st.columns([2, 1])
        
        # --- Register New User Card ---
        with col_reg:
            with st.container(border=True):
                st.markdown("### Register New User")
                
                sample_txt = """age: 17
Medu: 2
Fedu: 2
famrel: 4
freetime: 3
goout: 3
Dalc: 1
Walc: 2
health: 3
failures: 0
studytime: 2
school: GP
sex: F
address: U
famsize: GT3
Pstatus: T
Mjob: at_home
Fjob: teacher
reason: course
guardian: mother
schoolsup: no
famsup: yes
paid: no
activities: yes
nursery: yes
higher: yes
internet: yes
romantic: no"""
                
                st.download_button(
                    label="📄 Download Sample Metadata (.txt)",
                    data=sample_txt,
                    file_name="sample_student_metadata.txt",
                    mime="text/plain",
                    help="Download this template, fill it out, and upload it below."
                )

                with st.form("add_user_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        roll_no = st.text_input("Roll Number / ID")
                        name = st.text_input("Full Name")
                        role = st.selectbox("Role", ["student", "prof", "admin"])
                    with col2:
                        email = st.text_input("Email (Optional)")
                        password = st.text_input("Temporary Password", type="password")
                        subject = None
                        if role == "prof":
                            subject = st.text_input("Assigned Subject (e.g., Mathematics)")
                    
                    uploaded_file = None
                    if role == "student":
                        uploaded_file = st.file_uploader("Upload Student Data (.txt)", type=["txt"])
                    
                    if st.form_submit_button("Create User", use_container_width=True):
                        if not roll_no or not name or not password:
                            st.error("Roll No, Name, and Password are required.")
                        else:
                            metadata = None
                            if uploaded_file:
                                metadata = {}
                                try:
                                    for line in uploaded_file.getvalue().decode("utf-8").splitlines():
                                        if ":" in line:
                                            k, v = line.split(":", 1)
                                            v = v.strip()
                                            metadata[k.strip()] = int(v) if v.isdigit() else v
                                except Exception as e:
                                    st.error(f"Error parsing file: {e}")
                            
                            payload = {
                                "roll_no": roll_no, "name": name, "role": role, 
                                "email": email, "password": password, 
                                "subject": subject, "metadata": metadata
                            }
                            res = create_user(token, payload)
                            if res.status_code == 201:
                                st.success("User created successfully!")
                                st.rerun()
                            else:
                                st.error(res.json().get('detail', 'Error creating user'))
                                
        # --- Delete User Card ---
        with col_del:
            with st.container(border=True):
                st.markdown("### Delete User")
                st.warning("⚠️ This will permanently remove the user and their records.")
                users = get_all_users(token)
                # Prevent deleting admins
                deletable_users = [u['roll_no'] for u in users if u['role'] != 'admin']
                
                if deletable_users:
                    student_to_delete = st.selectbox("Select User", options=deletable_users)
                    if st.button("Delete User", type="primary", use_container_width=True):
                        res = delete_user(token, student_to_delete)
                        if res.status_code == 200:
                            st.success("Deleted.")
                            st.rerun()
                        else:
                            st.error("Failed to delete.")
                else:
                    st.info("No deletable users found.")

        st.write("")
        
        # --- System Users Dataframe Card ---
        with st.container(border=True):
            st.markdown("### System Users")
            users = get_all_users(token)
            if users:
                df_users = pd.DataFrame(users)
                cols = [c for c in ['roll_no', 'name', 'role', 'subject'] if c in df_users.columns]
                st.dataframe(df_users[cols], use_container_width=True)
            else:
                st.info("No users in the system.")

    # ==========================================
    # TAB 2: Override System
    # ==========================================
    with tab_override:
        with st.container(border=True):
            st.markdown("### Force Override System")
            st.write("Enter a Roll Number to forcefully update records. This bypasses the 24h/48h locks and generates an audit log.")
            
            search_rno = st.text_input("Enter Student Roll Number", placeholder="e.g. 2410992514")
            
            if search_rno:
                users = get_all_users(token)
                student = next((u for u in users if u["roll_no"] == search_rno), None)
                
                if not student:
                    st.error("Student not found.")
                else:
                    st.info(f"Found Student: **{student['name']}** ({student['roll_no']})")
                    col_m, col_a = st.columns(2)
                    
                    # --- UPDATED OVERRIDE MARKS FORM ---
                    with col_m:
                        with st.form("override_marks"):
                            st.markdown("#### Override Marks")
                            subj = st.text_input("Subject", "Mathematics")
                            mst1 = st.number_input("MST 1 Marks (G1)", 0.0, 100.0)
                            mst2 = st.number_input("MST 2 Marks (G2)", 0.0, 100.0)
                            finals = st.number_input("Finals Marks (G3)", 0.0, 100.0)
                            
                            if st.form_submit_button("Override Marks", use_container_width=True):
                                res = admin_override_marks(token, {
                                    "roll_no": search_rno, 
                                    "subject": subj, 
                                    "mst1_marks": mst1, 
                                    "mst2_marks": mst2,
                                    "finals_marks": finals
                                })
                                if res.status_code == 200:
                                    st.success("Marks overridden and logged!")
                                else:
                                    st.error("Error overriding marks.")
                                    
                    # Override Attendance
                    with col_a:
                        with st.form("override_attendance"):
                            st.markdown("#### Override Attendance")
                            subj_att = st.text_input("Subject", "Mathematics", key="att_subj")
                            date_str = st.date_input("Date")
                            status = st.selectbox("Status", ["Present", "Absent", "Leave"])
                            if st.form_submit_button("Override Attendance", use_container_width=True):
                                res = admin_override_attendance(token, {
                                    "roll_no": search_rno, "subject": subj_att, 
                                    "date": str(date_str), "status": status
                                })
                                if res.status_code == 200:
                                    st.success("Attendance overridden and logged!")

    # ==========================================
    # TAB 3: Audit Logs
    # ==========================================
    with tab_logs:
        logs = get_audit_logs(token)
        
        if logs:
            df = pd.DataFrame(logs)
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
            
            col_chart, col_info = st.columns([1, 2])
            
            # Chart Card
            with col_chart:
                with st.container(border=True):
                    st.markdown("### Overrides by Admin")
                    fig = px.pie(df, names="admin_id", template="plotly_dark", 
                                 color_discrete_sequence=['#7c3aed', '#3b82f6', '#ec4899', '#f59e0b'])
                    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(t=30, b=0, l=0, r=0))
                    st.plotly_chart(fig, use_container_width=True)
                    
            # Table Card
            with col_info:
                with st.container(border=True):
                    st.markdown("### Recent Actions")
                    st.write("Immutable trail of all system overrides.")
                    st.dataframe(df[['timestamp', 'admin_id', 'target_roll_no', 'action_type']], use_container_width=True)
        else:
            st.info("No overrides have been performed yet.")