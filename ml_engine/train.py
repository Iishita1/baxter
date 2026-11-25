import mlflow
import mlflow.keras
import mlflow.sklearn
import joblib
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score
from tensorflow.keras.callbacks import EarlyStopping

from ml_engine.preprocess import load_and_preprocess_data
from ml_engine.model import build_dnn

# Set MLflow tracking URI (assuming server is running on default port)
mlflow.set_tracking_uri("http://127.0.0.1:5000")
mlflow.set_experiment("Baxter_Student_Performance")

def train_models():
    print("Loading and preprocessing data...")
    X_train, X_test, y_train, y_test, preprocessor = load_and_preprocess_data()
    
    # Save preprocessor for the FastAPI backend
    os.makedirs("models", exist_ok=True)
    joblib.dump(preprocessor, "models/baxter_preprocessor.pkl")
    print("Saved preprocessor to models/baxter_preprocessor.pkl")

    # --- 1. Train Random Forest Baseline ---
    print("\nTraining Random Forest...")
    with mlflow.start_run(run_name="Random_Forest_Baseline"):
        rf = RandomForestClassifier(n_estimators=100, random_state=42)
        rf.fit(X_train, y_train)
        preds = rf.predict(X_test)
        
        acc = accuracy_score(y_test, preds)
        f1 = f1_score(y_test, preds)
        
        mlflow.log_param("model_type", "RandomForest")
        mlflow.log_param("n_estimators", 100)
        mlflow.log_metric("accuracy", acc)
        mlflow.log_metric("f1_score", f1)
        
        # Log model to MLflow
        mlflow.sklearn.log_model(
            rf, 
            name="random_forest_model", 
            skops_trusted_types=["sklearn.tree._tree.Tree"]
        )       
        print(f"RF Results - Accuracy: {acc:.4f}, F1: {f1:.4f}")

    # --- 2. Train DNN ---
    print("\nTraining DNN...")
    with mlflow.start_run(run_name="DNN_Benchmark"):
        input_dim = X_train.shape[1]
        model = build_dnn(input_dim)
        
        # MLflow autologging for Keras (automatically logs loss/accuracy per epoch)
        mlflow.keras.autolog()
        
        early_stop = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)
        
        history = model.fit(
            X_train, y_train,
            validation_split=0.2,
            epochs=100,
            batch_size=32,
            callbacks=[early_stop],
            verbose=1
        )
        
        # Evaluate
        loss, acc = model.evaluate(X_test, y_test, verbose=0)
        preds = (model.predict(X_test) > 0.5).astype(int)
        f1 = f1_score(y_test, preds)
        
        mlflow.log_metric("test_accuracy", acc)
        mlflow.log_metric("test_f1_score", f1)
        
        # Save the DNN natively for the FastAPI backend
        model.save("models/baxter_dnn.keras")
        print("Saved DNN to models/baxter_dnn.keras")
        
        # Log model to MLflow
        mlflow.keras.log_model(model, name="dnn_model")
        print(f"DNN Results - Accuracy: {acc:.4f}, F1: {f1:.4f}")

if __name__ == "__main__":
    train_models()