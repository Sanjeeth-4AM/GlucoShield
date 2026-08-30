"""
GlucoShield — Comprehensive Cohort Eligibility & Temporal Overlap Audit
========================================================================
Audits all 13 discovered Glucdict participants, computing exact timestamp
ranges, duration in days, sensor counts, and modality temporal overlap.
"""

import os
import csv
import json
import pandas as pd
import numpy as np
from datetime import datetime

BASE_DIR = "D:/ML PROJECT"
RAW_ROOT = os.path.join(BASE_DIR, "data", "raw", "Glucdict", "Glucdict Dataset")
RESULTS_DIR = os.path.join(BASE_DIR, "activity_telemetry", "experiments", "results")

def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    users = sorted([d for d in os.listdir(RAW_ROOT) if os.path.isdir(os.path.join(RAW_ROOT, d)) and d.startswith("User")])
    print(f"Auditing {len(users)} discovered participants: {users}\n")

    audit_results = []

    for u in users:
        upath = os.path.join(RAW_ROOT, u)

        # 1. CGM
        cgm_p = os.path.join(upath, "Glucose", f"CGM_{u}.csv")
        cgm_present = os.path.exists(cgm_p)
        cgm_start, cgm_end, cgm_days, cgm_valid_rows = None, None, 0.0, 0
        if cgm_present:
            cgm_df = pd.read_csv(cgm_p)
            cgm_df["ts"] = pd.to_datetime(cgm_df["Timestamp (YYYY-MM-DDThh:mm:ss)"], errors="coerce")
            cgm_df["val"] = pd.to_numeric(cgm_df["Glucose Value (mg/dL)"], errors="coerce")
            valid_cgm = cgm_df.dropna(subset=["ts", "val"]).sort_values("ts")
            cgm_valid_rows = len(valid_cgm)
            if cgm_valid_rows > 0:
                cgm_start = valid_cgm["ts"].min()
                cgm_end = valid_cgm["ts"].max()
                cgm_days = (cgm_end - cgm_start).total_seconds() / 86400.0

        # 2. Watch
        wdir = os.path.join(upath, "Watch")
        wfiles = [os.path.join(wdir, f) for f in os.listdir(wdir) if f.endswith(".csv")] if os.path.exists(wdir) else []

        hr_count, step_count, accel_count = 0, 0, 0
        w_min_ts, w_max_ts = float("inf"), 0

        for wf in wfiles:
            with open(wf, "r", encoding="utf-8", errors="ignore") as fp:
                reader = csv.reader(fp)
                for row in reader:
                    if not row or len(row) < 3:
                        continue
                    try:
                        sid = int(row[0])
                        ts_ms = int(row[1])
                        if ts_ms < w_min_ts:
                            w_min_ts = ts_ms
                        if ts_ms > w_max_ts:
                            w_max_ts = ts_ms
                        if sid == 21:
                            hr_count += 1
                        elif sid == 18:
                            step_count += 1
                        elif sid == 1:
                            accel_count += 1
                    except (ValueError, IndexError):
                        continue

        watch_present = len(wfiles) > 0 and (hr_count > 0 or step_count > 0 or accel_count > 0)
        w_start, w_end, w_days = None, None, 0.0
        if w_min_ts != float("inf") and w_max_ts != 0:
            w_start = pd.to_datetime(w_min_ts, unit="ms", utc=True).tz_localize(None)
            w_end = pd.to_datetime(w_max_ts, unit="ms", utc=True).tz_localize(None)
            w_days = (w_end - w_start).total_seconds() / 86400.0

        # 3. Temporal Overlap
        overlap_start, overlap_end, overlap_hours = None, None, 0.0
        if cgm_start is not None and w_start is not None:
            o_s = max(cgm_start, w_start)
            o_e = min(cgm_end, w_end)
            if o_e > o_s:
                overlap_start = o_s
                overlap_end = o_e
                overlap_hours = (o_e - o_s).total_seconds() / 3600.0

        usable_15m_windows = int(overlap_hours * 4) if overlap_hours > 0 else 0

        # Eligibility criteria:
        # 1. CGM valid readings >= 1,000 (~3.5 days minimum)
        # 2. Heart rate readings >= 10,000
        # 3. Accelerometer readings >= 100,000
        # 4. Step detector readings >= 1,000
        # 5. Continuous temporal overlap >= 72.0 hours (3 full days)
        is_eligible = True
        exclusion_reasons = []

        if not cgm_present or cgm_valid_rows < 1000:
            is_eligible = False
            exclusion_reasons.append(f"Insufficient CGM rows ({cgm_valid_rows})")
        if hr_count < 10000:
            is_eligible = False
            exclusion_reasons.append(f"Insufficient HR rows ({hr_count})")
        if accel_count < 100000:
            is_eligible = False
            exclusion_reasons.append(f"Insufficient Accel rows ({accel_count})")
        if step_count < 1000:
            is_eligible = False
            exclusion_reasons.append(f"Insufficient Step rows ({step_count})")
        if overlap_hours < 72.0:
            is_eligible = False
            exclusion_reasons.append(f"Insufficient Overlap ({overlap_hours:.1f}h)")

        status_str = "Eligible" if is_eligible else "; ".join(exclusion_reasons)

        rec = {
            "participant": u,
            "cgm_present": cgm_present,
            "cgm_rows": cgm_valid_rows,
            "cgm_start": str(cgm_start),
            "cgm_end": str(cgm_end),
            "cgm_duration_days": round(cgm_days, 2),
            "watch_present": watch_present,
            "hr_count": hr_count,
            "step_count": step_count,
            "accel_count": accel_count,
            "watch_start": str(w_start),
            "watch_end": str(w_end),
            "watch_duration_days": round(w_days, 2),
            "overlap_start": str(overlap_start),
            "overlap_end": str(overlap_end),
            "overlap_hours": round(overlap_hours, 2),
            "overlap_days": round(overlap_hours / 24.0, 2),
            "usable_15m_windows": usable_15m_windows,
            "is_eligible": is_eligible,
            "decision": "INCLUDED" if is_eligible else "EXCLUDED",
            "exclusion_reason": status_str
        }
        audit_results.append(rec)

        print(f"[{'INCLUDED' if is_eligible else 'EXCLUDED'}] {u:6s} | CGM: {cgm_valid_rows:4d} ({cgm_days:4.1f}d) | HR: {hr_count:7d} | Steps: {step_count:6d} | Accel: {accel_count:7d} | Overlap: {overlap_hours:5.1f}h ({overlap_hours/24:4.1f}d) | Status: {status_str}")

    # Output detailed JSON
    out_json = os.path.join(RESULTS_DIR, "detailed_cohort_eligibility.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(audit_results, f, indent=2)

    df_out = pd.DataFrame(audit_results)
    out_csv = os.path.join(RESULTS_DIR, "detailed_cohort_eligibility.csv")
    df_out.to_csv(out_csv, index=False)

    eligible_df = df_out[df_out["is_eligible"]]
    print("\n" + "=" * 80)
    print("COHORT ELIGIBILITY RESOLUTION SUMMARY")
    print("=" * 80)
    print(f"Total Discovered Participants: {len(df_out)}")
    print(f"Total Eligible Participants:   {len(eligible_df)}")
    print(f"Eligible Participant IDs:      {list(eligible_df['participant'])}")
    print(f"CGM Duration (Days) — Min: {eligible_df['cgm_duration_days'].min():.2f}, Max: {eligible_df['cgm_duration_days'].max():.2f}, Median: {eligible_df['cgm_duration_days'].median():.2f}, Mean: {eligible_df['cgm_duration_days'].mean():.2f}")
    print(f"Overlap Duration (Days) — Min: {eligible_df['overlap_days'].min():.2f}, Max: {eligible_df['overlap_days'].max():.2f}, Median: {eligible_df['overlap_days'].median():.2f}, Mean: {eligible_df['overlap_days'].mean():.2f}")
    print(f"Total Usable 15m Windows:      {eligible_df['usable_15m_windows'].sum()}")
    print("=" * 80)

    return audit_results

if __name__ == "__main__":
    main()
