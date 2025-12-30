import pandas as pd

try:
    file_path = r'F:\influxdb-1.8.10-1\2025-12-22_17_35_influxdb_data.csv'
    df = pd.read_csv(file_path, comment='#')
    print("Columns:", df.columns.tolist())
    print("First few rows:")
    print(df.head())
    print("Types:")
    print(df.dtypes)
except Exception as e:
    print(f"Error: {e}")
