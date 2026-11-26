from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout, BatchNormalization, Input
from tensorflow.keras.optimizers import Adam

def build_dnn(input_dim):
    model = Sequential([
        Input(shape=(input_dim,)), 
        Dense(64, activation='relu'),
        BatchNormalization(),
        Dropout(0.3),
        
        Dense(32, activation='relu'),
        BatchNormalization(),
        Dropout(0.2),
        
        Dense(16, activation='relu'),
        
        Dense(1, activation='sigmoid')
    ])
    
    model.compile(
        optimizer=Adam(learning_rate=0.001),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )
    return model

def build_dnn_regression(input_dim):
    model = Sequential([
        Input(shape=(input_dim,)), 
        Dense(64, activation='relu'),
        BatchNormalization(),
        Dropout(0.3),
        
        Dense(32, activation='relu'),
        BatchNormalization(),
        Dropout(0.2),
        
        Dense(16, activation='relu'),
        
        # REGRESSION OUTPUT: Linear activation, no sigmoid!
        Dense(1, activation='linear') 
    ])
    
    model.compile(
        optimizer=Adam(learning_rate=0.001),
        # REGRESSION LOSS: Mean Squared Error instead of Binary Crossentropy!
        loss='mse', 
        metrics=['mae'] # Mean Absolute Error
    )
    return model