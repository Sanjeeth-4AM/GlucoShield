"""
GlucoShield API — Input Payload Preprocessor
============================================
Converts validated JSON time series and patient static profiles into the exact
frozen 22-channel dynamic and 9-channel static tensors required by GlucoShield V1.
Uses pre-saved frozen scalers without refitting.
"""

import os
import joblib
import torch
import numpy as np
import pandas as pd
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime, timedelta

from api.schemas import TimeStepReading, PatientStaticProfile
from decision_engine.safety import SafetyGuardrails

BASE_DIR = "D:/ML PROJECT"
META_DIR = os.path.join(BASE_DIR, "data", "metadata")
FEATURE_SCALER_PATH = os.path.join(META_DIR, "feature_scaler.joblib")
STATIC_SCALER_PATH = os.path.join(META_DIR, "static_scaler.joblib")

# Halflives in 15-min steps (matching build_final_dataset.py)
IOB_HALFLIFE_STEPS = 8   # ~2 hours
COB_HALFLIFE_STEPS = 4   # ~1 hour

DYNAMIC_COLS = [
    "glucose",
    "glucose_velocity",
    "glucose_accel",
    "glucose_roll_mean_1h",
    "glucose_roll_std_1h",
    "glucose_roll_min_1h",
    "glucose_roll_max_1h",
    "glucose_roll_mean_3h",
    "glucose_roll_std_3h",
    "glucose_roll_mean_6h",
    "sin_hour",
    "cos_hour",
    "is_night",
    "insulin_basal",
    "insulin_bolus",
    "insulin_total",
    "iob",
    "carbs_estimate_g",
    "meal_flag",
    "cob",
    "insulin_cum_2h",
    "carbs_cum_2h"
]

STATIC_COLS = [
    "age",
    "bmi",
    "hba1c",
    "glycated_albumin",
    "fasting_glucose",
    "fasting_c_peptide",
    "macrovascular_comp_count",
    "microvascular_comp_count",
    "is_t1dm"
]

class InputPayloadPreprocessor:
    """
    Standardized, frozen preprocessor for API inference requests.
    """
    def __init__(self):
        if not os.path.exists(FEATURE_SCALER_PATH) or not os.path.exists(STATIC_SCALER_PATH):
            raise FileNotFoundError(f"Required frozen scalers not found at {META_DIR}")
        
        self.feature_scaler = joblib.load(FEATURE_SCALER_PATH)
        self.static_scaler = joblib.load(STATIC_SCALER_PATH)

    def preprocess_forecast_input(
        self,
        readings: List[TimeStepReading],
        static_profile: Optional[PatientStaticProfile] = None
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, List[str]]:
        """
        Converts 96 TimeStepReadings into model input tensors.
        
        Returns:
          dynamic_seq_scaled: (1, 96, 22) float32
          dynamic_seq_raw:    (1, 96, 22) float32
          static_feat_scaled: (1, 9) float32
          static_feat_raw:    (1, 9) float32
          safety_warnings:    List of string warnings
        """
        if len(readings) != 96:
            raise ValueError(f"Expected exactly 96 15-minute readings (24 hours), received {len(readings)}")

        # 1. Build DataFrame
        records = []
        base_time = datetime(2026, 1, 1, 0, 0, 0)
        
        for idx, r in enumerate(readings):
            ts = None
            if r.timestamp:
                try:
                    ts = pd.to_datetime(r.timestamp)
                except:
                    ts = base_time + timedelta(minutes=15 * idx)
            else:
                ts = base_time + timedelta(minutes=15 * idx)

            records.append({
                "timestamp": ts,
                "glucose": float(np.clip(r.cgm_glucose, 20.0, 600.0)),
                "insulin_bolus": float(max(0.0, r.insulin_bolus)),
                "insulin_basal": float(max(0.0, r.insulin_basal)),
                "insulin_total": float(max(0.0, r.insulin_bolus + r.insulin_basal)),
                "carbs_estimate_g": float(max(0.0, r.meal_carbs)),
                "meal_flag": 1.0 if r.meal_carbs > 0 else 0.0
            })

        df = pd.DataFrame(records)

        # 2. Compute Causal Dynamic Features
        df["glucose_velocity"] = df["glucose"].diff().fillna(0.0)
        df["glucose_accel"] = df["glucose_velocity"].diff().fillna(0.0)

        df["glucose_roll_mean_1h"] = df["glucose"].rolling(window=4, min_periods=1).mean()
        df["glucose_roll_std_1h"] = df["glucose"].rolling(window=4, min_periods=1).std().fillna(0.0)
        df["glucose_roll_min_1h"] = df["glucose"].rolling(window=4, min_periods=1).min()
        df["glucose_roll_max_1h"] = df["glucose"].rolling(window=4, min_periods=1).max()

        df["glucose_roll_mean_3h"] = df["glucose"].rolling(window=12, min_periods=1).mean()
        df["glucose_roll_std_3h"] = df["glucose"].rolling(window=12, min_periods=1).std().fillna(0.0)
        df["glucose_roll_mean_6h"] = df["glucose"].rolling(window=24, min_periods=1).mean()

        hours = df["timestamp"].dt.hour
        minutes = df["timestamp"].dt.minute
        hour_float = hours + minutes / 60.0
        df["sin_hour"] = np.sin(2 * np.pi * hour_float / 24.0)
        df["cos_hour"] = np.cos(2 * np.pi * hour_float / 24.0)
        df["is_night"] = ((hours >= 23) | (hours < 6)).astype(float)

        df["iob"] = df["insulin_total"].ewm(halflife=IOB_HALFLIFE_STEPS, adjust=False).mean()
        df["cob"] = df["carbs_estimate_g"].ewm(halflife=COB_HALFLIFE_STEPS, adjust=False).mean()

        df["insulin_cum_2h"] = df["insulin_total"].rolling(window=8, min_periods=1).sum()
        df["carbs_cum_2h"] = df["carbs_estimate_g"].rolling(window=8, min_periods=1).sum()

        raw_dynamic = df[DYNAMIC_COLS].values.astype(np.float32)  # (96, 22)

        # 3. Apply Frozen Feature Scaler (RobustScaler)
        scaled_dynamic = self.feature_scaler.transform(raw_dynamic).astype(np.float32)

        # 4. Build Static Features
        p = static_profile or PatientStaticProfile()
        raw_static = np.array([[
            p.age,
            p.bmi,
            p.hba1c,
            p.glycated_albumin,
            p.fasting_glucose,
            p.fasting_c_peptide,
            p.macrovascular_comp_count,
            p.microvascular_comp_count,
            p.is_t1dm
        ]], dtype=np.float32)  # (1, 9)

        scaled_static = self.static_scaler.transform(raw_static).astype(np.float32)

        # 5. Safety Validation
        current_g = float(raw_dynamic[-1, 0])
        max_bolus = float(df["insulin_bolus"].max())
        max_carbs = float(df["carbs_estimate_g"].max())
        safety_warns = SafetyGuardrails.validate_inputs(
            current_glucose=current_g,
            proposed_carbs=max_carbs if max_carbs > 0 else None,
            proposed_bolus=max_bolus if max_bolus > 0 else None
        )

        t_dynamic_scaled = torch.from_numpy(scaled_dynamic).unsqueeze(0)  # (1, 96, 22)
        t_dynamic_raw = torch.from_numpy(raw_dynamic).unsqueeze(0)        # (1, 96, 22)
        t_static_scaled = torch.from_numpy(scaled_static)                 # (1, 9)
        t_static_raw = torch.from_numpy(raw_static)                       # (1, 9)

        return t_dynamic_scaled, t_dynamic_raw, t_static_scaled, t_static_raw, safety_warns
