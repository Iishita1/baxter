import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer

def load_and_preprocess_data(filepath="data/raw/student-por.csv"):
    # UCI dataset uses ';' separator
    df = pd.read_csv(filepath, sep=";")
    
    # Target 1: Classification (Pass/Fail)
    df["pass"] = (df["G3"] >= 10).astype(int)
    y_class = df["pass"]
    
    # Target 2: Regression (Actual G3 Score)
    y_reg = df["G3"]
    
    # Features
    num_cols = ['age', 'absences', 'failures', 'Medu', 'Fedu', 'famrel', 
                'freetime', 'goout', 'Dalc', 'Walc', 'health', 'G1', 'G2']
    cat_cols = ['school', 'sex', 'address', 'famsize', 'Pstatus', 'Mjob', 
                'Fjob', 'reason', 'guardian', 'schoolsup', 'famsup', 'paid', 
                'activities', 'nursery', 'higher', 'internet', 'romantic']
    
    X = df[num_cols + cat_cols]
    
    # Train/Test Split (Splitting X, y_class, and y_reg together!)
    X_train, X_test, y_train, y_test, y_train_reg, y_test_reg = train_test_split(
        X, y_class, y_reg, test_size=0.2, random_state=42, stratify=y_class
    )
    
    # Preprocessing Pipeline
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), num_cols),
            ('cat', OneHotEncoder(handle_unknown='ignore'), cat_cols)
        ])
    
    X_train_processed = preprocessor.fit_transform(X_train)
    X_test_processed = preprocessor.transform(X_test)
    
    # Return both targets
    return X_train_processed, X_test_processed, y_train, y_test, y_train_reg, y_test_reg, preprocessor