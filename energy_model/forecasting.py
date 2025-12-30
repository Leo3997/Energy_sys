import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
import joblib
import os

class LoadForecaster:
    def __init__(self, df=None):
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.is_trained = False
        self.feature_cols = []
        if df is not None:
            self.prepare_data(df)

    def prepare_data(self, df):
        """
        Feature Engineering for Time Series Forecasting.
        """
        data = df.copy()
        
        # Ensure we use 'pt' or 'demand'
        power_col = 'pt' if 'pt' in data.columns and data['pt'].max() > 0 else 'demand'
        if power_col not in data.columns:
            print("Error: No power column found for forecasting.")
            return None, None
            
        # 1. Time Features
        data['hour'] = data.index.hour
        data['minute'] = data.index.minute
        data['dayofweek'] = data.index.dayofweek
        
        target_col = 'target_power_next_1h'
        
        # 2. Lag Features (Past values)
        # Using 5 min intervals. 
        # Lag 1 = 5 mins ago, Lag 12 = 1 hour ago
        lags = [1, 2, 3, 6, 12, 24] # 5m, 10m, 15m, 30m, 1h, 2h
        for lag in lags:
            data[f'lag_{lag}'] = data[power_col].shift(lag)
            
        # 3. Rolling Features
        # Rolling mean of last hour (12 periods of 5 mins)
        data['rolling_mean_1h'] = data[power_col].shift(1).rolling(window=12).mean()
        
        # 4. Target: Max power in next hour? or Avg?
        # Let's predict Max Power in next hour for Demand Charge reduction.
        # Shift -12 (future)
        indexer = pd.api.indexers.FixedForwardWindowIndexer(window_size=12)
        data[target_col] = data[power_col].rolling(window=indexer).max()
        
        # Drop NaNs created by lagging/shifting
        data = data.dropna()
        
        feature_cols = ['hour', 'minute', 'dayofweek', 'rolling_mean_1h'] + [f'lag_{l}' for l in lags]
        self.feature_cols = feature_cols
        
        return data, target_col

    def train(self, df):
        print("Preparing training data...")
        data, target_col = self.prepare_data(df)
        if data is None or data.empty:
            print("Not enough data to train.")
            return
            
        X = data[self.feature_cols]
        y = data[target_col]
        
        # Split
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
        
        print(f"Training on {len(X_train)} samples...")
        self.model.fit(X_train, y_train)
        self.is_trained = True
        
        # Validation
        preds = self.model.predict(X_test)
        mae = mean_absolute_error(y_test, preds)
        print(f"Model Trained. MAE on Test Set: {mae:.2f} kW")
        
        # Save model
        joblib.dump(self.model, 'energy_model/rf_model.pkl')
        print("Model saved to energy_model/rf_model.pkl")

    def predict_next_peak(self, current_df_window):
        """
        Predict peak demand for the next hour based on recent data window.
        Args:
            current_df_window: DataFrame containing at least last 2-3 hours of data 
                               to calculate lags and rolling means.
        """
        if not self.is_trained:
            # Try load
            if os.path.exists('energy_model/rf_model.pkl'):
                self.model = joblib.load('energy_model/rf_model.pkl')
                self.is_trained = True
                # Recover feature cols implies we know them or saved them. 
                # For simplicity, hardcoding them as per training logic or re-instantiating.
                # In prod, save metadata with model.
                self.feature_cols = ['hour', 'minute', 'dayofweek', 'rolling_mean_1h', 
                                     'lag_1', 'lag_2', 'lag_3', 'lag_6', 'lag_12', 'lag_24']
            else:
                return None

        # Prepare single row for prediction
        # We need the last timestamp's features
        # Create a small dummy DF to use the same feature engineering logic
        # OR manually construct the vector.
        
        # Let's take the tail, compute features, take the last row.
        data, _ = self.prepare_data(current_df_window)
        
        if data is None or data.empty:
            return None
            
        last_row = data.iloc[[-1]][self.feature_cols]
        pred = self.model.predict(last_row)[0]
        return pred
