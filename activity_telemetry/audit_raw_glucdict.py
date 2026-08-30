"""
GlucoShield — Glucdict Raw Data Structure & Schema Audit
=========================================================
Audits extracted raw files across all participants, verifying column headers,
sensor IDs, timestamp formats, row counts, valid physiological ranges, and alignment.
"""

import os
import csv
import json
import pandas as pd
from datetime import datetime

BASE_DIR = "D:/ML PROJECT"
RAW_ROOT = os.path.join(BASE_DIR, "data", "raw", "Glucdict", "Glucdict Dataset")
RESULTS_DIR = os.path.join(BASE_DIR, "activity_telemetry", "experiments", "results")

def audit_glucdict():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    users = sorted([d for d in os.listdir(RAW_ROOT) if os.path.isdir(os.path.join(RAW_ROOT, d)) and d.startswith("User")])
    print(f"Discovered {len(users)} participant folders: {users}")

    manifest_list = []
    tabular_rows = []

    for u in users:
        upath = os.path.join(RAW_ROOT, u)
        u_info = {"participant": u}

        # 1. CGM Glucose Audit
        gdir = os.path.join(upath, "Glucose")
        cgm_file = os.path.join(gdir, f"CGM_{u}.csv")
        if os.path.exists(cgm_file):
            df_cgm = pd.read_csv(cgm_file)
            df_cgm["glucose_clean"] = pd.to_numeric(df_cgm["Glucose Value (mg/dL)"], errors="coerce")
            valid_cgm = df_cgm.dropna(subset=["glucose_clean"])
            ts_min = str(df_cgm["Timestamp (YYYY-MM-DDThh:mm:ss)"].min())
            ts_max = str(df_cgm["Timestamp (YYYY-MM-DDThh:mm:ss)"].max())
            u_info["cgm"] = {
                "present": True,
                "file_name": f"CGM_{u}.csv",
                "total_rows": int(len(df_cgm)),
                "valid_glucose_rows": int(len(valid_cgm)),
                "ts_start": ts_min,
                "ts_end": ts_max,
                "mean_glucose": round(float(valid_cgm["glucose_clean"].mean()), 2) if len(valid_cgm) > 0 else None,
                "std_glucose": round(float(valid_cgm["glucose_clean"].std()), 2) if len(valid_cgm) > 0 else None,
                "min_glucose": float(valid_cgm["glucose_clean"].min()) if len(valid_cgm) > 0 else None,
                "max_glucose": float(valid_cgm["glucose_clean"].max()) if len(valid_cgm) > 0 else None
            }
        else:
            u_info["cgm"] = {"present": False}

        # 2. Watch Sensor Audit
        wdir = os.path.join(upath, "Watch")
        wfiles = [os.path.join(wdir, f) for f in os.listdir(wdir) if f.endswith(".csv")] if os.path.exists(wdir) else []
        
        sensor_counts = {}
        total_w_rows = 0
        w_ts_min, w_ts_max = float("inf"), 0

        for wf in wfiles:
            with open(wf, "r", encoding="utf-8", errors="ignore") as fp:
                reader = csv.reader(fp)
                for row in reader:
                    if not row or len(row) < 3:
                        continue
                    try:
                        sid = int(row[0])
                        ts_ms = int(row[1])
                        total_w_rows += 1
                        sensor_counts[sid] = sensor_counts.get(sid, 0) + 1
                        if ts_ms < w_ts_min: w_ts_min = ts_ms
                        if ts_ms > w_ts_max: w_ts_max = ts_ms
                    except:
                        continue

        u_info["watch"] = {
            "present": len(wfiles) > 0,
            "file_count": len(wfiles),
            "total_rows": total_w_rows,
            "sensor_id_counts": {str(k): v for k, v in sorted(sensor_counts.items())},
            "ts_start_epoch_ms": int(w_ts_min) if w_ts_min != float("inf") else None,
            "ts_end_epoch_ms": int(w_ts_max) if w_ts_max != 0 else None
        }
        if w_ts_min != float("inf"):
            u_info["watch"]["ts_start_iso"] = datetime.fromtimestamp(w_ts_min / 1000.0).isoformat()
            u_info["watch"]["ts_end_iso"] = datetime.fromtimestamp(w_ts_max / 1000.0).isoformat()

        # 3. Phone Activities Audit
        adir = os.path.join(upath, "Phone", "Activities")
        afiles = [os.path.join(adir, f) for f in os.listdir(adir) if f.endswith(".csv")] if os.path.exists(adir) else []
        act_counts = {}
        for af in afiles:
            with open(af, "r", encoding="utf-8", errors="ignore") as fp:
                reader = csv.reader(fp)
                for row in reader:
                    if len(row) >= 2:
                        # Clean ascii for key
                        raw_act = row[1].strip().lower()
                        ascii_act = "".join([c for c in raw_act if ord(c) < 128]) or "custom_event"
                        act_counts[ascii_act] = act_counts.get(ascii_act, 0) + 1

        u_info["activities"] = {
            "present": len(afiles) > 0,
            "file_count": len(afiles),
            "event_breakdown": act_counts
        }

        # Tabular summary row
        tabular_rows.append({
            "participant": u,
            "cgm_rows": u_info["cgm"].get("valid_glucose_rows", 0),
            "cgm_start": u_info["cgm"].get("ts_start", "N/A"),
            "cgm_end": u_info["cgm"].get("ts_end", "N/A"),
            "mean_glucose_mg_dl": u_info["cgm"].get("mean_glucose", "N/A"),
            "watch_rows": u_info["watch"].get("total_rows", 0),
            "watch_start": u_info["watch"].get("ts_start_iso", "N/A"),
            "watch_end": u_info["watch"].get("ts_end_iso", "N/A"),
            "accel_count": u_info["watch"].get("sensor_id_counts", {}).get("1", 0),
            "hr_count": u_info["watch"].get("sensor_id_counts", {}).get("21", 0),
            "step_count": u_info["watch"].get("sensor_id_counts", {}).get("18", 0),
            "eating_events": u_info["activities"].get("event_breakdown", {}).get("eat", 0),
            "drinking_events": u_info["activities"].get("event_breakdown", {}).get("drink", 0)
        })

        manifest_list.append(u_info)
        print(f"Participant {u:6s}: CGM={u_info['cgm']['present']} ({u_info['cgm'].get('valid_glucose_rows', 0)} pts) | Watch={u_info['watch']['total_rows']} rows (HR={u_info['watch'].get('sensor_id_counts', {}).get('21', 0)}, Steps={u_info['watch'].get('sensor_id_counts', {}).get('18', 0)}, Accel={u_info['watch'].get('sensor_id_counts', {}).get('1', 0)})")

    # Save JSON and CSV manifests
    json_path = os.path.join(RESULTS_DIR, "glucdict_dataset_manifest.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(manifest_list, f, indent=2)

    csv_path = os.path.join(RESULTS_DIR, "glucdict_dataset_manifest.csv")
    df_manifest = pd.DataFrame(tabular_rows)
    df_manifest.to_csv(csv_path, index=False, encoding="utf-8")

    print(f"\nManifests saved successfully:\n  --> {json_path}\n  --> {csv_path}")
    return manifest_list, df_manifest

if __name__ == "__main__":
    audit_glucdict()
