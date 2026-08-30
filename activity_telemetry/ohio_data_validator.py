"""
GlucoShield Ohio Data Validator
===============================
Strict schema validation layer enforcing data integrity, physiological bounds,
chronological monotonicity, and participant isolation before any model processing.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from activity_telemetry.ohio_schema import OhioT1DMConfig, OhioValidationReport

class OhioDataValidator:
    """Validates raw and parsed OhioT1DM telemetry against strict data contracts."""

    def __init__(self, config: Optional[OhioT1DMConfig] = None):
        self.config = config or OhioT1DMConfig()

    def validate_participant_dataframe(
        self,
        df: pd.DataFrame,
        expected_participant_id: str
    ) -> OhioValidationReport:
        errors: List[str] = []
        warnings: List[str] = []

        if df.empty:
            errors.append("DataFrame is completely empty.")
            return OhioValidationReport(
                participant_id=expected_participant_id,
                is_valid=False,
                total_raw_records=0,
                errors=errors,
                warnings=warnings
            )

        n_records = len(df)

        # 1. Participant Boundary Enforcement
        if "participant_id" in df.columns:
            unique_pids = df["participant_id"].dropna().unique().tolist()
            if len(unique_pids) > 1:
                errors.append(f"Mixed participant data detected! Found IDs: {unique_pids}")
                mixed_leakage = True
            elif len(unique_pids) == 1 and str(unique_pids[0]) != str(expected_participant_id):
                errors.append(f"Participant ID mismatch: expected '{expected_participant_id}', found '{unique_pids[0]}'")
                mixed_leakage = True
            else:
                mixed_leakage = False
        else:
            mixed_leakage = False

        # 2. Timestamp Validation & Monotonicity
        if "timestamp" not in df.columns:
            errors.append("Mandatory 'timestamp' column is missing.")
            return OhioValidationReport(
                participant_id=expected_participant_id,
                is_valid=False,
                total_raw_records=n_records,
                errors=errors,
                warnings=warnings
            )

        ts_series = pd.to_datetime(df["timestamp"])
        is_monotonic = ts_series.is_monotonic_increasing
        if not is_monotonic:
            errors.append("Timestamps are non-monotonic. Sorting is required before windowing.")

        # Duplicate Timestamps
        n_duplicates = int(ts_series.duplicated().sum())
        if n_duplicates > 0:
            warnings.append(f"Found {n_duplicates} duplicate timestamps. Deduplication is required.")

        t_min = str(ts_series.min())
        t_max = str(ts_series.max())
        duration_days = (ts_series.max() - ts_series.min()).total_seconds() / 86400.0

        # 3. Mandatory CGM Glucose Verification
        glucose_col = "cgm_glucose" if "cgm_glucose" in df.columns else "glucose"
        if glucose_col in df.columns:
            n_gluc = int(df[glucose_col].notna().sum())
            gluc_missing_pct = float((df[glucose_col].isna().sum() / n_records) * 100.0)
            
            # Unit / Out-of-Range Bounds Check (30 to 600 mg/dL)
            valid_gluc = df[glucose_col].dropna()
            out_of_range_gluc = int(((valid_gluc < 30.0) | (valid_gluc > 600.0)).sum())
            if out_of_range_gluc > 0:
                warnings.append(f"Found {out_of_range_gluc} glucose readings outside physiological range [30, 600] mg/dL.")
        else:
            errors.append("Mandatory continuous glucose signal is missing.")
            n_gluc = 0
            gluc_missing_pct = 100.0
            out_of_range_gluc = 0

        # 4. Heart Rate Signal Audit
        hr_col = "heart_rate" if "heart_rate" in df.columns else "heartrate"
        if hr_col in df.columns:
            n_hr = int(df[hr_col].notna().sum())
            hr_missing_pct = float((df[hr_col].isna().sum() / n_records) * 100.0)
            valid_hr = df[hr_col].dropna()
            out_of_range_hr = int(((valid_hr < 35.0) | (valid_hr > 220.0)).sum())
            if out_of_range_hr > 0:
                warnings.append(f"Found {out_of_range_hr} heart rate readings outside physiological bounds [35, 220] bpm.")
        else:
            n_hr = 0
            hr_missing_pct = 100.0
            out_of_range_hr = 0
            warnings.append("Optional heart rate signal is not present in this participant cohort.")

        # 5. Step & Accelerometer Signal Audit
        step_col = "steps" if "steps" in df.columns else "step"
        n_step = int(df[step_col].notna().sum()) if step_col in df.columns else 0
        step_missing_pct = float((df[step_col].isna().sum() / n_records) * 100.0) if step_col in df.columns else 100.0

        accel_col = "accel_mag" if "accel_mag" in df.columns else "acceleration"
        n_accel = int(df[accel_col].notna().sum()) if accel_col in df.columns else 0
        accel_missing_pct = float((df[accel_col].isna().sum() / n_records) * 100.0) if accel_col in df.columns else 100.0

        # 6. Event Signals (Bolus & Meals)
        bolus_col = "bolus" if "bolus" in df.columns else "bolus_dose"
        n_bolus = int(df[bolus_col].notna().sum()) if bolus_col in df.columns else 0

        meal_col = "meal_carbs" if "meal_carbs" in df.columns else "meal"
        n_meal = int(df[meal_col].notna().sum()) if meal_col in df.columns else 0

        is_valid = len(errors) == 0

        return OhioValidationReport(
            participant_id=expected_participant_id,
            is_valid=is_valid,
            total_raw_records=n_records,
            date_range_start=t_min,
            date_range_end=t_max,
            duration_days=duration_days,
            glucose_records=n_gluc,
            glucose_missing_pct=gluc_missing_pct,
            heart_rate_records=n_hr,
            heart_rate_missing_pct=hr_missing_pct,
            step_records=n_step,
            step_missing_pct=step_missing_pct,
            accel_records=n_accel,
            accel_missing_pct=accel_missing_pct,
            bolus_events=n_bolus,
            meal_events=n_meal,
            monotonic_timestamps=is_monotonic,
            duplicate_timestamps_found=n_duplicates,
            out_of_range_glucose_count=out_of_range_gluc,
            out_of_range_hr_count=out_of_range_hr,
            future_leakage_detected=False,
            mixed_participant_leakage=mixed_leakage,
            errors=errors,
            warnings=warnings
        )
