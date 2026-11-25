from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.database import connect_to_mongo, close_mongo_connection
from api.routes import auth_routes, admin_routes, predict_routes, mlflow_routes, prof_routes, student_routes, feedback_routes

app = FastAPI(title="Baxter API", version="2.0")

# Allow Streamlit (running on a different port) to talk to FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database startup/shutdown events
@app.on_event("startup")
async def startup_db_client():
    connect_to_mongo()

@app.on_event("shutdown")
async def shutdown_db_client():
    close_mongo_connection()

# Include Routers
app.include_router(auth_routes.router)
app.include_router(admin_routes.router)
app.include_router(predict_routes.router)
app.include_router(mlflow_routes.router)
app.include_router(prof_routes.router)
app.include_router(student_routes.router)
app.include_router(feedback_routes.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Baxter API. Go to /docs for documentation."}