"""
GlucoShield Pre-Modeling Investigation Script
Analyzes carb estimation artifacts, affected splits, and T1DM/T2DM distribution.
"""

import os
import json
import pandas as pd
import numpy as np

def run_investigation():
    base_dir = "D:/ML PROJECT"
    data_dir = os.path.join(base_dir, "data")
    processed_dir = os.path.join(data_dir, "processed")
    final_dir = os.path.join(data_dir, "final")
    meta_dir = os.path.join(data_dir, "metadata")

    df_ts = pd.read_csv(os.path.join(processed_dir, "cleaned_timeseries_all.csv"))
    train_meta = pd.read_csv(os.path.join(final_dir, "meta_train.csv"))
    val_meta = pd.read_csv(os.path.join(final_dir, "meta_val.csv"))
    test_meta = pd.read_csv(os.path.join(final_dir, "meta_test.csv"))

    with open(os.path.join(meta_dir, "dataset_manifest.json"), "r") as f:
        manifest = json.load(f)

    train_pids = set(manifest["patient_split"]["train_patient_ids"])
    val_pids = set(manifest["patient_split"]["val_patient_ids"])
    test_pids = set(manifest["patient_split"]["test_patient_ids"])

    def get_split(pid):
        spid = str(pid)
        if spid in train_pids:
            return "train"
        elif spid in val_pids:
            return "val"
        elif spid in test_pids:
            return "test"
        return "unknown"

    df_ts["split"] = df_ts["patient_id"].apply(get_split)

    meal_events = df_ts[df_ts["meal_flag"] > 0].copy()
    total_meals = len(meal_events)

    print(f"Total rows in dataset: {len(df_ts)}")
    print(f"Total logged meal events: {total_meals}")

    # Threshold analysis
    t150 = meal_events[meal_events["carbs_estimate_g"] > 150]
    t200 = meal_events[meal_events["carbs_estimate_g"] > 200]
    t300 = meal_events[meal_events["carbs_estimate_g"] > 300]
    t500 = meal_events[meal_events["carbs_estimate_g"] > 500]

    print("\n--- THRESHOLD SUMMARY ---")
    print(f"Carbs > 150g: {len(t150):>4} ({len(t150)/total_meals*100:.2f}%) | Affected Records: {t150['record_id'].nunique()} | Patients: {t150['patient_id'].nunique()}")
    print(f"Carbs > 200g: {len(t200):>4} ({len(t200)/total_meals*100:.2f}%) | Affected Records: {t200['record_id'].nunique()} | Patients: {t200['patient_id'].nunique()}")
    print(f"Carbs > 300g: {len(t300):>4} ({len(t300)/total_meals*100:.2f}%) | Affected Records: {t300['record_id'].nunique()} | Patients: {t300['patient_id'].nunique()}")
    print(f"Carbs > 500g: {len(t500):>4} ({len(t500)/total_meals*100:.2f}%) | Affected Records: {t500['record_id'].nunique()} | Patients: {t500['patient_id'].nunique()}")

    print("\n--- SPLIT DISTRIBUTION OF HIGH-CARB EVENTS ---")
    for name, subset in [(">150g", t150), (">200g", t200), (">300g", t300), (">500g", t500)]:
        sp_counts = subset["split"].value_counts().to_dict()
        print(f"  Threshold {name:<6}: Train={sp_counts.get('train', 0)}, Val={sp_counts.get('val', 0)}, Test={sp_counts.get('test', 0)}")

    # Details of > 300g events
    print("\n--- ALL EVENTS > 300g ---")
    for idx, r in t300.sort_values("carbs_estimate_g", ascending=False).iterrows():
        print(f"  Split: {r['split']:<5} | Record: {r['record_id']} | Carbs: {r['carbs_estimate_g']:>5.1f}g | Time: {r['timestamp']} | Text: {repr(r['meal_text'])}")

    # Check 660g event
    event_660 = df_ts[df_ts["carbs_estimate_g"] >= 660]
    print(f"\n--- 660g EVENT CHECK ---")
    for idx, r in event_660.iterrows():
        print(f"  Record: {r['record_id']} | Patient ID: {r['patient_id']} | Split: {r['split']} | Timestamp: {r['timestamp']}")

    # T1DM vs T2DM Breakdown across splits
    print("\n--- T1DM vs T2DM PATIENT & SEQUENCE DISTRIBUTION ---")
    for s_name, meta_df in [("Train", train_meta), ("Val", val_meta), ("Test", test_meta)]:
        n_p_t1 = meta_df[meta_df["diabetes_type"] == "T1DM"]["patient_id"].nunique()
        n_p_t2 = meta_df[meta_df["diabetes_type"] == "T2DM"]["patient_id"].nunique()
        n_seq_t1 = (meta_df["diabetes_type"] == "T1DM").sum()
        n_seq_t2 = (meta_df["diabetes_type"] == "T2DM").sum()
        total_seq = len(meta_df)
        total_p = meta_df["patient_id"].nunique()
        print(f"  {s_name:<5} Split: Patients={total_p:>2} (T1: {n_p_t1:>2}, T2: {n_p_t2:>2}) | Sequences={total_seq:>5} (T1: {n_seq_t1:>5} [{n_seq_t1/total_seq*100:5.2f}%], T2: {n_seq_t2:>5} [{n_seq_t2/total_seq*100:5.2f}%])")

    # Sequence dominance among T1DM patients
    print("\n--- T1DM PATIENT SEQUENCE BREAKDOWN ---")
    comb_meta = pd.concat([train_meta.assign(split="train"), val_meta.assign(split="val"), test_meta.assign(split="test")])
    t1_seqs = comb_meta[comb_meta["diabetes_type"] == "T1DM"].groupby(["patient_id", "split"]).size().reset_index(name="seq_count")
    for _, r in t1_seqs.sort_values("seq_count", ascending=False).iterrows():
        print(f"  Patient {r['patient_id']} ({r['split']}): {r['seq_count']} sequences ({r['seq_count']/len(comb_meta[comb_meta['diabetes_type']=='T1DM'])*100:.2f}% of all T1DM)")

if __name__ == "__main__":
    run_investigation()
