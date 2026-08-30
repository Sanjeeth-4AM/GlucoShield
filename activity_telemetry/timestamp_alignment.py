"""
GlucoShield Timestamp Alignment & 15-Minute Grid Slicing
========================================================
Slices continuous high-frequency wearable telemetry into strictly causal 15-minute bins.
Enforces zero lookahead leakage, tracks coverage percentages, and flags missing sensors.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional

def align_telemetry_to_15m_grid(
    df_raw: pd.DataFrame,
    participant_id: str,
    min_coverage_threshold: float = 0.30,
    expected_sample_interval_sec: float = 5.0
) -> pd.DataFrame:
    """
    Transforms irregular/high-frequency raw telemetry into uniform 15-minute causal windows.
    
    Each 15m window at timestamp t summarizes telemetry in the interval (t - 15m, t].
    
    Args:
      df_raw: Raw DataFrame with ['timestamp', 'cgm_glucose', 'heart_rate', 'accel_x', 'accel_y', 'accel_z', 'steps']
      participant_id: Unique participant string ID
      min_coverage_threshold: Minimum valid data fraction required to mark sensor as present (default 30%)
      expected_sample_interval_sec: Native sample period in seconds
    """
    if df_raw.empty:
        return pd.DataFrame()

    df = df_raw.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    # Compute Euclidean acceleration magnitude if XYZ present
    if "accel_x" in df.columns and "accel_y" in df.columns and "accel_z" in df.columns:
        df["accel_mag"] = np.sqrt(df["accel_x"]**2 + df["accel_y"]**2 + df["accel_z"]**2)
    else:
        df["accel_mag"] = np.nan

    # Clean extreme physiological heart rate artifacts
    if "heart_rate" in df.columns:
        df["heart_rate"] = np.where((df["heart_rate"] >= 35.0) & (df["heart_rate"] <= 220.0),
                                    df["heart_rate"], np.nan)

    # Determine 15-minute grid boundaries
    t_start = df["timestamp"].min().floor("15min")
    t_end = df["timestamp"].max().ceil("15min")
    
    # 15m grid timestamps: each label represents the end of the 15-minute window
    grid_ts = pd.date_range(t_start + pd.Timedelta(minutes=15), t_end, freq="15min")

    expected_samples_per_15m = (15 * 60) / expected_sample_interval_sec

    rows = []
    for t_window_end in grid_ts:
        t_window_start = t_window_end - pd.Timedelta(minutes=15)
        
        # Causal window slice: (t_start, t_end]
        mask = (df["timestamp"] > t_window_start) & (df["timestamp"] <= t_window_end)
        window_df = df[mask]

        n_samples = len(window_df)
        valid_hr = window_df["heart_rate"].dropna() if "heart_rate" in window_df.columns else pd.Series(dtype=float)
        valid_accel = window_df["accel_mag"].dropna() if "accel_mag" in window_df.columns else pd.Series(dtype=float)
        
        # Coverage fraction
        n_valid_wearable = max(len(valid_hr), len(valid_accel))
        coverage_pct = min(100.0, (n_valid_wearable / max(1, expected_samples_per_15m)) * 100.0)
        
        is_sensor_missing = int(coverage_pct < (min_coverage_threshold * 100.0))

        # Steps: sum of steps in window
        if "steps" in window_df.columns and not is_sensor_missing:
            steps_15m = float(window_df["steps"].fillna(0).sum())
        else:
            steps_15m = 0.0 if not is_sensor_missing else np.nan

        # Heart Rate: mean and std
        if len(valid_hr) > 0 and not is_sensor_missing:
            hr_mean = float(valid_hr.mean())
            hr_std = float(valid_hr.std()) if len(valid_hr) > 1 else 0.0
        else:
            hr_mean = np.nan
            hr_std = np.nan

        # Accelerometer magnitude: mean
        if len(valid_accel) > 0 and not is_sensor_missing:
            accel_mean = float(valid_accel.mean())
        else:
            accel_mean = np.nan

        # CGM Glucose: nearest reading at window end
        if "cgm_glucose" in window_df.columns and len(window_df["cgm_glucose"].dropna()) > 0:
            cgm_val = float(window_df["cgm_glucose"].dropna().iloc[-1])
        else:
            cgm_val = np.nan

        # Quality flag
        if is_sensor_missing:
            q_flag = "SENSOR_MISSING"
        elif coverage_pct >= 85.0:
            q_flag = "GOOD"
        else:
            q_flag = "PARTIAL"

        rows.append({
            "timestamp": t_window_end,
            "participant_id": participant_id,
            "cgm_glucose": cgm_val,
            "steps_15m": steps_15m,
            "hr_mean_15m": hr_mean,
            "hr_std_15m": hr_std,
            "accel_mag_15m": accel_mean,
            "sensor_coverage_pct": coverage_pct,
            "sensor_missing": is_sensor_missing,
            "quality_flag": q_flag
        })

    return pd.DataFrame(rows)
