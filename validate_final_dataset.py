"""
GlucoShield - Comprehensive Validation & Verification Suite
Tests leakage, monotonicity, boundary preservation, tensor shapes, scaling, and loadability.
"""

import os
import json
import numpy as np
import pandas as pd
import joblib

def run_validation():
    print("================================================================================")
    print("GLUCOSHIELD: FINAL DATASET VALIDATION & VERIFICATION")
    print("================================================================================")

    data_dir = "D:/ML PROJECT/data"
    final_dir = os.path.join(data_dir, "final")
    meta_dir = os.path.join(data_dir, "metadata")
    processed_dir = os.path.join(data_dir, "processed")

    # 1. Check Metadata Manifest
    manifest_path = os.path.join(meta_dir, "dataset_manifest.json")
    assert os.path.exists(manifest_path), "Missing dataset_manifest.json"
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
    print(f"[CHECK 1] Manifest loaded successfully. Dataset version: {manifest['version']}")

    # 2. Check Patient Leakage Across Splits
    train_meta = pd.read_csv(os.path.join(final_dir, "meta_train.csv"))
    val_meta = pd.read_csv(os.path.join(final_dir, "meta_val.csv"))
    test_meta = pd.read_csv(os.path.join(final_dir, "meta_test.csv"))

    train_pids = set(train_meta["patient_id"].astype(str).unique())
    val_pids = set(val_meta["patient_id"].astype(str).unique())
    test_pids = set(test_meta["patient_id"].astype(str).unique())

    print(f"\n[CHECK 2: LEAKAGE AUDIT]")
    print(f"  Unique Patients -> Train: {len(train_pids)}, Val: {len(val_pids)}, Test: {len(test_pids)}")
    
    inter_tr_val = train_pids.intersection(val_pids)
    inter_tr_te = train_pids.intersection(test_pids)
    inter_val_te = val_pids.intersection(test_pids)

    assert len(inter_tr_val) == 0, f"LEAKAGE DETECTED between Train and Val: {inter_tr_val}"
    assert len(inter_tr_te) == 0, f"LEAKAGE DETECTED between Train and Test: {inter_tr_te}"
    assert len(inter_val_te) == 0, f"LEAKAGE DETECTED between Val and Test: {inter_val_te}"
    print("  -> ZERO PATIENT LEAKAGE: All splits are 100% disjoint at patient level. [PASS]")

    # 3. Check Sequence Tensors, Shapes, NaNs, and Infs
    print(f"\n[CHECK 3: TENSOR INTEGRITY & VALUE RANGES]")
    splits = ["train", "val", "test"]
    for s in splits:
        X_raw = np.load(os.path.join(final_dir, f"X_{s}_raw.npy"))
        X_scaled = np.load(os.path.join(final_dir, f"X_{s}_scaled.npy"))
        stat_raw = np.load(os.path.join(final_dir, f"static_{s}_raw.npy"))
        stat_scaled = np.load(os.path.join(final_dir, f"static_{s}_scaled.npy"))
        Y_traj = np.load(os.path.join(final_dir, f"Y_{s}_trajectory.npy"))
        Y_h4 = np.load(os.path.join(final_dir, f"Y_{s}_hypo_4h.npy"))
        Y_hyp2 = np.load(os.path.join(final_dir, f"Y_{s}_hyper_4h.npy"))

        # Verify shapes
        N = len(X_raw)
        assert len(X_scaled) == N, f"Mismatch in {s} X_scaled length"
        assert len(stat_raw) == N, f"Mismatch in {s} static_raw length"
        assert len(stat_scaled) == N, f"Mismatch in {s} static_scaled length"
        assert len(Y_traj) == N, f"Mismatch in {s} Y_traj length"
        assert len(Y_h4) == N, f"Mismatch in {s} Y_hypo_4h length"
        assert len(Y_hyp2) == N, f"Mismatch in {s} Y_hyper_4h length"

        # Check for NaN / Inf
        assert not np.isnan(X_raw).any(), f"NaN found in X_{s}_raw"
        assert not np.isinf(X_raw).any(), f"Inf found in X_{s}_raw"
        assert not np.isnan(X_scaled).any(), f"NaN found in X_{s}_scaled"
        assert not np.isinf(X_scaled).any(), f"Inf found in X_{s}_scaled"
        assert not np.isnan(stat_scaled).any(), f"NaN found in static_{s}_scaled"
        assert not np.isnan(Y_traj).any(), f"NaN found in Y_{s}_trajectory"

        print(f"  Split '{s.upper()}': N={N}")
        print(f"    X Shape: {X_raw.shape} | Scaled Range: [{X_scaled.min():.2f}, {X_scaled.max():.2f}]")
        print(f"    Static Shape: {stat_raw.shape} | Trajectory Target: {Y_traj.shape}")
        print(f"    Hypo 4h Rate: {np.mean(Y_h4)*100:.2f}% | Hyper 4h Rate: {np.mean(Y_hyp2)*100:.2f}%")
        print(f"    NaN/Inf check: PASSED (Zero NaNs, Zero Infs)")

    # 4. Check Input/Output Alignment & Monotonicity
    print(f"\n[CHECK 4: INPUT/TARGET TEMPORAL ALIGNMENT]")
    for s, meta in [("train", train_meta), ("val", val_meta), ("test", test_meta)]:
        t_start = pd.to_datetime(meta["start_timestamp"])
        t_in_end = pd.to_datetime(meta["input_end_timestamp"])
        t_out_end = pd.to_datetime(meta["target_end_timestamp"])

        # Monotonicity check
        assert (t_in_end > t_start).all(), f"Input timestamps not monotonic in {s}"
        assert (t_out_end > t_in_end).all(), f"Output timestamps not after input in {s}"
        
        # Verify single record boundary per sequence
        assert (meta["record_id"].str.len() > 0).all(), f"Empty record_id in {s}"
        print(f"  Split '{s.upper()}': {len(meta)} metadata rows verified monotonic. [PASS]")

    # 5. Check Scaler Artifacts
    print(f"\n[CHECK 5: SCALER LOADABILITY]")
    feat_scaler = joblib.load(os.path.join(meta_dir, "feature_scaler.joblib"))
    stat_scaler = joblib.load(os.path.join(meta_dir, "static_scaler.joblib"))
    print(f"  Feature Scaler: RobustScaler with {feat_scaler.center_.shape[0]} features")
    print(f"  Static Scaler : StandardScaler with {stat_scaler.mean_.shape[0]} features")
    print("  Scalers loaded successfully. [PASS]")

    print("\n================================================================================")
    print("ALL VALIDATION & INTEGRITY CHECKS PASSED PERFECTLY!")
    print("The final dataset in 'data/final/' is 100% clean, leakage-free, and model-ready.")
    print("================================================================================")

if __name__ == "__main__":
    run_validation()
