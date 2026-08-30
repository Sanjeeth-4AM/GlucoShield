"""
GlucoShield Activity Detection & Episode Extraction
===================================================
Rule-based, transparent activity gating and workout episode clustering.
"""

import pandas as pd
import numpy as np
from typing import List, Optional
from activity_telemetry.schemas import ActivityEpisode

def detect_activity_states(
    df: pd.DataFrame,
    step_threshold: float = 150.0,
    hr_reserve_threshold: float = 25.0,
    accel_threshold: float = 1.15
) -> pd.DataFrame:
    """
    Applies transparent rule-based activity classification.
    
    is_active_15m = 1 if:
      (steps_15m >= step_threshold) OR
      (hr_reserve_pct >= hr_reserve_threshold) OR
      (accel_mag_15m >= accel_threshold)
      
    exercise_onset_flag = 1 on the leading edge (0 -> 1 transition).
    """
    if df.empty:
        return df

    out = df.copy()
    
    cond_steps = out["steps_15m"].fillna(0) >= step_threshold
    cond_hr = out["hr_reserve_pct"].fillna(0) >= hr_reserve_threshold
    cond_accel = out["accel_mag_15m"].fillna(0) >= accel_threshold
    
    is_active = (cond_steps | cond_hr | cond_accel) & (out["sensor_missing"] == 0)
    out["is_active_15m"] = is_active.astype(int)

    # Exercise Onset: 1 on 0 -> 1 transitions
    active_arr = out["is_active_15m"].values
    onset = np.zeros(len(active_arr), dtype=int)
    for i in range(len(active_arr)):
        if active_arr[i] == 1 and (i == 0 or active_arr[i - 1] == 0):
            onset[i] = 1
    out["exercise_onset_flag"] = onset

    return out


def extract_activity_episodes(
    df: pd.DataFrame,
    min_duration_minutes: int = 15
) -> List[ActivityEpisode]:
    """
    Groups contiguous active 15-minute windows into discrete workout episodes.
    """
    if df.empty or "is_active_15m" not in df.columns:
        return []

    episodes = []
    active_mask = df["is_active_15m"].values
    n = len(df)
    
    i = 0
    while i < n:
        if active_mask[i] == 1:
            start_idx = i
            while i < n and active_mask[i] == 1:
                i += 1
            end_idx = i - 1

            chunk = df.iloc[start_idx : end_idx + 1]
            duration_m = len(chunk) * 15.0

            if duration_m >= min_duration_minutes:
                pid = str(chunk["participant_id"].iloc[0])
                t_start = str(chunk["timestamp"].iloc[0])
                t_end = str(chunk["timestamp"].iloc[-1])

                mean_hr = float(chunk["hr_mean_15m"].dropna().mean()) if chunk["hr_mean_15m"].notna().sum() > 0 else 0.0
                peak_hr = float(chunk["hr_mean_15m"].dropna().max()) if chunk["hr_mean_15m"].notna().sum() > 0 else 0.0
                tot_steps = float(chunk["steps_15m"].dropna().sum())
                mean_accel = float(chunk["accel_mag_15m"].dropna().mean()) if chunk["accel_mag_15m"].notna().sum() > 0 else 1.0

                # Pre and Post Glucose
                pre_idx = max(0, start_idx - 1)
                post_idx = min(n - 1, end_idx + 1)
                
                pre_g = float(df["cgm_glucose"].iloc[pre_idx]) if pd.notna(df["cgm_glucose"].iloc[pre_idx]) else None
                post_g = float(df["cgm_glucose"].iloc[post_idx]) if pd.notna(df["cgm_glucose"].iloc[post_idx]) else None
                delta_g = (post_g - pre_g) if (pre_g is not None and post_g is not None) else None

                episodes.append(ActivityEpisode(
                    participant_id=pid,
                    start_timestamp=t_start,
                    end_timestamp=t_end,
                    duration_minutes=duration_m,
                    mean_hr=round(mean_hr, 1),
                    peak_hr=round(peak_hr, 1),
                    total_steps=round(tot_steps, 1),
                    mean_accel=round(mean_accel, 3),
                    pre_glucose=round(pre_g, 1) if pre_g is not None else None,
                    post_glucose=round(post_g, 1) if post_g is not None else None,
                    glucose_delta=round(delta_g, 1) if delta_g is not None else None
                ))
        else:
            i += 1

    return episodes
