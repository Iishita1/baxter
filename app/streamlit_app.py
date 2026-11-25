import sys
import os

# --- Path Setup ---
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root_dir not in sys.path:
    sys.path.append(root_dir)

import streamlit as st
from app.api_client import login_user
from app.views import student_view, prof_view, admin_view, experiment_lab

# Set page config (Must be first Streamlit command)
st.set_page_config(page_title="Baxter SaaS", page_icon="🎓", layout="wide")

# --- Load Custom SaaS CSS ---
def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

css_path = os.path.join(root_dir, "app", "assets", "style.css")
local_css(css_path)

# --- Initialize Session State safely ---
if "token" not in st.session_state:
    st.session_state.token = None
if "role" not in st.session_state:
    st.session_state.role = None
if "name" not in st.session_state:
    st.session_state.name = None

# --- Check URL Query Params for Persisted Login on Reload ---
if st.session_state.token is None:
    if "token" in st.query_params:
        st.session_state.token = st.query_params["token"]
        st.session_state.role = st.query_params.get("role")
        st.session_state.name = st.query_params.get("name")

def logout():
    """Clear session state and query params to log out."""
    st.session_state.token = None
    st.session_state.role = None
    st.session_state.name = None
    # Clear URL params
    st.query_params.clear()
    st.rerun()

def main():
    # ==========================================
    # LOGIN SCREEN
    # ==========================================
    if not st.session_state.token:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        
        # Centered Login Form inside a SaaS Card
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            with st.container(border=True):
                st.markdown("""
                    <div style='text-align: center; margin-bottom: 20px;'>
                        <h1 style='font-size: 2.5rem; margin-bottom: 0;'>🎓 Baxter</h1>
                        <p style='color: #a0a0b0; font-size: 0.9rem;'>Student Performance Prediction</p>
                    </div>
                """, unsafe_allow_html=True)
                
                with st.form("login_form"):
                    roll_no = st.text_input("Roll Number / Admin ID")
                    password = st.text_input("Password", type="password")
                    submit = st.form_submit_button("Login", use_container_width=True)

                    if submit:
                        with st.spinner("Authenticating..."):
                            user_data = login_user(roll_no, password)
                            
                            if user_data:
                                # Set Session State
                                st.session_state.token = user_data["access_token"]
                                st.session_state.role = user_data["role"]
                                st.session_state.name = user_data["name"]
                                
                                # Set Query Params to survive reload (but clear on new tab)
                                st.query_params["token"] = user_data["access_token"]
                                st.query_params["role"] = user_data["role"]
                                st.query_params["name"] = user_data["name"]
                                
                                st.rerun()
                            else:
                                st.error("Invalid credentials. Please try again.")
    
    # ==========================================
    # MAIN APPLICATION (Logged In)
    # ==========================================
    else:
        # Sidebar with user info and logout
        with st.sidebar:
            st.markdown(f"""
                <div style='margin-bottom: 30px;'>
                    <h2 style='margin: 0;'>🎓 Baxter</h2>
                    <p style='color: #a0a0b0; font-size: 0.9rem;'>EdTech Platform</p>
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"**User:** {st.session_state.name}")
            role_display = st.session_state.role.capitalize() if st.session_state.role else "Unknown"
            st.markdown(f"**Role:** `{role_display}`")
            
            st.divider()
            
            if st.button("Logout", type="primary", use_container_width=True):
                logout()

        # --- Role-Based Routing ---
        if st.session_state.role == "student":
            student_view.render()
            
        elif st.session_state.role == "prof":
            prof_view.render()
            
        elif st.session_state.role == "admin":
            # Admin gets the main dashboard and the MLflow Experiment Lab
            tab1, tab2 = st.tabs(["🛡️ Admin Dashboard", "🧪 Experiment Lab"])
            with tab1:
                admin_view.render()
            with tab2:
                experiment_lab.render()
                
        else:
            st.error("Unknown role or session expired. Please log out and log back in.")

if __name__ == "__main__":
    main()