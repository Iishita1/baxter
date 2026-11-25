# 🎓 Baxter: AI-Powered Student Performance & EdTech SaaS

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-SaaS_UI-FF4B4B)
![FastAPI](https://img.shields.io/badge/FastAPI-REST_API-009688)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248)
![TensorFlow](https://img.shields.io/badge/TensorFlow-DNN-FF6F00)
![MLflow](https://img.shields.io/badge/MLflow-MLOps-0194E2)

**Baxter** is a production-grade, role-based EdTech platform that leverages a Deep Neural Network (DNN) to predict student academic risks. It features multi-subject tracking, continuous MLOps feedback loops, and a sleek, dark-mode SaaS dashboard.

---

## 🏗️ System Architecture (P3 & P4)

Baxter is built on a modern 3-tier architecture:

1. **Frontend (Streamlit):** A custom CSS-styled SaaS interface with Plotly charts, role-based routing, and URL query-param authentication (persists on reload, logs out on tab close).
2. **Backend (FastAPI):** A high-performance REST API. Handles JWT authentication, role-based access control (RBAC), and business logic (like 24h/48h locks).
3. **Database (MongoDB Atlas):** A cloud NoSQL database handling flexible, document-based data structures.
4. **ML/MLOps Engine:** TensorFlow/Keras (DNN) tracked via MLflow.

---

## 🧠 Machine Learning & MLOps (P1 & P3)

### The Models
-   **Deep Neural Network (DNN):** A 3-hidden-layer architecture (64-32-16) with Batch Normalization and Dropout. Chosen for its ability to capture non-linear relationships between behavioral and academic features.
-   **Baseline (Random Forest):** Trained alongside the DNN to prove the DNN's superiority and provide a benchmark for MLflow tracking.

### The Features
-   **Data Leakage Prevention:** The model does *not* use current-semester marks to predict the current semester. Instead, it uses baseline demographics (uploaded by Admin) and maps live continuous assessment marks to a normalized scale.
-   **Continuous Feedback Loop:** Every time a Professor uploads final marks, the system evaluates the DNN's original prediction against the *actual* result. This is logged in MongoDB and can be exported as a CSV (`feedback_logs`) to retrain the model, simulating a real-world MLOps pipeline.
-   **Experiment Tracking:** MLflow is integrated. All hyperparameters, metrics (Accuracy, F1), and model artifacts (`.keras`, `.pkl`) are logged and viewable in the UI.

---

## ✨ Key Features & Business Logic (P2: Problem Solving)

### 🛡️ Admin Dashboard
-   **Onboarding:** Register students/professors. Assign professors to specific subjects. Upload `.txt` files containing static student metadata (UCI dataset features).
-   **Override System:** Forcefully update marks or attendance if a Professor misses the deadline.
-   **Audit Logs:** Every Admin override is logged immutably (`admin_id`, `target_student`, `old_value`, `new_value`, `timestamp`) to ensure accountability. Visualized via a Plotly donut chart.

### 👩‍🏫 Professor Dashboard
-   **Multi-Subject Isolation:** Professors only see data for the subject assigned to them by the Admin.
-   **Dynamic Settings:** Configure the maximum MST and Finals marks per subject.
-   **24-Hour Mark Lock:** To prevent tampering, marks cannot be edited 24 hours after the first entry (unless overridden by Admin).
-   **48-Hour Attendance Lock:** Professors manage a daily attendance register (Present, Absent, Leave). Locks after 48 hours.

### 🎓 Student Dashboard
-   **SaaS Interface:** A beautiful dark-mode interface with custom glassmorphism cards.
-   **Sticky Notes:** Active daily, weekly, and monthly goals are displayed prominently.
-   **AI Risk Analysis:** Real-time risk level (High/Medium/Low) based on the DNN model.
-   **What-If Calculator:** Dynamically calculates the score needed in Finals to achieve a target letter grade, adapting to the Professor's custom max-mark configurations.

---

## 🗄️ Database Schema (MongoDB Collections)

-   `users`: `{ roll_no, name, role, email, subject, hashed_password, metadata }`
-   `academics`: `{ roll_no, subject, mst_marks, finals_marks, absences, failures, last_updated }`
-   `attendance`: `{ roll_no, subject, date, status, marked_by }`
-   `config`: `{ subject, max_mst, max_finals }`
-   `goals`: `{ roll_no, subject, date, study_hours, expected_grade, daily_goal, weekly_goal, monthly_goal }`
-   `audit_logs`: `{ admin_id, target_roll_no, action_type, old_value, new_value, timestamp }`
-   `feedback_logs`: `{ roll_no, subject, predicted_class, actual_class, is_correct, timestamp }`

---

## 🚀 Local Setup & Installation

**Prerequisites:** Python 3.12 and a MongoDB Atlas URI.

### 1. Clone & Install
```bash
git clone https://github.com/yourusername/Baxter.git
cd Baxter
python -m venv .venv
# Activate venv (Windows: .venv\Scripts\activate | Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
```
### 2. Environment Variables
Create a .env file in the root directory:

```env
MONGODB_URI="mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority"
DATABASE_NAME="baxter_db"
SECRET_KEY="your_super_secret_jwt_key"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=60
```
### 3. Start MLflow Server
Open a terminal and run:

```bash
mlflow server --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlruns --host 127.0.0.1 --port 5000
```
### 4. Train the Model & Seed DB
Open a new terminal:

```bash
python -m ml_engine.train
python seed_db.py
```
### 5. Run the Application
#### Terminal 1 (Backend):

```bash
uvicorn api.main:app --reload
```
#### Terminal 2 (Frontend):

```bash
streamlit run app/streamlit_app.py
```
