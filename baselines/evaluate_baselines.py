"""
GlucoShield Comprehensive Trajectory & Subgroup Evaluation Suite
Reusable evaluation engine for all baseline, neural, physics, and digital twin models.
"""

import numpy as np
import pandas as pd

def clarke_error_grid(y_true, y_pred):
    """
    Computes Clarke Error Grid Analysis Zone percentages (Zone A, Zone B, Zone A+B).
    y_true: reference blood glucose (mg/dL)
    y_pred: predicted blood glucose (mg/dL)
    """
    y_true = np.asarray(y_true, dtype=np.float64).flatten()
    y_pred = np.asarray(y_pred, dtype=np.float64).flatten()
    N = len(y_true)
    if N == 0:
        return {"Zone_A_pct": 0.0, "Zone_B_pct": 0.0, "Zone_AB_pct": 0.0}

    zone_a = 0
    zone_b = 0
    zone_c = 0
    zone_d = 0
    zone_e = 0

    for act, pred in zip(y_true, y_pred):
        # Zone A
        if (pred <= 70 and act <= 70) or (pred >= 0.8 * act and pred <= 1.2 * act):
            zone_a += 1
        # Zone E (erroneous treatment)
        elif (act <= 70 and pred >= 180) or (act >= 180 and pred <= 70):
            zone_e += 1
        # Zone D (failure to detect)
        elif (act >= 70 and act <= 240 and (pred < 70 or pred > 240)) or \
             (act <= 70 and pred > 70 and pred < 180) or \
             (act >= 240 and pred > 70 and pred < 180):
            zone_d += 1
        # Zone C (overcorrection)
        elif (act >= 130 and act <= 180 and pred <= 70) or \
             (act >= 70 and act <= 100 and pred >= 180):
            zone_c += 1
        # Zone B (benign errors)
        else:
            zone_b += 1

    pct_a = float(zone_a / N * 100.0)
    pct_b = float(zone_b / N * 100.0)
    pct_ab = float((zone_a + zone_b) / N * 100.0)

    return {
        "Zone_A_pct": pct_a,
        "Zone_B_pct": pct_b,
        "Zone_AB_pct": pct_ab
    }


def evaluate_trajectory(Y_pred, Y_true, meta_df=None):
    """
    Computes overall, horizon-wise, subgroup, and per-patient trajectory forecast metrics.
    
    Args:
        Y_pred: np.ndarray of shape (N, 20)
        Y_true: np.ndarray of shape (N, 20)
        meta_df: pd.DataFrame of shape (N, ...) containing 'patient_id', 'diabetes_type'
    Returns:
        metrics: dict of comprehensive metric tables
    """
    Y_pred = np.asarray(Y_pred, dtype=np.float32)
    Y_true = np.asarray(Y_true, dtype=np.float32)
    N, K = Y_true.shape
    assert Y_pred.shape == Y_true.shape, f"Shape mismatch: {Y_pred.shape} vs {Y_true.shape}"

    # 1. Global Metrics
    diff = Y_pred - Y_true
    overall_mae = float(np.mean(np.abs(diff)))
    overall_rmse = float(np.sqrt(np.mean(diff ** 2)))
    ega_global = clarke_error_grid(Y_true, Y_pred)

    # 2. Horizon-wise metrics (15-min intervals: 1h=step 4, 2h=step 8, 3h=step 12, 4h=step 16, 5h=step 20)
    horizons = {
        "15min (k=1)": 0,
        "30min (k=2)": 1,
        "45min (k=3)": 2,
        "1h (k=4)": 3,
        "2h (k=8)": 7,
        "3h (k=12)": 11,
        "4h (k=16)": 15,
        "5h (k=20)": 19
    }
    horizon_metrics = {}
    for h_name, h_idx in horizons.items():
        h_diff = diff[:, h_idx]
        h_mae = float(np.mean(np.abs(h_diff)))
        h_rmse = float(np.sqrt(np.mean(h_diff ** 2)))
        h_ega = clarke_error_grid(Y_true[:, h_idx], Y_pred[:, h_idx])
        horizon_metrics[h_name] = {
            "MAE": h_mae,
            "RMSE": h_rmse,
            "Zone_AB_pct": h_ega["Zone_AB_pct"]
        }

    # 3. Subgroup & Patient-level metrics (if metadata provided)
    subgroups = {}
    patient_metrics = {}
    macro_patient = {}

    if meta_df is not None:
        meta_df = meta_df.reset_index(drop=True)
        assert len(meta_df) == N, f"Metadata length {len(meta_df)} != {N}"

        # Subgroups: T1DM vs T2DM
        for dtype in ["T1DM", "T2DM"]:
            mask = (meta_df["diabetes_type"] == dtype).values
            n_sub = int(np.sum(mask))
            if n_sub > 0:
                sub_diff = diff[mask]
                sub_mae = float(np.mean(np.abs(sub_diff)))
                sub_rmse = float(np.sqrt(np.mean(sub_diff ** 2)))
                sub_ega = clarke_error_grid(Y_true[mask], Y_pred[mask])
                subgroups[dtype] = {
                    "num_sequences": n_sub,
                    "num_patients": int(meta_df[mask]["patient_id"].nunique()),
                    "MAE": sub_mae,
                    "RMSE": sub_rmse,
                    "Zone_AB_pct": sub_ega["Zone_AB_pct"]
                }

        # Per-patient metrics
        p_maes = []
        p_rmses = []
        for pid, pgrp in meta_df.groupby("patient_id"):
            p_idx = pgrp.index.values
            p_diff = diff[p_idx]
            p_mae = float(np.mean(np.abs(p_diff)))
            p_rmse = float(np.sqrt(np.mean(p_diff ** 2)))
            p_dtype = str(pgrp["diabetes_type"].iloc[0])
            patient_metrics[str(pid)] = {
                "patient_id": str(pid),
                "diabetes_type": p_dtype,
                "num_sequences": len(p_idx),
                "MAE": p_mae,
                "RMSE": p_rmse
            }
            p_maes.append(p_mae)
            p_rmses.append(p_rmse)

        # Macro-averaged patient metrics
        macro_patient = {
            "macro_patient_mae_mean": float(np.mean(p_maes)),
            "macro_patient_mae_std": float(np.std(p_maes)),
            "macro_patient_rmse_mean": float(np.mean(p_rmses)),
            "macro_patient_rmse_std": float(np.std(p_rmses))
        }

    return {
        "overall": {
            "num_sequences": N,
            "MAE": overall_mae,
            "RMSE": overall_rmse,
            "Zone_A_pct": ega_global["Zone_A_pct"],
            "Zone_B_pct": ega_global["Zone_B_pct"],
            "Zone_AB_pct": ega_global["Zone_AB_pct"]
        },
        "horizons": horizon_metrics,
        "subgroups": subgroups,
        "macro_patient": macro_patient,
        "per_patient": patient_metrics
    }


def format_metric_table(eval_res):
    """
    Formats evaluation results into a clean string representation.
    """
    ov = eval_res["overall"]
    hz = eval_res["horizons"]
    sg = eval_res["subgroups"]
    mp = eval_res["macro_patient"]

    lines = []
    lines.append(f"Overall MAE: {ov['MAE']:.2f} mg/dL | Overall RMSE: {ov['RMSE']:.2f} mg/dL | Clarke A+B: {ov['Zone_AB_pct']:.2f}%")
    lines.append(f"Macro-Patient MAE: {mp.get('macro_patient_mae_mean', 0.0):.2f} ± {mp.get('macro_patient_mae_std', 0.0):.2f} mg/dL | RMSE: {mp.get('macro_patient_rmse_mean', 0.0):.2f} ± {mp.get('macro_patient_rmse_std', 0.0):.2f} mg/dL")
    if "T1DM" in sg:
        lines.append(f"T1DM Subgroup ({sg['T1DM']['num_patients']} pts, {sg['T1DM']['num_sequences']} seqs): MAE={sg['T1DM']['MAE']:.2f}, RMSE={sg['T1DM']['RMSE']:.2f} mg/dL")
    if "T2DM" in sg:
        lines.append(f"T2DM Subgroup ({sg['T2DM']['num_patients']} pts, {sg['T2DM']['num_sequences']} seqs): MAE={sg['T2DM']['MAE']:.2f}, RMSE={sg['T2DM']['RMSE']:.2f} mg/dL")
    return "\n".join(lines)
