import pickle
import numpy as np

# Q-Table Structure: 10 x 10 x 2
# Axis 0: Current State (0-9) representing 10.0A to ~15.0A
# Axis 1: Temperature State (0-9) representing 25C to ~70C
# Axis 2: Action (0=Monitor, 1=Inject)

q_table = np.zeros((10, 10, 2))

# Define Thresholds
# Current > 12.0A -> Index > 4 (assuming (12-10)*2 = 4)
# Temp > 50C -> Index > 5 (assuming (50-25)/5 = 5)

for curr_idx in range(10):
    for temp_idx in range(10):
        # Calculate approximate physical values for checking
        # Logic matches backend_server.py:
        # curr_idx = (curr - 9.0) * 2  => curr = curr_idx/2 + 9.0
        # temp_idx = (temp - 25.0) / 5 => temp = temp_idx*5 + 25.0
        
        sim_curr = curr_idx / 2.0 + 9.0
        sim_temp = temp_idx * 5.0 + 25.0
        
        # Policy: 
        # If Current > 12.0 or Temp > 45.0, prefer INJECT (Action 1)
        if sim_curr > 14.5 or sim_temp > 45.0:
            q_table[curr_idx, temp_idx, 0] = 0.0  # Monitor reward low
            q_table[curr_idx, temp_idx, 1] = 10.0 # Inject reward high
        else:
            q_table[curr_idx, temp_idx, 0] = 10.0 # Monitor reward high
            q_table[curr_idx, temp_idx, 1] = 0.0  # Inject reward low

# Save to pickle
with open("q_brain.pkl", "wb") as f:
    pickle.dump(q_table, f)

print("✅ 'q_brain.pkl' has been generated with threshold logic.")
print("   - Thresholds: Current > 14.5A OR Temperature > 45.0C -> INJECT")
