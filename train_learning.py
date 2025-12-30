import pickle
import numpy as np
import time
import os
from datetime import datetime, timedelta
# Import database connector
try:
    from energy_model.mysql_db import MySQLDatabase
except ImportError:
    print("Error: Could not import MySQLDatabase. Make sure energy_model package is in path.")
    exit(1)

# Config
DB_CONFIG = {
    'host': "115.120.248.123",
    'user': "root",
    'password': "rootpassword",
    'database': "energy"
}
MODEL_PATH = "q_brain.pkl"

def train_offline():
    print("🧠 [Offline Training] Starting...")
    
    # 1. Connect DB
    db = MySQLDatabase(**DB_CONFIG)
    if not db.conn:
        print("❌ DB Connection failed")
        return

    # 2. Fetch "INJECT" events vs "MONITOR" states
    # This is a simplified Mock RL update logic
    print("📊 Fetching history events...")
    events = db.fetch_events(limit=5000)
    
    # Filter for Lubrication Injection events
    inject_events = [e for e in events if e['action_type'] == 'INJECT' or e['action_type'] == '人工喷油']
    print(f"   Found {len(inject_events)} injection events.")

    # 3. Load Q-Table
    if os.path.exists(MODEL_PATH):
        with open(MODEL_PATH, "rb") as f:
            q_table = pickle.load(f)
        print("   Loaded existing Q-Table.")
    else:
        # Initialize (10 current states x 10 temp states, 2 actions)
        q_table = np.zeros((10, 10, 2))
        print("   Created NEW Q-Table.")

    # 4. Learning Loop (Simplified)
    # Logic: If after Injection, the temperature (from subsequent logs?) dropped, Reward +1.
    # Since we don't have time-series in MySQL easily (only events), we might need InfluxDB for effect verification.
    # For this script, we will simulate a "Mock Reward" based on the event details assuming it was successful.
    
    alpha = 0.1 # Learning Rate
    gamma = 0.9 # Discount
    
    updates = 0
    for evt in inject_events:
        try:
            details = evt.get('details_json')
            if isinstance(details, str): import json; details = json.loads(details)
            
            # Extract state
            curr = float(details.get('current', '10.0').replace('A',''))
            temp = float(details.get('temp', '40.0').replace('°C',''))
            
            curr_idx = int(min(9, max(0, (curr - 9.0) * 2)))
            temp_idx = int(min(9, max(0, (temp - 25.0) / 5)))
            
            # Assume constant reward for "Human Intervention" (Imitation Learning)
            # If human injected, it means it was necessary -> Reward AI to do it too.
            reward = 5.0 if '人工' in evt['action_type'] else 1.0
            
            # Q-Learning Update
            # Old Q
            old_q = q_table[curr_idx, temp_idx, 1] # Action 1 = Inject
            
            # Max Future Q (Assume next state is better/cooler)
            next_max = np.max(q_table[curr_idx, max(0, temp_idx-1)]) 
            
            # New Q
            new_q = (1 - alpha) * old_q + alpha * (reward + gamma * next_max)
            
            q_table[curr_idx, temp_idx, 1] = new_q
            updates += 1
        except Exception as e:
            # print(f"Skip event {e}")
            pass

    print(f"✅ Updated {updates} Q-values.")
    
    # 5. Save Model
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(q_table, f)
    print(f"💾 Model saved to {MODEL_PATH}")

if __name__ == "__main__":
    train_offline()
