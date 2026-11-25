import requests

BASE_URL = "http://127.0.0.1:8000"

def get_auth_headers(token):
    return {"Authorization": f"Bearer {token}"}

def login_user(roll_no, password):
    url = f"{BASE_URL}/api/auth/login"
    payload = {"username": roll_no, "password": password}
    response = requests.post(url, data=payload)
    return response.json() if response.status_code == 200 else None

# --- Admin Routes ---
def get_all_users(token):
    url = f"{BASE_URL}/api/admin/users"
    response = requests.get(url, headers=get_auth_headers(token))
    return response.json() if response.status_code == 200 else []

def delete_user(token, roll_no):
    url = f"{BASE_URL}/api/admin/users/{roll_no}"
    return requests.delete(url, headers=get_auth_headers(token))

def get_audit_logs(token):
    url = f"{BASE_URL}/api/admin/audit-logs"
    response = requests.get(url, headers=get_auth_headers(token))
    return response.json() if response.status_code == 200 else []

# --- MLflow & Predict Routes ---
def get_mlflow_runs(token):
    url = f"{BASE_URL}/api/mlflow/runs"
    response = requests.get(url, headers=get_auth_headers(token))
    return response.json().get("runs", []) if response.status_code == 200 else []

def predict_student(token, student_data):
    url = f"{BASE_URL}/api/predict/"
    return requests.post(url, json=student_data, headers=get_auth_headers(token))

# --- Prof Routes ---
def get_all_students_prof(token):
    url = f"{BASE_URL}/api/prof/students"
    response = requests.get(url, headers=get_auth_headers(token))
    return response.json() if response.status_code == 200 else []

def update_student_marks(token, data):
    url = f"{BASE_URL}/api/prof/marks"
    return requests.post(url, json=data, headers=get_auth_headers(token))

def get_attendance_register(token, date_str):
    url = f"{BASE_URL}/api/prof/attendance/{date_str}"
    response = requests.get(url, headers=get_auth_headers(token))
    return response.json() if response.status_code == 200 else []

def save_attendance_register(token, date_str, records):
    url = f"{BASE_URL}/api/prof/attendance/{date_str}"
    payload = {"records": records}
    return requests.post(url, json=payload, headers=get_auth_headers(token))


def get_class_config(token):
    url = f"{BASE_URL}/api/prof/config"
    response = requests.get(url, headers=get_auth_headers(token))
    return response.json() if response.status_code == 200 else {"max_mst": 30.0, "max_finals": 70.0}

def update_class_config(token, config_data):
    url = f"{BASE_URL}/api/prof/config"
    return requests.post(url, json=config_data, headers=get_auth_headers(token))

# --- Admin Routes ---
def create_user(token, user_data):
    url = f"{BASE_URL}/api/admin/users"
    return requests.post(url, json=user_data, headers=get_auth_headers(token))

def admin_override_marks(token, data):
    url = f"{BASE_URL}/api/admin/override/marks"
    return requests.post(url, json=data, headers=get_auth_headers(token))

def admin_override_attendance(token, data):
    url = f"{BASE_URL}/api/admin/override/attendance"
    return requests.post(url, json=data, headers=get_auth_headers(token))

# --- Student Routes ---
def get_student_dashboard(token, subject):
    url = f"{BASE_URL}/api/student/dashboard/{subject}"
    response = requests.get(url, headers=get_auth_headers(token))
    return response.json() if response.status_code == 200 else {}

def save_student_goal(token, data):
    url = f"{BASE_URL}/api/student/goals"
    return requests.post(url, json=data, headers=get_auth_headers(token))

def get_student_goals(token, subject):
    url = f"{BASE_URL}/api/student/goals/{subject}"
    response = requests.get(url, headers=get_auth_headers(token))
    return response.json() if response.status_code == 200 else []

def calculate_what_if(token, data):
    url = f"{BASE_URL}/api/student/what-if"
    return requests.post(url, json=data, headers=get_auth_headers(token))

def get_student_subject_config(token, subject):
    url = f"{BASE_URL}/api/student/config/{subject}"
    response = requests.get(url, headers=get_auth_headers(token))
    return response.json() if response.status_code == 200 else {"max_mst": 30.0, "max_finals": 70.0}

def evaluate_and_log_feedback(token, data):
    url = f"{BASE_URL}/api/feedback/evaluate"
    return requests.post(url, json=data, headers=get_auth_headers(token))

def download_feedback_csv(token):
    url = f"{BASE_URL}/api/feedback/export"
    response = requests.get(url, headers=get_auth_headers(token))
    return response

def get_admin_summary(token):
    url = f"{BASE_URL}/api/admin/summary"
    response = requests.get(url, headers=get_auth_headers(token))
    return response.json() if response.status_code == 200 else {}