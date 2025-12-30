import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import joblib
import os

class LSTMModel(nn.Module):
    def __init__(self, input_size, hidden_size=64, num_layers=2):
        super(LSTMModel, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)
        
    def forward(self, x):
        # x shape: (batch, seq_len, input_size)
        out, _ = self.lstm(x)
        # Decode the hidden state of the last time step
        out = self.fc(out[:, -1, :])
        return out

class LSTMForecaster:
    def __init__(self, sequence_length=24):
        self.seq_len = sequence_length # 24 steps = 2 hours (at 5min intervals)
        self.scaler = MinMaxScaler()
        self.model = None
        self.is_trained = False
        self.input_size = 3 # pt, hour, dayofweek
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
    def prepare_data(self, df, training=True):
        """
        Prepare sequences for LSTM.
        Data format: [pt, hour, dayofweek]
        """
        data = df.copy()
        
        # Select Power Column
        power_col = 'pt' if 'pt' in data.columns and data['pt'].max() > 0 else 'demand'
        if power_col not in data.columns:
            return None, None
            
        # Normalize
        values = data[power_col].values.reshape(-1, 1)
        
        # Time features
        hours = data.index.hour.values.reshape(-1, 1) / 23.0
        days = data.index.dayofweek.values.reshape(-1, 1) / 6.0
        
        if training:
            self.scaler.fit(values)
        
        scaled_power = self.scaler.transform(values)
        
        # Combine [power, hour, day]
        features = np.hstack((scaled_power, hours, days))
        
        if not training:
            return features, None
            
        # Create Sequences and Targets (Max of next 1 hour / 12 steps)
        X, y = [], []
        target_window = 12
        
        # We need seq_len past data + target_window future data
        total_len = len(features)
        
        for i in range(total_len - self.seq_len - target_window):
            seq_x = features[i : i + self.seq_len]
            # Target is Max power in next window
            # We must use unscaled power for target? No, scale target too for better convergence.
            target_seq = scaled_power[i + self.seq_len : i + self.seq_len + target_window]
            target_max = np.max(target_seq)
            
            X.append(seq_x)
            y.append(target_max)
            
        return np.array(X), np.array(y)

    def train(self, df, epochs=50, lr=0.001):
        print("Preparing LSTM training data...")
        X, y = self.prepare_data(df, training=True)
        
        if X is None or len(X) == 0:
            print("Not enough data to train LSTM.")
            return
            
        # To Tensor
        X_tensor = torch.from_numpy(X).float().to(self.device)
        y_tensor = torch.from_numpy(y).float().to(self.device).view(-1, 1)
        
        # Model
        self.model = LSTMModel(input_size=self.input_size).to(self.device)
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        
        print(f"Training LSTM on {len(X)} samples for {epochs} epochs...")
        self.model.train()
        
        for epoch in range(epochs):
            outputs = self.model(X_tensor)
            loss = criterion(outputs, y_tensor)
            
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            if (epoch+1) % 10 == 0:
                print(f"Epoch [{epoch+1}/{epochs}], Loss: {loss.item():.6f}")
                
        self.is_trained = True
        
        # Save
        torch.save(self.model.state_dict(), 'energy_model/lstm_model.pth')
        joblib.dump(self.scaler, 'energy_model/lstm_scaler.pkl')
        print("LSTM Model saved.")

    def predict_next_peak(self, current_df_window):
        if not self.is_trained:
            if os.path.exists('energy_model/lstm_model.pth'):
                self.model = LSTMModel(input_size=self.input_size).to(self.device)
                self.model.load_state_dict(torch.load('energy_model/lstm_model.pth', map_location=self.device))
                self.scaler = joblib.load('energy_model/lstm_scaler.pkl')
                self.is_trained = True
                self.model.eval()
            else:
                return None
                
        # Must have enough data for at least 1 sequence
        if len(current_df_window) < self.seq_len:
            return None
            
        # Take last seq_len rows
        window = current_df_window.iloc[-self.seq_len:]
        
        features, _ = self.prepare_data(window, training=False)
        # Should be shape (seq_len, 3)
        
        # Reshape to (1, seq_len, 3)
        X_tensor = torch.from_numpy(features).float().unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            pred_scaled = self.model(X_tensor).item()
            
        # Inverse transform
        # Create dummy array with shape (1, 1) and pred value to use inverse_transform
        pred_kw = self.scaler.inverse_transform([[pred_scaled]])[0][0]
        
        return pred_kw
