import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer

def load_and_preprocess_data(filepath="data/raw/student-por.csv"):
    # UCI dataset uses ';' separator
    df = pd.read_csv(filepath, sep=";")
    
    # Target: 1 if pass (G3 >= 10), else 0
    df["pass"] = (df["G3"] >= 10).astype(int)
    
    # Benchmark Model Features (Including G1 and G2)
    num_cols = ['age', 'absences', 'failures', 'Medu', 'Fedu', 'famrel', 
                'freetime', 'goout', 'Dalc', 'Walc', 'health', 'G1', 'G2']
    cat_cols = ['school', 'sex', 'address', 'famsize', 'Pstatus', 'Mjob', 
                'Fjob', 'reason', 'guardian', 'schoolsup', 'famsup', 'paid', 
                'activities', 'nursery', 'higher', 'internet', 'romantic']
    
    X = df[num_cols + cat_cols]
    y = df["pass"]
    
    # Train/Test Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Preprocessing Pipeline
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), num_cols),
            ('cat', OneHotEncoder(handle_unknown='ignore'), cat_cols)
        ])
    
    X_train_processed = preprocessor.fit_transform(X_train)
    X_test_processed = preprocessor.transform(X_test)
    
    return X_train_processed, X_test_processed, y_train, y_test, preprocessor