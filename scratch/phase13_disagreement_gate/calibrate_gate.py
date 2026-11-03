"""
GlucoShield Phase 13 — Calibration Partition Gate Parameter Selection
=====================================================================
Executes principled hyperparameter optimization strictly on the HUPA-UCM
CALIBRATION partition (11,497 windows).

GOVERNANCE:
  - SEALED PARTITION B IS NOT ACCESSED OR TOUCHED IN THIS SCRIPT.
  - All selection decisions are locked prior to Partition B confirmation.
"""

import os
import sys
import json
import numpy as np
import torch

BASE_DIR = "D:/ML PROJECT"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from models.v2.context_encoder import PhysiologicalContextBatch
from models.v2.neural_forecaster import GlucoShieldNeuralForecasterV2
from models.v2.hybrid_forecaster_v2 import GlucoShieldHybridForecasterV2
from scratch.cgmacros_inference import load_frozen_artifacts
from scratch.phase13_disagreement_gate.disagreement_gate import DisagreementAttenuatedFusionGate

DATA_DIR_HUPA = os.path.join(BASE_DIR, "scratch", "phase11_sleep", "data")
OUT_DIR = os.path.join(BASE_DIR, "scratch", "phase13_disagreement_gate")
os.makedirs(OUT_DIR, exist_ok=True)

def calc_rmse(p, t):
    return float(np.sqrt(np.mean((p - t) ** 2)))

def calc_mae(p, t):
    return float(np.mean(np.abs(p - t)))

def calc_bias(p, t):
    return float(np.mean(p - t))

def calc_coverage(t, low, upp):
    return float(np.mean((t >= low) & (t <= upp))) * 100.0

def run_calibration():
    print("=" * 80)
    print("PHASE 13: GATE HYPERPARAMETER OPTIMIZATION (CALIBRATION PARTITION ONLY)")
    print("=" * 80)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Execution Device: {device}")

    # Load frozen scalers
    feat_scaler, stat_scaler, _, _, _ = load_frozen_artifacts(device)

    # Load V2 model
    v2_ckpt_path = os.path.join(BASE_DIR, "models", "v2", "glucoshield_v2_best.pt")
    ckpt = torch.load(v2_ckpt_path, map_location=device)
    v2_neural = GlucoShieldNeuralForecasterV2().to(device)
    v2_hybrid = GlucoShieldHybridForecasterV2(v2_neural, freeze_neural=False, calib_iterations=5).to(device)
    v2_hybrid.load_state_dict(ckpt)
    v2_hybrid.eval()

    # Load HUPA Dataset
    hupa_raw = np.load(os.path.join(DATA_DIR_HUPA, "hupa_windows_stride4.npz"))
    hupa_feat = np.load(os.path.join(DATA_DIR_HUPA, "sleep_features.npz"))

    hupa_dyn_raw = hupa_raw["dynamic_raw"]
    hupa_stat_raw = hupa_raw["static_raw"]
    hupa_targets = hupa_raw["targets"]
    hupa_parts = hupa_feat["partitions"]
    hupa_aligned = hupa_feat["sleep_aligned"]
    hupa_dur = hupa_feat["dur_hours"]
    hupa_eff = hupa_feat["efficiency"]
    hupa_deep = hupa_feat["deep_pct"]
    hupa_debt = hupa_feat["debt_hours"]
    hupa_tau = hupa_feat["tau_wake_hours"]

    # STRICT FILTER: Calibration partition only!
    cal_mask = (hupa_parts == "calibration") & hupa_aligned
    cal_idx = np.where(cal_mask)[0]
    N_cal = len(cal_idx)
    print(f"Selected HUPA Calibration Partition: {N_cal:,} windows (Partition B strictly excluded).")

    # Scale inputs
    N_hupa, T, D = hupa_dyn_raw.shape
    hupa_dyn_scaled = feat_scaler.transform(hupa_dyn_raw.reshape(-1, D)).reshape(N_hupa, T, D).astype(np.float32)
    hupa_stat_scaled = stat_scaler.transform(hupa_stat_raw).astype(np.float32)

    # Context batch for calibration
    psi_decay = np.exp(-np.log(2.0) * np.maximum(0.0, hupa_tau) / 6.0).astype(np.float32)
    f_sleep_hupa = np.stack([hupa_dur / 8.0, hupa_eff, hupa_deep, hupa_debt / 4.0, psi_decay], axis=-1).astype(np.float32)
    sin_24 = hupa_dyn_raw[:, -1, 10]
    cos_24 = hupa_dyn_raw[:, -1, 11]
    f_circ = np.stack([sin_24, cos_24, 2.0*sin_24*cos_24, cos_24**2 - sin_24**2], axis=-1).astype(np.float32)

    ctx_cal = PhysiologicalContextBatch(
        f_exercise=torch.zeros(N_cal, 4, device=device),
        m_exercise=torch.zeros(N_cal, 1, device=device),
        f_sleep=torch.tensor(f_sleep_hupa[cal_mask], dtype=torch.float32, device=device),
        m_sleep=torch.ones(N_cal, 1, device=device),
        f_hormonal=torch.zeros(N_cal, 3, device=device),
        m_hormonal=torch.zeros(N_cal, 1, device=device),
        f_circadian=torch.tensor(f_circ[cal_mask], dtype=torch.float32, device=device)
    )

    tar_cal = hupa_targets[cal_mask]

    # Extract V2 components across calibration partition
    print("Extracting V2 predictions and intermediate states on calibration partition...")
    batch_size = 256
    v2_y_neural = []
    v2_y_ode = []
    v2_alphas = []
    v2_residuals = []
    v2_low95 = []
    v2_upp95 = []
    v2_low80 = []
    v2_upp80 = []

    with torch.no_grad():
        for b_start in range(0, N_cal, batch_size):
            b_end = min(b_start + batch_size, N_cal)
            b_idx = cal_idx[b_start:b_end]

            b_dyn_s = torch.tensor(hupa_dyn_scaled[b_idx], dtype=torch.float32, device=device)
            b_dyn_r = torch.tensor(hupa_dyn_raw[b_idx], dtype=torch.float32, device=device)
            b_stat_s = torch.tensor(hupa_stat_scaled[b_idx], dtype=torch.float32, device=device)
            b_stat_r = torch.tensor(hupa_stat_raw[b_idx], dtype=torch.float32, device=device)

            b_ctx = PhysiologicalContextBatch(
                f_exercise=ctx_cal.f_exercise[b_start:b_end],
                m_exercise=ctx_cal.m_exercise[b_start:b_end],
                f_sleep=ctx_cal.f_sleep[b_start:b_end],
                m_sleep=ctx_cal.m_sleep[b_start:b_end],
                f_hormonal=ctx_cal.f_hormonal[b_start:b_end],
                m_hormonal=ctx_cal.m_hormonal[b_start:b_end],
                f_circadian=ctx_cal.f_circadian[b_start:b_end]
            )

            out = v2_hybrid(b_dyn_s, b_dyn_r, b_stat_s, b_stat_r, b_ctx, calibrate=False, ablation_mode="full_v2")
            v2_y_neural.append(out["y_neural"].cpu().numpy())
            v2_y_ode.append(out["y_ode"].cpu().numpy())
            v2_alphas.append(out["alpha"].cpu().numpy())
            v2_residuals.append(out["residual"].cpu().numpy())

            p_int = out["prediction_interval"]
            v2_low95.append(p_int.lower_95.cpu().numpy())
            v2_upp95.append(p_int.upper_95.cpu().numpy())
            v2_low80.append(p_int.lower_80.cpu().numpy())
            v2_upp80.append(p_int.upper_80.cpu().numpy())

    v2_y_neural = np.concatenate(v2_y_neural, axis=0)
    v2_y_ode = np.concatenate(v2_y_ode, axis=0)
    v2_alphas = np.concatenate(v2_alphas, axis=0)
    v2_residuals = np.concatenate(v2_residuals, axis=0)
    v2_low95 = np.concatenate(v2_low95, axis=0)
    v2_upp95 = np.concatenate(v2_upp95, axis=0)
    v2_low80 = np.concatenate(v2_low80, axis=0)
    v2_upp80 = np.concatenate(v2_upp80, axis=0)

    half_w95 = (v2_upp95 - v2_low95) / 2.0
    half_w80 = (v2_upp80 - v2_low80) / 2.0

    # Benchmark original V2 on calibration partition
    y_v2_orig = v2_alphas * v2_y_neural + (1.0 - v2_alphas) * v2_y_ode + v2_residuals
    orig_rmse = calc_rmse(y_v2_orig, tar_cal)
    orig_mae = calc_mae(y_v2_orig, tar_cal)
    orig_cov95 = calc_coverage(tar_cal, y_v2_orig - half_w95, y_v2_orig + half_w95)
    orig_cov80 = calc_coverage(tar_cal, y_v2_orig - half_w80, y_v2_orig + half_w80)
    print(f"\nOriginal Unrestricted V2 on Calibration Partition:")
    print(f"  RMSE: {orig_rmse:.3f} mg/dL | MAE: {orig_mae:.3f} mg/dL | 95% Cov: {orig_cov95:.2f}% | 80% Cov: {orig_cov80:.2f}%")

    # Define Parameter Grid
    ceilings = [0.30, 0.35, 0.40, 0.45, 0.50]
    d_mids = [25.0, 30.0, 35.0]
    taus = [5.0, 8.0]
    w_highs = [0.15, 0.20, 0.25]

    grid_results = []
    print("\nExecuting grid search across 90 candidate configurations...")

    for c in ceilings:
        for dm in d_mids:
            for tau in taus:
                for wh in w_highs:
                    if wh > c:
                        continue
                    
                    gate = DisagreementAttenuatedFusionGate(ceiling=c, d_mid=dm, tau=tau, w_high=wh)
                    blend_out = gate.blend(v2_y_neural, v2_y_ode, v2_alphas, residual=v2_residuals)
                    y_cand = blend_out["trajectory"]

                    r = calc_rmse(y_cand, tar_cal)
                    m = calc_mae(y_cand, tar_cal)
                    b = calc_bias(y_cand, tar_cal)
                    cov95 = calc_coverage(tar_cal, y_cand - half_w95, y_cand + half_w95)
                    cov80 = calc_coverage(tar_cal, y_cand - half_w80, y_cand + half_w80)
                    mean_pw = float(np.mean(blend_out["w_phys"])) * 100.0

                    grid_results.append({
                        "ceiling": c,
                        "d_mid": dm,
                        "tau": tau,
                        "w_high": wh,
                        "rmse": r,
                        "mae": m,
                        "bias": b,
                        "cov95": cov95,
                        "cov80": cov80,
                        "mean_physics_weight": mean_pw,
                        "rmse_gain": orig_rmse - r
                    })

    # Sort results by lowest RMSE
    grid_results.sort(key=lambda x: x["rmse"])

    print("\nTop 10 Configurations on Calibration Partition:")
    print(f"{'Ceiling':<8} | {'D_mid':<6} | {'Tau':<5} | {'W_high':<7} | {'RMSE':<10} | {'MAE':<10} | {'95% Cov':<8} | {'80% Cov':<8} | {'Mean Phys Wt':<12}")
    print("-" * 88)
    for res in grid_results[:10]:
        print(f"{res['ceiling']:6.2f}   | {res['d_mid']:5.1f}  | {res['tau']:4.1f} | {res['w_high']:6.2f}  | {res['rmse']:8.3f}   | {res['mae']:8.3f}   | {res['cov95']:6.2f}%  | {res['cov80']:6.2f}%  | {res['mean_physics_weight']:10.1f}%")

    # Selection Rule:
    # 1. cov95 >= 95.0%
    # 2. cov80 >= 85.0%
    # 3. Lowest RMSE
    valid_candidates = [r for r in grid_results if r["cov95"] >= 95.0 and r["cov80"] >= 85.0]
    assert len(valid_candidates) > 0, "No candidates met uncertainty preservation criteria!"
    best_candidate = valid_candidates[0]

    print("\n" + "=" * 80)
    print("OPTIMAL CANDIDATE SELECTED FROM CALIBRATION PARTITION:")
    print("=" * 80)
    print(f"  Physics Ceiling:           {best_candidate['ceiling']:.2f} (max physics contribution: {best_candidate['ceiling']*100:.1f}%)")
    print(f"  Disagreement Midpoint:     {best_candidate['d_mid']:.1f} mg/dL")
    print(f"  Transition Scale (tau):    {best_candidate['tau']:.1f} mg/dL")
    print(f"  High-Disagreement Target:  {best_candidate['w_high']:.2f} (max physics during divergence: {best_candidate['w_high']*100:.1f}%)")
    print(f"  Calibration Trajectory RMSE: {best_candidate['rmse']:.3f} mg/dL (Gain vs V2: +{best_candidate['rmse_gain']:.3f} mg/dL)")
    print(f"  Calibration 95% Coverage:    {best_candidate['cov95']:.2f}% (Preserved)")
    print(f"  Calibration 80% Coverage:    {best_candidate['cov80']:.2f}% (Preserved)")

    # Save grid results
    grid_path = os.path.join(OUT_DIR, "calibration_grid_results.json")
    with open(grid_path, "w") as f:
        json.dump(grid_results, f, indent=2)
    print(f"\nSaved all 90 grid results to: {grid_path}")

    # Freeze configuration
    frozen_config = {
        "status": "LOCKED_FROM_CALIBRATION_ONLY",
        "selected_parameters": {
            "ceiling": best_candidate["ceiling"],
            "d_mid": best_candidate["d_mid"],
            "tau": best_candidate["tau"],
            "w_high": best_candidate["w_high"]
        },
        "calibration_metrics": best_candidate,
        "unrestricted_v2_calibration_metrics": {
            "rmse": orig_rmse,
            "mae": orig_mae,
            "cov95": orig_cov95,
            "cov80": orig_cov80
        }
    }
    frozen_path = os.path.join(OUT_DIR, "frozen_gate_config.json")
    with open(frozen_path, "w") as f:
        json.dump(frozen_config, f, indent=2)
    print(f"Saved locked gate configuration to: {frozen_path}")
    print("Parameters are now FROZEN. Ready for single-pass evaluation on Partition B.")

if __name__ == "__main__":
    run_calibration()
