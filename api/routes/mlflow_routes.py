import mlflow
from fastapi import APIRouter, Depends
from api.auth import get_current_admin

router = APIRouter(prefix="/api/mlflow", tags=["MLflow"])

# Point to the running MLflow server
mlflow.set_tracking_uri("http://127.0.0.1:5000")

@router.get("/runs")
def get_experiment_runs(current_user: dict = Depends(get_current_admin)):
    client = mlflow.tracking.MlflowClient()
    experiment = client.get_experiment_by_name("Baxter_Student_Performance")
    
    if not experiment:
        return {"runs": []}
        
    runs = client.search_runs(experiment_ids=[experiment.experiment_id])
    
    run_list = []
    for run in runs:
        run_list.append({
            "run_id": run.info.run_id,
            "run_name": run.data.tags.get("mlflow.runName", "Unnamed"),
            "status": run.info.status,
            "metrics": run.data.metrics,
            "params": run.data.params
        })
        
    return {"runs": run_list}