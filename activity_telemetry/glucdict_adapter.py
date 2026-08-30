"""
GlucoShield — Glucdict Wearable Dataset Adapter
===============================================
Modular, isolated adapter for the Glucdict dataset (Figshare DOI: 10.6084/m9.figshare.25939312).
Parses Dexcom G6 CGM files and Mobvoi TicWatch Pro multi-sensor CSV streams into standardized
causal 15-minute telemetry DataFrames.
"""

import os
import csv
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from activity_telemetry.dataset_adapter import BaseWearableAdapter

class GlucdictAdapter(BaseWearableAdapter):
    """
    Adapter for the Glucdict multi-modal dataset.
    
    Sensors mapped from TicWatch Pro:
      - Sensor 1: 3-Axis Accelerometer (x, y, z in m/s^2 or g)
      - Sensor 4: Gyroscope
      - Sensor 18: Step Detector / Counter
      - Sensor 21: Heart Rate (bpm)
    """

    def __init__(self, raw_root: Optional[str] = None):
        if raw_root is None:
            self._raw_root = "D:/ML PROJECT/data/raw/Glucdict/Glucdict Dataset"
        else:
            self._raw_root = raw_root

    @property
    def dataset_name(self) -> str:
        return "Glucdict"

    def list_participants(self, base_dir: Optional[str] = None) -> List[str]:
        root = base_dir or self._raw_root
        if not os.path.exists(root):
            # Check if one level down or parent
            alt = os.path.join(root, "Glucdict Dataset")
            if os.path.exists(alt):
                root = alt
            else:
                return []

        pts = []
        for d in sorted(os.listdir(root)):
            pdir = os.path.join(root, d)
            if os.path.isdir(pdir) and d.startswith("User"):
                # Must contain Glucose/
                gdir = os.path.join(pdir, "Glucose")
                if os.path.exists(gdir):
                    pts.append(d)
        return pts

    def load_raw_cgm(self, participant_id: str, base_dir: Optional[str] = None) -> pd.DataFrame:
        """Loads and cleans raw Dexcom G6 CGM for participant."""
        root = base_dir or self._raw_root
        pdir = os.path.join(root, participant_id)
        if not os.path.exists(pdir):
            pdir = os.path.join(root, "Glucdict Dataset", participant_id)
        
        cgm_path = os.path.join(pdir, "Glucose", f"CGM_{participant_id}.csv")
        if not os.path.exists(cgm_path):
            raise FileNotFoundError(f"CGM file not found: {cgm_path}")

        df = pd.read_csv(cgm_path)
        # Parse timestamp
        ts_col = "Timestamp (YYYY-MM-DDThh:mm:ss)"
        val_col = "Glucose Value (mg/dL)"
        if ts_col not in df.columns or val_col not in df.columns:
            raise ValueError(f"Unexpected CGM columns in {cgm_path}: {list(df.columns)}")

        df["timestamp"] = pd.to_datetime(df[ts_col], errors="coerce")
        df["cgm_glucose"] = pd.to_numeric(df[val_col], errors="coerce")
        
        df = df.dropna(subset=["timestamp", "cgm_glucose"]).sort_values("timestamp")
        df = df.drop_duplicates(subset=["timestamp"], keep="last")
        return df[["timestamp", "cgm_glucose"]]

    def load_raw_watch_telemetry(self, participant_id: str, base_dir: Optional[str] = None) -> Dict[str, pd.DataFrame]:
        """Loads raw TicWatch PPG heart rate, steps, and 3D accelerometer."""
        root = base_dir or self._raw_root
        pdir = os.path.join(root, participant_id)
        if not os.path.exists(pdir):
            pdir = os.path.join(root, "Glucdict Dataset", participant_id)

        wdir = os.path.join(pdir, "Watch")
        if not os.path.exists(wdir):
            return {
                "heart_rate": pd.DataFrame(columns=["timestamp", "heart_rate"]),
                "steps": pd.DataFrame(columns=["timestamp", "steps"]),
                "accel": pd.DataFrame(columns=["timestamp", "accel_x", "accel_y", "accel_z"])
            }

        wfiles = [os.path.join(wdir, f) for f in os.listdir(wdir) if f.endswith(".csv")]
        
        hr_records = []
        step_records = []
        accel_records = []

        for wf in wfiles:
            with open(wf, "r", encoding="utf-8", errors="ignore") as fp:
                reader = csv.reader(fp)
                for row in reader:
                    if not row or len(row) < 3:
                        continue
                    try:
                        sid = int(row[0])
                        ts_ms = int(row[1])
                        
                        if sid == 21:  # Heart Rate (bpm)
                            hr_val = float(row[2])
                            if 30.0 <= hr_val <= 230.0:
                                hr_records.append((ts_ms, hr_val))
                        elif sid == 18:  # Step Detector
                            step_val = float(row[2])
                            if step_val > 0:
                                step_records.append((ts_ms, step_val))
                        elif sid == 1:  # Accelerometer
                            if len(row) >= 5:
                                ax, ay, az = float(row[2]), float(row[3]), float(row[4])
                                accel_records.append((ts_ms, ax, ay, az))
                    except (ValueError, IndexError):
                        continue

        # Build DataFrames
        if hr_records:
            df_hr = pd.DataFrame(hr_records, columns=["ts_ms", "heart_rate"])
            df_hr["timestamp"] = pd.to_datetime(df_hr["ts_ms"], unit="ms", utc=True).dt.tz_localize(None)
            df_hr = df_hr.sort_values("timestamp")[["timestamp", "heart_rate"]]
        else:
            df_hr = pd.DataFrame(columns=["timestamp", "heart_rate"])

        if step_records:
            df_step = pd.DataFrame(step_records, columns=["ts_ms", "steps"])
            df_step["timestamp"] = pd.to_datetime(df_step["ts_ms"], unit="ms", utc=True).dt.tz_localize(None)
            df_step = df_step.sort_values("timestamp")[["timestamp", "steps"]]
        else:
            df_step = pd.DataFrame(columns=["timestamp", "steps"])

        if accel_records:
            df_accel = pd.DataFrame(accel_records, columns=["ts_ms", "accel_x", "accel_y", "accel_z"])
            df_accel["timestamp"] = pd.to_datetime(df_accel["ts_ms"], unit="ms", utc=True).dt.tz_localize(None)
            df_accel = df_accel.sort_values("timestamp")[["timestamp", "accel_x", "accel_y", "accel_z"]]
        else:
            df_accel = pd.DataFrame(columns=["timestamp", "accel_x", "accel_y", "accel_z"])

        return {
            "heart_rate": df_hr,
            "steps": df_step,
            "accel": df_accel
        }

    def load_participant_telemetry(
        self,
        participant_id: str,
        base_dir: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Loads and aligns multi-modal streams for a single participant into 15m grid.
        Returns standardized DataFrame with columns:
          ['timestamp', 'cgm_glucose', 'heart_rate', 'accel_x', 'accel_y', 'accel_z', 'steps']
        """
        df_cgm = self.load_raw_cgm(participant_id, base_dir=base_dir)
        watch_data = self.load_raw_watch_telemetry(participant_id, base_dir=base_dir)

        if df_cgm.empty:
            raise ValueError(f"No valid CGM readings found for participant {participant_id}")

        # Construct regular 15-minute grid over the CGM time span
        t_start = df_cgm["timestamp"].min().floor("15min")
        t_end = df_cgm["timestamp"].max().ceil("15min")
        grid = pd.date_range(start=t_start, end=t_end, freq="15min")

        aligned_df = pd.DataFrame({"timestamp": grid})
        
        # 1. CGM aggregation (mean / nearest in (t - 15m, t])
        df_cgm = df_cgm.sort_values("timestamp")
        cgm_resampled = pd.merge_asof(
            aligned_df,
            df_cgm,
            on="timestamp",
            direction="backward",
            tolerance=pd.Timedelta(minutes=15)
        )
        aligned_df["cgm_glucose"] = cgm_resampled["cgm_glucose"]

        # 2. Heart Rate (mean in (t - 15m, t])
        df_hr = watch_data["heart_rate"]
        if not df_hr.empty:
            df_hr["grid_ts"] = df_hr["timestamp"].dt.ceil("15min")
            hr_agg = df_hr.groupby("grid_ts")["heart_rate"].mean().reset_index()
            hr_agg.rename(columns={"grid_ts": "timestamp"}, inplace=True)
            aligned_df = pd.merge(aligned_df, hr_agg, on="timestamp", how="left")
        else:
            aligned_df["heart_rate"] = np.nan

        # 3. Steps (sum in (t - 15m, t])
        df_steps = watch_data["steps"]
        if not df_steps.empty:
            df_steps["grid_ts"] = df_steps["timestamp"].dt.ceil("15min")
            steps_agg = df_steps.groupby("grid_ts")["steps"].sum().reset_index()
            steps_agg.rename(columns={"grid_ts": "timestamp"}, inplace=True)
            aligned_df = pd.merge(aligned_df, steps_agg, on="timestamp", how="left")
            aligned_df["steps"] = aligned_df["steps"].fillna(0.0)
        else:
            aligned_df["steps"] = 0.0

        # 4. Accelerometer (mean x, y, z in (t - 15m, t])
        df_accel = watch_data["accel"]
        if not df_accel.empty:
            df_accel["grid_ts"] = df_accel["timestamp"].dt.ceil("15min")
            accel_agg = df_accel.groupby("grid_ts")[["accel_x", "accel_y", "accel_z"]].mean().reset_index()
            accel_agg.rename(columns={"grid_ts": "timestamp"}, inplace=True)
            aligned_df = pd.merge(aligned_df, accel_agg, on="timestamp", how="left")
        else:
            aligned_df["accel_x"] = np.nan
            aligned_df["accel_y"] = np.nan
            aligned_df["accel_z"] = np.nan

        # Sort and ensure standardized columns
        aligned_df = aligned_df.sort_values("timestamp").reset_index(drop=True)
        cols = ["timestamp", "cgm_glucose", "heart_rate", "accel_x", "accel_y", "accel_z", "steps"]
        return aligned_df[cols]
