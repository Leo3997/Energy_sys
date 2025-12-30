import pandas as pd
import numpy as np

class EnergyOptimizer:
    def __init__(self, df):
        """
        Args:
            df (pd.DataFrame): Preprocessed dataframe with columns including
                               demand, pft, ia, ib, ic, etc.
        """
        self.df = df
        
    def detect_idle_state(self, threshold_power=None, duration_minutes=30, resample_interval_minutes=5):
        """
        Detects periods where the machine is likely in idle state (running but not productive).
        
        Args:
            threshold_power (float): Power (kW) below which is considered idle. 
                                     If None, estimated as 20th percentile of non-zero power.
            duration_minutes (int): Minimum duration to classify as idle event.
            resample_interval_minutes (int): Time interval between data points in minutes.
                                             Default 5 for offline CSV, use 1 for real-time.
        
        Returns:
            dict: Statistics about idle time and a DataFrame of idle periods.
        """
        # Determine which column to use for power
        # Prefer 'pt' if available and has non-zero values, else 'demand'
        power_col = 'demand'
        if 'pt' in self.df.columns and self.df['pt'].sum() > 0:
            power_col = 'pt'
        elif 'demand' not in self.df.columns:
             return {"error": "Missing power column ('pt' or 'demand')"}
             
        power = self.df[power_col]
        
        # Estimate threshold if not provided
        if threshold_power is None:
            # Assume idle is low power but not zero
            active_power = power[power > 0.1]
            if active_power.empty:
                return {"idle_hours": 0, "wasted_energy": 0}
            # Use 15th percentile
            threshold_power = active_power.quantile(0.15)
        
        # Identify idle periods
        is_idle = power < threshold_power
        
        # We want continuous blocks. 
        # Calculate duration of each block.
        # Since data is resampled to interval (e.g. 5min or 1min), each row is X min.
        
        # Group consecutive True values
        # Logic: (is_idle != is_idle.shift()).cumsum() creates a group ID that changes every time state changes
        groups = is_idle.ne(is_idle.shift()).cumsum()
        idle_blocks = self.df[is_idle].groupby(groups)
        
        idle_events = []
        total_wasted_energy = 0
        total_idle_time = 0
        
        for _, block in idle_blocks:
            duration = len(block) * resample_interval_minutes
            if duration >= duration_minutes:
                start_time = block.index.min()
                end_time = block.index.max()
                avg_power = block[power_col].mean()
                energy = (avg_power * duration) / 60.0 # kWh
                
                idle_events.append({
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration_minutes": duration,
                    "avg_power": avg_power,
                    "wasted_energy_kwh": energy
                })
                total_wasted_energy += energy
                total_idle_time += duration
                
        return {
            "threshold_used": threshold_power,
            "total_idle_hours": total_idle_time / 60.0,
            "total_wasted_energy_kwh": total_wasted_energy,
            "idle_events_count": len(idle_events),
            "events": pd.DataFrame(idle_events)
        }

    def analyze_phase_balance(self):
        """
        Analyzes current unbalance between phases A, B, C.
        Formula: Max deviation from mean / mean * 100%
        """
        cols = ['ia', 'ib', 'ic']
        if not all(c in self.df.columns for c in cols):
            return {"error": "Missing current columns"}
            
        currents = self.df[cols]
        # Calculate average current
        i_avg = currents.mean(axis=1)
        
        # Avoid division by zero
        valid_idx = i_avg > 1.0 
        
        if not valid_idx.any():
            return {"status": "Current too low for balance analysis"}
            
        # Max deviation
        max_dev = currents.sub(i_avg, axis=0).abs().max(axis=1)
        
        # Unbalance percentage
        unbalance = (max_dev / i_avg) * 100.0
        
        # Filter where current is significant
        unbalance_valid = unbalance[valid_idx]
        
        severe_unbalance = unbalance_valid[unbalance_valid > 15] # >15% is bad
        
        return {
            "avg_unbalance_percent": unbalance_valid.mean(),
            "max_unbalance_percent": unbalance_valid.max(),
            "severe_unbalance_hours": (len(severe_unbalance) * 5) / 60.0
        }

    def analyze_power_factor(self):
        """
        Analyzes Power Factor (pft/cos phi).
        Identifies time below 0.9.
        """
        if 'pft' not in self.df.columns:
            return {"error": "Missing 'pft' column"}
            
        pf = self.df['pft'].copy()
        
        # Scale PF if it looks like it's in range 0-1000
        if pf.max() > 1.5:
            pf = pf / 1000.0
        
        # Filter for times when system is running (power > some value)
        # Check available power column
        power_col = 'pt' if 'pt' in self.df.columns and self.df['pt'].max() > 0 else 'demand'
        running_so_valid = self.df[power_col] > (self.df[power_col].max() * 0.05)
        
        pf_active = pf[running_so_valid]
        
        low_pf = pf_active[pf_active < 0.9]
        
        return {
            "avg_pf": pf_active.mean(),
            "min_pf": pf_active.min(),
            "low_pf_hours": (len(low_pf) * 5) / 60.0,
            "recommendation": "Install capacitor bank" if len(low_pf) > 0 else "Good PF"
        }

    def get_peak_demand(self):
        """
        Identifies peak demand.
        """
        power_col = 'pt' if 'pt' in self.df.columns and self.df['pt'].max() > 0 else 'demand'
        
        if power_col not in self.df.columns:
            return {}
            
        peak_val = self.df[power_col].max()
        peak_time = self.df[power_col].idxmax()
        
        return {
            "peak_demand_kw": peak_val,
            "peak_time": peak_time
        }
