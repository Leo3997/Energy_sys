from influxdb_client import InfluxDBClient
import pandas as pd
import warnings

# Suppress FutureWarning from influxdb_client regarding tabular data
warnings.simplefilter(action='ignore', category=FutureWarning)

class InfluxConnector:
    def __init__(self, url, token, org, bucket):
        self.client = InfluxDBClient(url=url, token=token, org=org, timeout=10000)
        self.bucket = bucket
        self.org = org
        self.query_api = self.client.query_api()

    def query_recent_data(self, minutes=30, device_id=None):
        """
        Query recent data from InfluxDB.
        
        Args:
            minutes (int): Lookback period in minutes.
            device_id (str): Optional device ID to filter by gateWayId.
            
        Returns:
            pd.DataFrame: Pivoted and resampled DataFrame fit for EnergyOptimizer.
                          Returns None if query fails or is empty.
        """
        # Flux query to get data for specific measurements and fields
        # Getting all fields from 'ElectricalEnergy' measurement
        device_filter = f'|> filter(fn: (r) => r["gateWayId"] == "{device_id}")' if device_id else ''
        
        query = f"""
        from(bucket: "{self.bucket}")
          |> range(start: -{minutes}m)
          |> filter(fn: (r) => r["_measurement"] == "ElectricalEnergy")
          {device_filter}
          |> filter(fn: (r) => r["_field"] == "ua" or r["_field"] == "ub" or r["_field"] == "uc" or r["_field"] == "ia" or r["_field"] == "ib" or r["_field"] == "ic" or r["_field"] == "pt" or r["_field"] == "demand" or r["_field"] == "pft" or r["_field"] == "impep")
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
          |> keep(columns: ["_time", "ua", "ub", "uc", "ia", "ib", "ic", "pt", "demand", "pft", "impep"])
        """
        
        try:
            # Query and return as DataFrame
            df = self.query_api.query_data_frame(query)
            
            if df.empty:
                return None
                
            # Clean up DataFrame
            # influxdb-client returns '_time', 'result', 'table', etc.
            if '_time' in df.columns:
                df['_time'] = pd.to_datetime(df['_time'])
                df = df.set_index('_time')
                
            # Drop non-numeric columns that might have slipped through (like tags) if pivot didn't handle them implicitly
            numeric_cols = ['ua', 'ub', 'uc', 'ia', 'ib', 'ic', 'pt', 'demand', 'pft', 'impep']
            available_cols = [c for c in numeric_cols if c in df.columns]
            
            df = df[available_cols].apply(pd.to_numeric, errors='coerce')
            
            # Resample to 1 minute or keep raw? 
            # Optimization logic expects approx 5 mins for rates, but raw is fine if index is datetime.
            # Let's resample to ensure regularity, matching the offline model's expectation of 'blocks'
            if not df.empty:
                df = df.resample('1T').mean().interpolate(method='linear', limit=2)
                
            return df
            
        except Exception as e:
            print(f"InfluxDB Query Error: {e}")
            return None

    def close(self):
        self.client.close()
