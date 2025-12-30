import pandas as pd
import numpy as np
import sys

def load_and_preprocess_data(file_path):
    print(f"Loading data from {file_path}...")
    
    try:
        # Read with low memory=False to avoid type warnings, and comment='#'
        df = pd.read_csv(file_path, comment='#', low_memory=False)
        print("CSV loaded successfully.")
        print(f"Initial shape: {df.shape}")
        print(f"Columns: {df.columns.tolist()}")
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return None

    required_cols = ['_time', '_value', '_field']
    if not all(col in df.columns for col in required_cols):
        print(f"Missing required columns. Found: {df.columns}")
        return None

    print("Converting _time to datetime...")
    try:
        # mixed format or ISO8601 usually works
        df['_time'] = pd.to_datetime(df['_time'], errors='coerce')
        # Drop rows where time is NaT
        original_len = len(df)
        df = df.dropna(subset=['_time'])
        print(f"Dropped {original_len - len(df)} rows with invalid time.")
    except Exception as e:
        print(f"Error converting time: {e}")
        return None
    
    print("Converting _value to numeric...")
    df['_value'] = pd.to_numeric(df['_value'], errors='coerce')
    
    # Filter only relevant fields
    relevant_fields = [
        'ua', 'ub', 'uc', 
        'ia', 'ib', 'ic', 
        'demand', 'pt', 
        'pft', 'impep'
    ]
    
    print(f"Filtering for fields: {relevant_fields}")
    df = df[df['_field'].isin(relevant_fields)]
    print(f"Shape after filtering: {df.shape}")
    
    if df.empty:
        print("Dataframe is empty after filtering!")
        return None

    print("Pivoting data table...")
    try:
        df_pivot = df.pivot_table(index='_time', columns='_field', values='_value', aggfunc='mean')
    except Exception as e:
        print(f"Error creating pivot table: {e}")
        return None
    
    print("Resampling to 5min intervals...")
    try:
        df_resampled = df_pivot.resample('5T').mean()
    except Exception as e:
        print(f"Error resampling: {e}")
        return None
        
    print("Interpolating missing values...")
    df_resampled = df_resampled.interpolate(method='linear', limit=2)
    
    print("Data preprocessing complete.")
    print(f"Shape: {df_resampled.shape}")
    
    return df_resampled

if __name__ == "__main__":
    file_path = r'F:\influxdb-1.8.10-1\2025-12-22_17_35_influxdb_data.csv'
    df = load_and_preprocess_data(file_path)
    if df is not None:
        print("Final DataFrame Head:")
        print(df.head())
        print("Final DataFrame Describe:")
        print(df.describe())
        # Save a sample for inspection
        df.head(100).to_csv('energy_model/preprocessed_sample.csv')
        print("Saved sample to energy_model/preprocessed_sample.csv")
