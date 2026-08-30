"""
GlucoShield Wearable Dataset Adapters
=====================================
Modular adapters decoupling dataset-specific file formats (D1NAMO, OhioT1DM, Mock)
from the standardized internal telemetry representation.
"""

import os
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple

class BaseWearableAdapter(ABC):
    """Abstract interface for wearable telemetry dataset adapters."""

    @property
    @abstractmethod
    def dataset_name(self) -> str:
        pass

    @abstractmethod
    def list_participants(self, base_dir: str) -> List[str]:
        """Returns list of available participant identifiers."""
        pass

    @abstractmethod
    def load_participant_telemetry(
        self,
        participant_id: str,
        base_dir: str
    ) -> pd.DataFrame:
        """
        Loads raw multi-modal time series for a participant.
        Must return DataFrame with columns:
          ['timestamp', 'cgm_glucose', 'heart_rate', 'accel_x', 'accel_y', 'accel_z', 'steps']
        """
        pass


class D1NAMOAdapter(BaseWearableAdapter):
    """
    Adapter for the D1NAMO dataset (Zenodo DOI: 10.5281/zenodo.1421616).
    Handles Zephyr BioHarness _Summary.csv, _Accel.csv, and glucose.csv.
    """
    @property
    def dataset_name(self) -> str:
        return "D1NAMO"

    def list_participants(self, base_dir: str) -> List[str]:
        diab_dir = os.path.join(base_dir, "diabetes_subset")
        if not os.path.exists(diab_dir):
            diab_dir = base_dir
        if not os.path.exists(diab_dir):
            return []
        
        pts = [d for d in os.listdir(diab_dir) if os.path.isdir(os.path.join(diab_dir, d)) and not d.startswith(".")]
        return sorted(pts)

    def load_participant_telemetry(
        self,
        participant_id: str,
        base_dir: str
    ) -> pd.DataFrame:
        pt_dir = os.path.join(base_dir, "diabetes_subset", participant_id)
        if not os.path.exists(pt_dir):
            pt_dir = os.path.join(base_dir, participant_id)
        if not os.path.exists(pt_dir):
            raise FileNotFoundError(f"D1NAMO participant directory not found: {pt_dir}")

        # 1. Load Glucose
        gluc_path = os.path.join(pt_dir, "glucose.csv")
        if not os.path.exists(gluc_path):
            gluc_path = os.path.join(pt_dir, "Glucose.csv")

        df_gluc = pd.DataFrame()
        if os.path.exists(gluc_path):
            df_gluc = pd.read_csv(gluc_path)
            # D1NAMO glucose timestamp column
            ts_col = [c for c in df_gluc.columns if "time" in c.lower() or "date" in c.lower()][0]
            val_col = [c for c in df_gluc.columns if "gluc" in c.lower() or "value" in c.lower() or "cgm" in c.lower()][0]
            
            df_gluc["timestamp"] = pd.to_datetime(df_gluc[ts_col])
            # Check unit: if mean < 30, it is in mmol/L -> convert to mg/dL (* 18.0182)
            mean_v = df_gluc[val_col].dropna().mean()
            if mean_v < 35.0:
                df_gluc["cgm_glucose"] = df_gluc[val_col] * 18.0182
            else:
                df_gluc["cgm_glucose"] = df_gluc[val_col]
            df_gluc = df_gluc[["timestamp", "cgm_glucose"]].dropna(subset=["timestamp"])

        # 2. Load Summary (Heart Rate, Activity)
        sum_files = [f for f in os.listdir(pt_dir) if "summary" in f.lower() and f.endswith(".csv")]
        df_sum = pd.DataFrame()
        if sum_files:
            sum_path = os.path.join(pt_dir, sum_files[0])
            df_sum = pd.read_csv(sum_path)
            ts_col = [c for c in df_sum.columns if "time" in c.lower() or "date" in c.lower()][0]
            df_sum["timestamp"] = pd.to_datetime(df_sum[ts_col])
            
            # Map HR
            hr_cols = [c for c in df_sum.columns if "hr" in c.lower() or "heart" in c.lower() or "pulse" in c.lower()]
            df_sum["heart_rate"] = df_sum[hr_cols[0]] if hr_cols else np.nan
            
            # Map Activity / VMU
            act_cols = [c for c in df_sum.columns if "activity" in c.lower() or "vmu" in c.lower() or "accel" in c.lower()]
            df_sum["activity_vmu"] = df_sum[act_cols[0]] if act_cols else np.nan
            df_sum = df_sum[["timestamp", "heart_rate", "activity_vmu"]].dropna(subset=["timestamp"])

        # 3. Load Accelerometry (if present)
        acc_files = [f for f in os.listdir(pt_dir) if "accel" in f.lower() and f.endswith(".csv")]
        df_acc = pd.DataFrame()
        if acc_files:
            acc_path = os.path.join(pt_dir, acc_files[0])
            # Read first 100k rows if very large
            df_acc = pd.read_csv(acc_path, nrows=500000)
            ts_col = [c for c in df_acc.columns if "time" in c.lower() or "date" in c.lower()][0]
            df_acc["timestamp"] = pd.to_datetime(df_acc[ts_col])
            
            x_col = [c for c in df_acc.columns if "x" in c.lower()][0]
            y_col = [c for c in df_acc.columns if "y" in c.lower()][0]
            z_col = [c for c in df_acc.columns if "z" in c.lower()][0]
            df_acc["accel_x"] = df_acc[x_col]
            df_acc["accel_y"] = df_acc[y_col]
            df_acc["accel_z"] = df_acc[z_col]
            df_acc = df_acc[["timestamp", "accel_x", "accel_y", "accel_z"]].dropna(subset=["timestamp"])

        # Merge on Timestamp
        if not df_sum.empty:
            merged = df_sum
            if not df_gluc.empty:
                merged = pd.merge_asof(merged.sort_values("timestamp"), df_gluc.sort_values("timestamp"),
                                       on="timestamp", direction="nearest", tolerance=pd.Timedelta("15min"))
            if not df_acc.empty:
                merged = pd.merge_asof(merged.sort_values("timestamp"), df_acc.sort_values("timestamp"),
                                       on="timestamp", direction="nearest", tolerance=pd.Timedelta("1sec"))
        elif not df_gluc.empty:
            merged = df_gluc
            merged["heart_rate"] = np.nan
            merged["accel_x"] = np.nan
            merged["accel_y"] = np.nan
            merged["accel_z"] = np.nan
        else:
            merged = pd.DataFrame(columns=["timestamp", "cgm_glucose", "heart_rate", "accel_x", "accel_y", "accel_z", "steps"])

        if "steps" not in merged.columns:
            # Approximate steps from activity VMU if available
            if "activity_vmu" in merged.columns:
                merged["steps"] = (merged["activity_vmu"] * 1.5).fillna(0.0)
            else:
                merged["steps"] = np.nan

        return merged.sort_values("timestamp").reset_index(drop=True)


class MockWearableAdapter(BaseWearableAdapter):
    """
    Deterministic synthetic multi-modal wearable generator for testing and CI/CD.
    Generates realistic 5-day continuous records with workout episodes and sleep.
    """
    def __init__(self, num_days: int = 5, seed: int = 42):
        self.num_days = num_days
        self.seed = seed

    @property
    def dataset_name(self) -> str:
        return "MockWearableDataset"

    def list_participants(self, base_dir: str = "") -> List[str]:
        return ["MOCK_001", "MOCK_002", "MOCK_003"]

    def load_participant_telemetry(
        self,
        participant_id: str,
        base_dir: str = ""
    ) -> pd.DataFrame:
        np.random.seed(self.seed + hash(participant_id) % 1000)
        
        start_ts = pd.to_datetime("2026-06-01 00:00:00")
        # 1 Hz timestamps for 1 day = 86,400 samples
        n_samples = self.num_days * 86400 // 5  # 5-sec resolution for efficient testing
        ts = pd.date_range(start_ts, periods=n_samples, freq="5s")
        
        hours = np.array(ts.hour + ts.minute / 60.0)
        days = np.array(ts.day)
        
        # Circadian baseline HR: 60 bpm nocturnal, 75 bpm diurnal
        base_hr = 68.0 + 8.0 * np.sin(2 * np.pi * (hours - 8) / 24.0)
        
        # Inject workout episodes (e.g. at 17:00 each day for 45 mins)
        is_workout = ((hours >= 17.0) & (hours <= 17.75)).astype(float)
        workout_hr_boost = is_workout * 65.0  # Spikes HR to 140-150 bpm
        
        noise_hr = np.random.normal(0, 2.0, size=n_samples)
        hr = np.clip(base_hr + workout_hr_boost + noise_hr, 45.0, 185.0).astype(float)
        
        # Steps
        steps = np.where(is_workout > 0, np.random.poisson(12, size=n_samples),
                         np.where(hours >= 8.0, np.random.poisson(1, size=n_samples), 0)).astype(float)
        
        # Accelerometer (g): 1.0g gravity + motion
        accel_mag = np.where(is_workout > 0, 1.0 + np.random.uniform(0.3, 1.2, size=n_samples),
                             1.0 + np.random.uniform(0.01, 0.08, size=n_samples))
        accel_x = (np.random.normal(0, 0.1, size=n_samples) + (is_workout * 0.4)).astype(float)
        accel_y = np.random.normal(0, 0.1, size=n_samples).astype(float)
        accel_z = accel_mag.astype(float)
        
        # Glucose: 120 baseline, postprandial spikes, drop after workout
        base_gluc = 130.0 + 20.0 * np.sin(2 * np.pi * (hours - 12) / 24.0)
        workout_gluc_drop = is_workout * -25.0
        noise_gluc = np.random.normal(0, 3.0, size=n_samples)
        glucose = np.clip(base_gluc + workout_gluc_drop + noise_gluc, 65.0, 220.0).astype(float)

        # Inject some realistic sensor missingness (e.g. 2 hours off-wrist on Day 3)
        off_wrist_mask = (days == start_ts.day + 2) & (hours >= 13.0) & (hours <= 15.0)
        hr[off_wrist_mask] = np.nan
        accel_x[off_wrist_mask] = np.nan
        accel_y[off_wrist_mask] = np.nan
        accel_z[off_wrist_mask] = np.nan
        steps[off_wrist_mask] = 0.0

        df = pd.DataFrame({
            "timestamp": ts,
            "cgm_glucose": glucose,
            "heart_rate": hr,
            "accel_x": accel_x,
            "accel_y": accel_y,
            "accel_z": accel_z,
            "steps": steps
        })
        return df
