"""
GlucoShield - Comprehensive Data Engineering, Audit, Leakage-Safe Splitting & Sequence Pipeline
"""

import os
import json
import shutil
import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler, StandardScaler
import joblib

def audit_and_build_pipeline():
    print("================================================================================")
    print("GLUCOSHIELD: DATA ENGINEERING & LEAKAGE-SAFE PIPELINE INITIALIZATION")
    print("================================================================================")

    # 1. Setup Directory Structure
    base_dir = "D:/ML PROJECT"
    data_dir = os.path.join(base_dir, "data")
    raw_dir = os.path.join(data_dir, "raw")
    processed_dir = os.path.join(data_dir, "processed")
    final_dir = os.path.join(data_dir, "final")
    meta_dir = os.path.join(data_dir, "metadata")
    deprecated_dir = os.path.join(data_dir, "deprecated")
    dep_models_dir = os.path.join(deprecated_dir, "old_test_models")

    for d in [data_dir, raw_dir, processed_dir, final_dir, meta_dir, deprecated_dir, dep_models_dir]:
        os.makedirs(d, exist_ok=True)

    # 2. Archive Old Prototype / Test Models
    old_models = [
        "glucoshield_twin.pt",
        "glucoshield_twin_5h.pt",
        "glucoshield_twin_5h_T1DM.pt",
        "glucoshield_twin_5h_T2DM.pt"
    ]
    archived_models = []
    for m in old_models:
        src = os.path.join(base_dir, m)
        dst = os.path.join(dep_models_dir, m)
        if os.path.exists(src):
            shutil.move(src, dst)
            archived_models.append(m)
            print(f"[DEPRECATED] Moved test model checkpoint '{m}' -> '{dst}'")

    # 3. Load & Audit Raw / Cleaned Master Time Series
    master_path = os.path.join(base_dir, "clean_output", "cleaned_master.csv")
    static_path = os.path.join(base_dir, "clean_output", "patient_static_features.csv")

    if not os.path.exists(master_path):
        raise FileNotFoundError(f"Master file not found at {master_path}")

    print("\n--- STEP 1 & 3: AUDITING RAW/CURRENT DATASET ---")
    df_raw = pd.read_csv(master_path)
    df_raw["timestamp"] = pd.to_datetime(df_raw["timestamp"])

    initial_row_count = len(df_raw)
    initial_patients = df_raw["patient_id"].nunique()
    initial_records = df_raw["record_id"].nunique()
    print(f"Loaded master CSV: {initial_row_count} rows, {initial_patients} unique patients, {initial_records} visits/records.")

    # Audit statistics
    null_counts = df_raw.isnull().sum().to_dict()
    print(f"Missing values per column:\n{json.dumps(null_counts, indent=2)}")

    # Audit Glucose
    g_min = float(df_raw["glucose"].min())
    g_max = float(df_raw["glucose"].max())
    g_mean = float(df_raw["glucose"].mean())
    g_median = float(df_raw["glucose"].median())
    g_std = float(df_raw["glucose"].std())
    print(f"Glucose Distribution: min={g_min:.1f}, max={g_max:.1f}, mean={g_mean:.1f}, median={g_median:.1f}, std={g_std:.1f} mg/dL")

    # Audit physiologically suspicious readings (< 20 mg/dL or > 600 mg/dL)
    extreme_low = int((df_raw["glucose"] < 20).sum())
    extreme_high = int((df_raw["glucose"] > 600).sum())
    print(f"Physiologically extreme values: < 20 mg/dL: {extreme_low} rows | > 600 mg/dL: {extreme_high} rows")

    # Audit timestamps & duplicates
    dup_rows = int(df_raw.duplicated().sum())
    dup_patient_ts = int(df_raw.duplicated(subset=["record_id", "timestamp"]).sum())
    print(f"Exact duplicate rows: {dup_rows} | Duplicate timestamps per record: {dup_patient_ts}")

    # Audit Insulin and Carbs
    neg_insulin = int((df_raw["insulin_total"] < 0).sum())
    max_insulin = float(df_raw["insulin_total"].max())
    neg_carbs = int((df_raw["carbs_estimate_g"] < 0).sum())
    max_carbs = float(df_raw["carbs_estimate_g"].max())
    print(f"Insulin checks: negative={neg_insulin}, max_single_dose={max_insulin:.2f} IU")
    print(f"Carb checks: negative={neg_carbs}, max_single_meal={max_carbs:.2f} g")

    # 4. Clean Time-Series Data without Over-Cleaning
    print("\n--- STEP 4 & 5: CLEANING & CAUSAL FEATURE ENGINEERING ---")
    clean_records = []
    
    # Half-lives in 15-minute steps
    IOB_HALFLIFE_STEPS = 8   # ~2 hours
    COB_HALFLIFE_STEPS = 4   # ~1 hour

    for record_id, grp in df_raw.groupby("record_id"):
        g = grp.copy()
        g = g.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
        
        raw_cols = ["glucose", "insulin_bolus", "insulin_basal", "insulin_total", "carbs_estimate_g", "meal_flag"]
        for col in raw_cols:
            if col not in g.columns:
                g[col] = 0.0
            g[col] = g[col].ffill().fillna(0.0)

        # Clip glucose to safe clinical sensor bounds [20.0, 600.0] mg/dL
        g["glucose"] = g["glucose"].clip(lower=20.0, upper=600.0)

        # 1. Causal Velocity & Acceleration (15-min rate of change)
        g["glucose_velocity"] = g["glucose"].diff().fillna(0.0)
        g["glucose_accel"] = g["glucose_velocity"].diff().fillna(0.0)

        # 2. Causal Rolling Statistics (using past values only, min_periods=1)
        g["glucose_roll_mean_1h"] = g["glucose"].rolling(window=4, min_periods=1).mean()
        g["glucose_roll_std_1h"] = g["glucose"].rolling(window=4, min_periods=1).std().fillna(0.0)
        g["glucose_roll_min_1h"] = g["glucose"].rolling(window=4, min_periods=1).min()
        g["glucose_roll_max_1h"] = g["glucose"].rolling(window=4, min_periods=1).max()
        
        g["glucose_roll_mean_3h"] = g["glucose"].rolling(window=12, min_periods=1).mean()
        g["glucose_roll_std_3h"] = g["glucose"].rolling(window=12, min_periods=1).std().fillna(0.0)
        g["glucose_roll_mean_6h"] = g["glucose"].rolling(window=24, min_periods=1).mean()

        # 3. Temporal & Cyclical Features
        g["hour"] = g["timestamp"].dt.hour
        g["minute"] = g["timestamp"].dt.minute
        hour_float = g["hour"] + g["minute"] / 60.0
        g["sin_hour"] = np.sin(2 * np.pi * hour_float / 24.0)
        g["cos_hour"] = np.cos(2 * np.pi * hour_float / 24.0)
        g["is_night"] = ((g["hour"] >= 23) | (g["hour"] < 6)).astype(float)

        # 4. Physiological Insulin & Carb Decay Features (IOB & COB)
        g["iob"] = g["insulin_total"].ewm(halflife=IOB_HALFLIFE_STEPS, adjust=False).mean()
        g["cob"] = g["carbs_estimate_g"].ewm(halflife=COB_HALFLIFE_STEPS, adjust=False).mean()

        # Cumulative 2-hour insulin and carbs
        g["insulin_cum_2h"] = g["insulin_total"].rolling(window=8, min_periods=1).sum()
        g["carbs_cum_2h"] = g["carbs_estimate_g"].rolling(window=8, min_periods=1).sum()

        clean_records.append(g)

    df_cleaned = pd.concat(clean_records, ignore_index=True)
    print(f"Cleaned time-series generated: {len(df_cleaned)} rows across {df_cleaned['record_id'].nunique()} records.")

    # 5. Clean & Standardize Static Patient Features
    print("\n--- STEP 5.2: CLEANING STATIC CLINICAL FEATURES ---")
    df_static_raw = pd.read_csv(static_path)

    static_clean = pd.DataFrame()
    static_clean["patient_id"] = df_static_raw["patient_id"].astype(str)
    static_clean["visit"] = df_static_raw["visit"].fillna(0.0).astype(float)
    static_clean["record_id"] = df_static_raw["diabetes_type"].astype(str) + "_" + df_static_raw["patient_id"].astype(str) + "_" + df_static_raw["visit"].astype(int).astype(str)
    static_clean["diabetes_type"] = df_static_raw["diabetes_type"].fillna("T2DM")
    static_clean["is_t1dm"] = (static_clean["diabetes_type"] == "T1DM").astype(float)
    
    def to_float_safe(series):
        return pd.to_numeric(series.replace('/', np.nan).replace('none', np.nan), errors='coerce')

    static_clean["age"] = to_float_safe(df_static_raw["Age (years)"])
    static_clean["bmi"] = to_float_safe(df_static_raw["BMI (kg/m2)"])
    static_clean["hba1c"] = to_float_safe(df_static_raw["HbA1c (mmol/mol)"])
    static_clean["glycated_albumin"] = to_float_safe(df_static_raw["Glycated Albumin (%)"])
    static_clean["fasting_glucose"] = to_float_safe(df_static_raw["Fasting Plasma Glucose (mg/dl)"])
    static_clean["fasting_c_peptide"] = to_float_safe(df_static_raw["Fasting C-peptide (nmol/L)"])
    static_clean["postprandial_c_peptide"] = to_float_safe(df_static_raw["2-hour Postprandial C-peptide (nmol/L)"])
    
    def count_items(series):
        return series.fillna("none").apply(lambda x: 0 if str(x).lower().strip() == 'none' else len(str(x).split(','))).astype(float)

    if "Diabetic Macrovascular  Complications" in df_static_raw.columns:
        static_clean["macrovascular_comp_count"] = count_items(df_static_raw["Diabetic Macrovascular  Complications"])
    else:
        static_clean["macrovascular_comp_count"] = 0.0

    if "Diabetic Microvascular Complications" in df_static_raw.columns:
        static_clean["microvascular_comp_count"] = count_items(df_static_raw["Diabetic Microvascular Complications"])
    else:
        static_clean["microvascular_comp_count"] = 0.0

    static_patient_level = static_clean.groupby("patient_id").first().reset_index()
    print(f"Cleaned static patient features: {len(static_patient_level)} unique patients.")

    # 6. Strict Leakage-Safe Patient-Wise Train / Validation / Test Split
    print("\n--- STEP 6: PATIENT-WISE SPLITTING (ZERO LEAKAGE) ---")
    unique_patients = static_patient_level[["patient_id", "diabetes_type"]].drop_duplicates().reset_index(drop=True)
    
    SPLIT_SEED = 42
    np.random.seed(SPLIT_SEED)

    t1_patients = list(unique_patients[unique_patients["diabetes_type"] == "T1DM"]["patient_id"].values)
    t2_patients = list(unique_patients[unique_patients["diabetes_type"] == "T2DM"]["patient_id"].values)

    np.random.shuffle(t1_patients)
    np.random.shuffle(t2_patients)

    def split_pids(pids, train_ratio=0.70, val_ratio=0.15):
        n = len(pids)
        n_train = max(1, int(round(n * train_ratio)))
        n_val = max(1, int(round(n * val_ratio)))
        train_p = pids[:n_train]
        val_p = pids[n_train:n_train + n_val]
        test_p = pids[n_train + n_val:]
        return list(train_p), list(val_p), list(test_p)

    t1_tr, t1_val, t1_te = split_pids(t1_patients, 0.70, 0.15)
    t2_tr, t2_val, t2_te = split_pids(t2_patients, 0.70, 0.15)

    train_pids = sorted(t1_tr + t2_tr)
    val_pids = sorted(t1_val + t2_val)
    test_pids = sorted(t1_te + t2_te)

    # Verification
    set_train = set(train_pids)
    set_val = set(val_pids)
    set_test = set(test_pids)

    assert len(set_train.intersection(set_val)) == 0, "FATAL ERROR: Train and Val overlap!"
    assert len(set_train.intersection(set_test)) == 0, "FATAL ERROR: Train and Test overlap!"
    assert len(set_val.intersection(set_test)) == 0, "FATAL ERROR: Val and Test overlap!"
    print(f"Patient-wise split verification PASSED:")
    print(f"  Train: {len(train_pids)} patients (T1: {len(t1_tr)}, T2: {len(t2_tr)})")
    print(f"  Val  : {len(val_pids)} patients (T1: {len(t1_val)}, T2: {len(t2_val)})")
    print(f"  Test : {len(test_pids)} patients (T1: {len(t1_te)}, T2: {len(t2_te)})")

    # 7. Multi-Horizon Sliding Window Sequence Building
    print("\n--- STEP 7: MULTI-HORIZON SEQUENCE GENERATION ---")
    INPUT_STEPS = 96     # 24 hours of history
    MAX_OUTPUT_STEPS = 20  # 5 hours
    STRIDE = 4             # 1 hour stride

    feature_cols = [
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

    static_cols = [
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

    # Impute static features based on TRAIN SET MEDIANS only
    train_static = static_patient_level[static_patient_level["patient_id"].isin(train_pids)]
    static_medians = train_static[static_cols].median().to_dict()
    
    static_imputed = static_patient_level.copy()
    for col in static_cols:
        static_imputed[col] = static_imputed[col].fillna(static_medians[col])
    
    static_dict = static_imputed.set_index("patient_id")[static_cols].to_dict('index')

    def generate_sequences_for_patients(df, pids):
        X_seqs = []
        Y_trajectory = []     # continuous glucose forecast (20 steps)
        Y_hypo_1h = []        # binary hypo in 1h (< 70 mg/dL)
        Y_hypo_2h = []        # binary hypo in 2h (< 70 mg/dL)
        Y_hypo_4h = []        # binary hypo in 4h (< 70 mg/dL)
        Y_hyper_2h = []       # binary hyper in 2h (> 180 mg/dL)
        Y_hyper_4h = []       # binary hyper in 4h (> 180 mg/dL)
        static_features = []
        meta_records = []

        sub_df = df[df["patient_id"].astype(str).isin(pids)]
        window_len = INPUT_STEPS + MAX_OUTPUT_STEPS

        for record_id, g in sub_df.groupby("record_id"):
            g = g.sort_values("timestamp").reset_index(drop=True)
            if len(g) < window_len:
                continue

            feat_vals = g[feature_cols].values
            glucose_vals = g["glucose"].values
            timestamps = g["timestamp"].values
            pid = str(g["patient_id"].iloc[0])
            dtype = str(g["diabetes_type"].iloc[0])
            p_static = [static_dict[pid][c] for c in static_cols] if pid in static_dict else [static_medians[c] for c in static_cols]

            n = len(g)
            for start in range(0, n - window_len + 1, STRIDE):
                x_window = feat_vals[start : start + INPUT_STEPS]
                y_window = glucose_vals[start + INPUT_STEPS : start + window_len]

                if np.isnan(x_window).any() or np.isnan(y_window).any():
                    continue

                hypo_1h = float(np.min(y_window[:4]) < 70.0)
                hypo_2h = float(np.min(y_window[:8]) < 70.0)
                hypo_4h = float(np.min(y_window[:16]) < 70.0)
                hyper_2h = float(np.max(y_window[:8]) > 180.0)
                hyper_4h = float(np.max(y_window[:16]) > 180.0)

                X_seqs.append(x_window)
                Y_trajectory.append(y_window)
                Y_hypo_1h.append(hypo_1h)
                Y_hypo_2h.append(hypo_2h)
                Y_hypo_4h.append(hypo_4h)
                Y_hyper_2h.append(hyper_2h)
                Y_hyper_4h.append(hyper_4h)
                static_features.append(p_static)

                meta_records.append({
                    "record_id": record_id,
                    "patient_id": pid,
                    "diabetes_type": dtype,
                    "start_timestamp": str(timestamps[start]),
                    "input_end_timestamp": str(timestamps[start + INPUT_STEPS - 1]),
                    "target_end_timestamp": str(timestamps[start + window_len - 1]),
                    "current_glucose": float(x_window[-1, 0]),
                    "min_future_glucose": float(np.min(y_window)),
                    "max_future_glucose": float(np.max(y_window)),
                    "hypo_in_4h": int(hypo_4h),
                    "hyper_in_4h": int(hyper_4h)
                })

        return {
            "X": np.array(X_seqs, dtype=np.float32),
            "Y_traj": np.array(Y_trajectory, dtype=np.float32),
            "Y_hypo_1h": np.array(Y_hypo_1h, dtype=np.float32),
            "Y_hypo_2h": np.array(Y_hypo_2h, dtype=np.float32),
            "Y_hypo_4h": np.array(Y_hypo_4h, dtype=np.float32),
            "Y_hyper_2h": np.array(Y_hyper_2h, dtype=np.float32),
            "Y_hyper_4h": np.array(Y_hyper_4h, dtype=np.float32),
            "static": np.array(static_features, dtype=np.float32),
            "meta": pd.DataFrame(meta_records)
        }

    print("Generating train sequences...")
    train_data = generate_sequences_for_patients(df_cleaned, train_pids)
    print("Generating validation sequences...")
    val_data = generate_sequences_for_patients(df_cleaned, val_pids)
    print("Generating test sequences...")
    test_data = generate_sequences_for_patients(df_cleaned, test_pids)

    print(f"Sequence counts generated:")
    print(f"  Train : {len(train_data['X'])} sequences (Shape: {train_data['X'].shape})")
    print(f"  Val   : {len(val_data['X'])} sequences (Shape: {val_data['X'].shape})")
    print(f"  Test  : {len(test_data['X'])} sequences (Shape: {test_data['X'].shape})")

    # 8. Leakage-Safe Normalization (Fit Scalers on TRAIN ONLY)
    print("\n--- STEP 8: LEAKAGE-SAFE FEATURE SCALING (FIT ON TRAIN ONLY) ---")
    N_tr, T, F = train_data["X"].shape
    X_train_flat = train_data["X"].reshape(-1, F)

    feature_scaler = RobustScaler()
    feature_scaler.fit(X_train_flat)

    static_scaler = StandardScaler()
    static_scaler.fit(train_data["static"])

    def scale_split(split_data):
        X = split_data["X"]
        n_samples = len(X)
        if n_samples == 0:
            return split_data
        X_scaled = feature_scaler.transform(X.reshape(-1, F)).reshape(n_samples, T, F).astype(np.float32)
        static_scaled = static_scaler.transform(split_data["static"]).astype(np.float32)
        return {
            **split_data,
            "X_scaled": X_scaled,
            "static_scaled": static_scaled
        }

    train_data = scale_split(train_data)
    val_data = scale_split(val_data)
    test_data = scale_split(test_data)

    # 9. Save Cleaned Datasets, Scalers, Metadata, and Final Tensors
    print("\n--- STEP 9: SAVING ALL ARTIFACTS TO data/ ---")
    df_cleaned.to_csv(os.path.join(processed_dir, "cleaned_timeseries_all.csv"), index=False)
    static_imputed.to_csv(os.path.join(processed_dir, "cleaned_static_features.csv"), index=False)

    for split_name, sdata in [("train", train_data), ("val", val_data), ("test", test_data)]:
        np.save(os.path.join(final_dir, f"X_{split_name}_raw.npy"), sdata["X"])
        np.save(os.path.join(final_dir, f"X_{split_name}_scaled.npy"), sdata["X_scaled"])
        np.save(os.path.join(final_dir, f"static_{split_name}_raw.npy"), sdata["static"])
        np.save(os.path.join(final_dir, f"static_{split_name}_scaled.npy"), sdata["static_scaled"])
        np.save(os.path.join(final_dir, f"Y_{split_name}_trajectory.npy"), sdata["Y_traj"])
        np.save(os.path.join(final_dir, f"Y_{split_name}_hypo_1h.npy"), sdata["Y_hypo_1h"])
        np.save(os.path.join(final_dir, f"Y_{split_name}_hypo_2h.npy"), sdata["Y_hypo_2h"])
        np.save(os.path.join(final_dir, f"Y_{split_name}_hypo_4h.npy"), sdata["Y_hypo_4h"])
        np.save(os.path.join(final_dir, f"Y_{split_name}_hyper_2h.npy"), sdata["Y_hyper_2h"])
        np.save(os.path.join(final_dir, f"Y_{split_name}_hyper_4h.npy"), sdata["Y_hyper_4h"])
        sdata["meta"].to_csv(os.path.join(final_dir, f"meta_{split_name}.csv"), index=False)
        print(f"Saved {split_name} split files successfully.")

    # Save Scalers
    joblib.dump(feature_scaler, os.path.join(meta_dir, "feature_scaler.joblib"))
    joblib.dump(static_scaler, os.path.join(meta_dir, "static_scaler.joblib"))

    # Save Metadata & Manifest JSON
    manifest = {
        "dataset_name": "GlucoShield Cleaned Clinical Digital-Twin Dataset",
        "version": "1.0.0",
        "description": "Multi-horizon continuous glucose forecasting and acute event prediction dataset.",
        "input_steps": INPUT_STEPS,
        "input_duration_hours": 24,
        "max_output_steps": MAX_OUTPUT_STEPS,
        "max_output_duration_hours": 5,
        "stride_steps": STRIDE,
        "time_interval_minutes": 15,
        "feature_count": len(feature_cols),
        "feature_columns": feature_cols,
        "static_count": len(static_cols),
        "static_columns": static_cols,
        "static_medians": static_medians,
        "patient_split": {
            "random_seed": SPLIT_SEED,
            "train_patient_count": len(train_pids),
            "val_patient_count": len(val_pids),
            "test_patient_count": len(test_pids),
            "train_patient_ids": train_pids,
            "val_patient_ids": val_pids,
            "test_patient_ids": test_pids
        },
        "sequence_counts": {
            "train": len(train_data["X"]),
            "val": len(val_data["X"]),
            "test": len(test_data["X"]),
            "total": len(train_data["X"]) + len(val_data["X"]) + len(test_data["X"])
        },
        "event_rates": {
            "train_hypo_4h_rate": float(np.mean(train_data["Y_hypo_4h"])),
            "train_hyper_4h_rate": float(np.mean(train_data["Y_hyper_4h"])),
            "val_hypo_4h_rate": float(np.mean(val_data["Y_hypo_4h"])),
            "val_hyper_4h_rate": float(np.mean(val_data["Y_hyper_4h"])),
            "test_hypo_4h_rate": float(np.mean(test_data["Y_hypo_4h"])),
            "test_hyper_4h_rate": float(np.mean(test_data["Y_hyper_4h"]))
        },
        "archived_prototype_models": archived_models
    }

    with open(os.path.join(meta_dir, "dataset_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    # 10. Generate Quality Report Text
    quality_report = f"""GLUCOSHIELD DATASET AUDIT & ENGINEERING REPORT
======================================================
Generated: Leakage-Safe Multi-Modal Digital-Twin Dataset

1. Patient Cohort Breakdown:
   - Total Unique Patients : {len(unique_patients)}
   - T1DM Patients         : {len(t1_patients)} (High volatility cohort)
   - T2DM Patients         : {len(t2_patients)} (Standard insulin resistance cohort)
   - Train Patients        : {len(train_pids)} (T1: {len(t1_tr)}, T2: {len(t2_tr)})
   - Validation Patients   : {len(val_pids)} (T1: {len(t1_val)}, T2: {len(t2_val)})
   - Test Patients         : {len(test_pids)} (T1: {len(t1_te)}, T2: {len(t2_te)})

2. Sequence Statistics:
   - Input Sequence Length : 96 steps = 24.0 hours
   - Forecast Horizon      : 20 steps = 5.0 hours (also supports 1h, 2h, 3h, 4h)
   - Sliding Stride        : 4 steps = 1.0 hour
   - Total Train Sequences : {len(train_data['X'])}
   - Total Val Sequences   : {len(val_data['X'])}
   - Total Test Sequences  : {len(test_data['X'])}
   - Combined Sequences    : {len(train_data['X']) + len(val_data['X']) + len(test_data['X'])}

3. Feature Breakdown (22 Dynamic Channels + 9 Static Clinical Features):
   - Dynamic Features: {', '.join(feature_cols)}
   - Static Features : {', '.join(static_cols)}

4. Leakage Prevention Guarantees:
   [PASSED] Strict patient-wise stratification (zero patient overlap between train, val, and test).
   [PASSED] Scaler fitted EXCLUSIVELY on training data, then transformed val/test.
   [PASSED] Static medians computed EXCLUSIVELY on training patients.
   [PASSED] All temporal rolling statistics and IOB/COB decays are strictly causal (past-only).
   [PASSED] Sequences never cross patient or visit boundaries.

5. Deprecated Prototypes:
   - Old prototype .pt models removed from active workspace and moved to data/deprecated/old_test_models/.
"""
    with open(os.path.join(meta_dir, "data_quality_report.txt"), "w") as f:
        f.write(quality_report)

    print(f"\nPipeline successfully completed! Report written to {os.path.join(meta_dir, 'data_quality_report.txt')}")


if __name__ == "__main__":
    audit_and_build_pipeline()
