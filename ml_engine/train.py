import mlflow
import mlflow.keras
import mlflow.sklearn
import joblib
import os
import pandas as pd
import numpy as np
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error

from ml_engine.preprocess import load_and_preprocess_data
from ml_engine.model import build_dnn, build_dnn_regression

# Set MLflow tracking URI (assuming server is running on default port)
mlflow.set_tracking_uri("http://127.0.0.1:5000")
mlflow.set_experiment("Baxter_Student_Performance")

def train_models():
    print("Loading and preprocessing data...")
    X_train, X_test, y_train, y_test, y_train_reg, y_test_reg, preprocessor = load_and_preprocess_data()
    
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
        
        mlflow.sklearn.log_model(
            rf, 
            name="random_forest_model", 
            skops_trusted_types=["sklearn.tree._tree.Tree"]
        )
        print(f"RF Results - Accuracy: {acc:.4f}, F1: {f1:.4f}")

        # --- 2. Train Random Forest Regressor ---
    print("\nTraining Random Forest Regressor...")
    with mlflow.start_run(run_name="Random_Forest_Regressor"):
        rf_reg = RandomForestRegressor(n_estimators=100, random_state=42)
        
        # Train on the actual G3 scores (y_train_reg)
        rf_reg.fit(X_train, y_train_reg)
        
        # Predict and calculate MAE
        reg_preds = rf_reg.predict(X_test)
        mae = mean_absolute_error(y_test_reg, reg_preds)
        
        # Log to MLflow
        mlflow.log_param("model_type", "RandomForestRegressor")
        mlflow.log_param("n_estimators", 100)
        mlflow.log_metric("mae", mae)
        
        mlflow.sklearn.log_model(
            rf_reg, 
            name="random_forest_regressor", 
            skops_trusted_types=["sklearn.tree._tree.Tree"]
        )
        print(f"RF Regressor - Mean Absolute Error: {mae:.2f} points off from actual G3.")

    # --- 2. Train Classification DNN ---
    print("\nTraining Classification DNN...")
    with mlflow.start_run(run_name="DNN_Classification"):
        input_dim = X_train.shape[1]
        model = build_dnn(input_dim)
        
        mlflow.keras.autolog()
        early_stop = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)
        
        history = model.fit(
            X_train, y_train.values, # .values for NumPy array
            validation_split=0.2,
            epochs=100,
            batch_size=32,
            callbacks=[early_stop],
            verbose=1
        )
        
        # .values for NumPy array
        loss, acc = model.evaluate(X_test, y_test.values, verbose=0)
        preds = (model.predict(X_test) > 0.5).astype(int)
        f1 = f1_score(y_test, preds)
        
        mlflow.log_metric("test_accuracy", acc)
        mlflow.log_metric("test_f1_score", f1)
        
        model.save("models/baxter_dnn.keras")
        mlflow.keras.log_model(model, name="dnn_model")
        print(f"Classification DNN - Accuracy: {acc:.4f}, F1: {f1:.4f}")

    # --- 3. Train Regression DNN ---
    print("\nTraining Regression DNN...")
    with mlflow.start_run(run_name="DNN_Regression"):
        reg_model = build_dnn_regression(input_dim)
        
        mlflow.keras.autolog()
        
        reg_model.fit(
            X_train, y_train_reg.values, # .values for NumPy array
            validation_split=0.2,
            epochs=100,
            batch_size=32,
            callbacks=[early_stop],
            verbose=1
        )
        
        # Evaluate Regression
        reg_preds = reg_model.predict(X_test).flatten()
        # Using y_test_reg (sklearn handles pandas series fine, but we use .values for consistency)
        mae = mean_absolute_error(y_test_reg.values, reg_preds)
        
        mlflow.log_metric("test_mae", mae)
        reg_model.save("models/baxter_dnn_regression.keras")
        mlflow.keras.log_model(reg_model, name="dnn_regression_model")
        print(f"Regression DNN - Mean Absolute Error: {mae:.2f} points off from actual G3.")

if __name__ == "__main__":
    train_models()