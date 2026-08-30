"""
GlucoShield Telemetry Missing Data & Quality Audit
==================================================
Audits sensor coverage, gap distributions, duplicate timestamps, and data integrity.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from activity_telemetry.schemas import ParticipantCoverageReport

def clean_raw_timestamps(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans raw telemetry by sorting timestamps and removing exact duplicates.
    """
    if df_raw.empty:
        return df_raw

    df = df_raw.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    
    # Sort chronologically
    df = df.sort_values("timestamp")
    
    # Deduplicate timestamps keeping the first valid record
    df = df.drop_duplicates(subset=["timestamp"], keep="first").reset_index(drop=True)
    return df


def audit_participant_quality(
    df_15m: pd.DataFrame,
    participant_id: str
) -> ParticipantCoverageReport:
    """
    Generates structured quality report for a 15-minute aligned participant DataFrame.
    """
    if df_15m.empty:
        return ParticipantCoverageReport(
            participant_id=participant_id,
            total_duration_hours=0.0,
            total_15m_windows=0,
            valid_cgm_windows=0,
            valid_wearable_windows=0,
            cgm_coverage_pct=0.0,
            wearable_coverage_pct=0.0,
            joint_coverage_pct=0.0,
            detected_active_windows=0,
            active_time_pct=0.0
        )

    n_total = len(df_15m)
    tot_hours = n_total * 0.25  # 15 mins = 0.25 hrs

    valid_cgm = df_15m["cgm_glucose"].notna().sum()
    valid_wearable = (df_15m["sensor_missing"] == 0).sum()
    joint_valid = (df_15m["cgm_glucose"].notna() & (df_15m["sensor_missing"] == 0)).sum()
    
    active_windows = (df_15m["is_active_15m"] == 1).sum()

    cgm_cov = (valid_cgm / n_total) * 100.0
    wear_cov = (valid_wearable / n_total) * 100.0
    joint_cov = (joint_valid / n_total) * 100.0
    active_pct = (active_windows / max(1, valid_wearable)) * 100.0

    # Resting vs Active HR
    resting_mask = (df_15m["is_active_15m"] == 0) & (df_15m["hr_mean_15m"].notna())
    active_mask = (df_15m["is_active_15m"] == 1) & (df_15m["hr_mean_15m"].notna())

    mean_rest_hr = float(df_15m.loc[resting_mask, "hr_mean_15m"].mean()) if resting_mask.sum() > 0 else None
    mean_act_hr = float(df_15m.loc[active_mask, "hr_mean_15m"].mean()) if active_mask.sum() > 0 else None

    return ParticipantCoverageReport(
        participant_id=participant_id,
        total_duration_hours=round(tot_hours, 1),
        total_15m_windows=int(n_total),
        valid_cgm_windows=int(valid_cgm),
        valid_wearable_windows=int(valid_wearable),
        cgm_coverage_pct=round(cgm_cov, 1),
        wearable_coverage_pct=round(wear_cov, 1),
        joint_coverage_pct=round(joint_cov, 1),
        detected_active_windows=int(active_windows),
        active_time_pct=round(active_pct, 1),
        mean_resting_hr=round(mean_rest_hr, 1) if mean_rest_hr is not None else None,
        mean_active_hr=round(mean_act_hr, 1) if mean_act_hr is not None else None
    )
