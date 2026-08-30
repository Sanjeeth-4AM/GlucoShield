"""
GlucoShield Phase 6 — Master Pre-Flight Integrity Audit & Manifest Generator
=============================================================================
Computes SHA256 checksums, verifies array shapes, sequence alignments,
patient-level isolation, and environment dependencies.
"""

import os
import sys
import json
import hashlib
import platform
import numpy as np
import pandas as pd
import torch
import sklearn
import scipy
import matplotlib

BASE_DIR = "D:/ML PROJECT"
DATA_DIR = os.path.join(BASE_DIR, "data", "final")
META_DIR = os.path.join(BASE_DIR, "data", "metadata")
MODELS_DIR = os.path.join(BASE_DIR, "models")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
OUT_DIR = os.path.join(BASE_DIR, "evaluation", "phase6", "results")

os.makedirs(OUT_DIR, exist_ok=True)

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def run_preflight_audit():
    print("=" * 80)
    print("GLUCOSHIELD PHASE 6 — PRE-FLIGHT INTEGRITY & REPRODUCIBILITY AUDIT")
    print("=" * 80)

    # 1. Environment Information
    env_info = {
        "python_version": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "pytorch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_version": torch.version.cuda if torch.cuda.is_available() else None,
        "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
        "scipy_version": scipy.__version__,
        "sklearn_version": sklearn.__version__,
        "matplotlib_version": matplotlib.__version__
    }

    print("\n[1] Environment & Hardware:")
    for k, v in env_info.items():
        print(f"  {k:<22}: {v}")

    # 2. Audit Dataset v1.0 Files
    print("\n[2] Verifying Dataset v1.0 Files...")
    meta_train = pd.read_csv(os.path.join(DATA_DIR, "meta_train.csv"))
    meta_val = pd.read_csv(os.path.join(DATA_DIR, "meta_val.csv"))
    meta_test = pd.read_csv(os.path.join(DATA_DIR, "meta_test.csv"))

    train_pts = set(meta_train["patient_id"].unique())
    val_pts = set(meta_val["patient_id"].unique())
    test_pts = set(meta_test["patient_id"].unique())

    # Leakage checks
    assert len(train_pts.intersection(val_pts)) == 0, "Train-Val patient leakage detected!"
    assert len(train_pts.intersection(test_pts)) == 0, "Train-Test patient leakage detected!"
    assert len(val_pts.intersection(test_pts)) == 0, "Val-Test patient leakage detected!"

    print(f"  Train: {len(train_pts)} patients, {len(meta_train)} sequences")
    print(f"  Val:   {len(val_pts)} patients, {len(meta_val)} sequences")
    print(f"  Test:  {len(test_pts)} patients, {len(meta_test)} sequences")
    print("  --> Patient Leakage Audit: PASS (Zero overlap between all splits)")

    # 3. Audit Checkpoints and Prediction Arrays
    print("\n[3] Auditing Models and Prediction Arrays...")
    frozen_files = {
        "dataset_manifest": os.path.join(META_DIR, "dataset_manifest.json"),
        "meta_train": os.path.join(DATA_DIR, "meta_train.csv"),
        "meta_val": os.path.join(DATA_DIR, "meta_val.csv"),
        "meta_test": os.path.join(DATA_DIR, "meta_test.csv"),
        "X_test_scaled": os.path.join(DATA_DIR, "X_test_scaled.npy"),
        "X_test_raw": os.path.join(DATA_DIR, "X_test_raw.npy"),
        "static_test_scaled": os.path.join(DATA_DIR, "static_test_scaled.npy"),
        "static_test_raw": os.path.join(DATA_DIR, "static_test_raw.npy"),
        "Y_test_trajectory": os.path.join(DATA_DIR, "Y_test_trajectory.npy"),
        "Y_test_hypo_1h": os.path.join(DATA_DIR, "Y_test_hypo_1h.npy"),
        "Y_test_hypo_2h": os.path.join(DATA_DIR, "Y_test_hypo_2h.npy"),
        "Y_test_hypo_4h": os.path.join(DATA_DIR, "Y_test_hypo_4h.npy"),
        "Y_test_hyper_2h": os.path.join(DATA_DIR, "Y_test_hyper_2h.npy"),
        "Y_test_hyper_4h": os.path.join(DATA_DIR, "Y_test_hyper_4h.npy"),
        "model_neural_best": os.path.join(MODELS_DIR, "glucoshield_neural_best.pt"),
        "model_hybrid_best": os.path.join(MODELS_DIR, "glucoshield_hybrid_best.pt"),
        "preds_ridge_test": os.path.join(RESULTS_DIR, "baselines", "preds_classical_ridge_test.npy"),
        "preds_linear_trend_test": os.path.join(RESULTS_DIR, "baselines", "preds_linear_trend_test.npy"),
        "preds_persistence_test": os.path.join(RESULTS_DIR, "baselines", "preds_persistence_test.npy"),
        "preds_neural_test": os.path.join(RESULTS_DIR, "neural", "preds_best_neural_test.npy"),
        "probs_neural_risk_test": os.path.join(RESULTS_DIR, "neural", "probs_best_neural_test.npy"),
        "preds_ode_standalone_test": os.path.join(RESULTS_DIR, "digital_twin", "preds_ode_standalone_test.npy"),
        "preds_hybrid_test": os.path.join(RESULTS_DIR, "digital_twin", "preds_hybrid_test.npy"),
        "probs_hybrid_risk_test": os.path.join(RESULTS_DIR, "digital_twin", "probs_risk_hybrid_test.npy")
    }

    file_manifest = {}
    for name, path in frozen_files.items():
        assert os.path.exists(path), f"Missing frozen file: {path}"
        sz = os.path.getsize(path)
        sha = sha256_file(path)
        file_manifest[name] = {
            "path": os.path.relpath(path, BASE_DIR).replace("\\", "/"),
            "size_bytes": sz,
            "sha256": sha
        }
        print(f"  {name:<28}: size={sz:>10,} B | SHA256[:16]={sha[:16]}")

    # 4. Numerical Health and Target Alignment Verification
    print("\n[4] Numerical Health & Array Alignment Verification...")
    y_true = np.load(frozen_files["Y_test_trajectory"])
    assert y_true.shape == (4113, 20), f"Unexpected Y_test shape: {y_true.shape}"
    assert not np.isnan(y_true).any(), "NaNs detected in Y_test_trajectory!"
    assert not np.isinf(y_true).any(), "Infs detected in Y_test_trajectory!"

    pred_keys = ["preds_ridge_test", "preds_linear_trend_test", "preds_persistence_test", "preds_neural_test", "preds_ode_standalone_test", "preds_hybrid_test"]
    baseline_metrics = {}
    for k in pred_keys:
        p_arr = np.load(frozen_files[k])
        assert p_arr.shape == y_true.shape, f"Shape mismatch for {k}: {p_arr.shape} vs {y_true.shape}"
        assert not np.isnan(p_arr).any(), f"NaNs detected in {k}!"
        assert not np.isinf(p_arr).any(), f"Infs detected in {k}!"
        diff = p_arr - y_true
        mae = float(np.mean(np.abs(diff)))
        rmse = float(np.sqrt(np.mean(diff ** 2)))
        baseline_metrics[k] = {"MAE": round(mae, 4), "RMSE": round(rmse, 4)}
        print(f"  {k:<28}: MAE = {mae:>7.4f} mg/dL | RMSE = {rmse:>7.4f} mg/dL [OK]")

    # 5. Export Master Audit Manifest JSON
    master_manifest = {
        "audit_name": "GlucoShield Phase 6 Pre-Flight Integrity & Evaluation Manifest",
        "timestamp": pd.Timestamp.now().isoformat(),
        "environment": env_info,
        "cohort_summary": {
            "total_patients": 112,
            "train_patients": len(train_pts),
            "val_patients": len(val_pts),
            "test_patients": len(test_pts),
            "test_t1dm_patients": len(meta_test[meta_test["diabetes_type"] == "T1DM"]["patient_id"].unique()),
            "test_t2dm_patients": len(meta_test[meta_test["diabetes_type"] == "T2DM"]["patient_id"].unique()),
            "total_sequences": 28447,
            "train_sequences": len(meta_train),
            "val_sequences": len(meta_val),
            "test_sequences": len(meta_test)
        },
        "file_inventory": file_manifest,
        "verified_test_metrics": baseline_metrics
    }

    manifest_path = os.path.join(OUT_DIR, "evaluation_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(master_manifest, f, indent=2)
    print(f"\nSaved master evaluation manifest to: {manifest_path}")
    print("=" * 80)
    return master_manifest

if __name__ == "__main__":
    run_preflight_audit()
