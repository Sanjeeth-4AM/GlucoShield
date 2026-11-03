"""
GlucoShield Phase 13 — Sealed Partition B Confirmation
======================================================
Executes ONE-TIME unbiased evaluation of the frozen Phase-13 Disagreement-Attenuated Gate
on the sealed HUPA-UCM Partition B evaluation set (10,785 windows).

GOVERNANCE:
  - Gate hyperparameters are frozen from Calibration partition.
  - Zero tuning or adjustment performed on Partition B.
  - All outputs saved to scratch/phase13_disagreement_gate/.
"""

import os
import sys
import json
import numpy as np
import torch
from scipy import stats

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

def calc_rmse(p, t):
    return float(np.sqrt(np.mean((p - t) ** 2)))

def calc_mae(p, t):
    return float(np.mean(np.abs(p - t)))

def calc_bias(p, t):
    return float(np.mean(p - t))

def calc_coverage(t, low, upp):
    return float(np.mean((t >= low) & (t <= upp))) * 100.0

def calc_mean_width(low, upp):
    return float(np.mean(upp - low))

def bootstrap_ci(diffs, n_boot=2000, alpha=0.05):
    rng = np.random.RandomState(42)
    boot_means = [np.mean(rng.choice(diffs, size=len(diffs), replace=True)) for _ in range(n_boot)]
    low = float(np.percentile(boot_means, 100.0 * (alpha / 2.0)))
    high = float(np.percentile(boot_means, 100.0 * (1.0 - alpha / 2.0)))
    return low, high

def run_confirmation():
    print("=" * 80)
    print("PHASE 13: SEALED PARTITION B CONFIRMATION (ONE-TIME FINAL EVALUATION)")
    print("=" * 80)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # Load frozen gate parameters
    config_path = os.path.join(OUT_DIR, "frozen_gate_config.json")
    with open(config_path) as f:
        frozen_cfg = json.load(f)
    params = frozen_cfg["selected_parameters"]
    print(f"Loaded Frozen Phase-13 Gate Parameters:")
    print(f"  Ceiling: {params['ceiling']:.2f} | D_mid: {params['d_mid']:.1f} mg/dL | Tau: {params['tau']:.1f} | W_high: {params['w_high']:.2f}")

    gate_p13 = DisagreementAttenuatedFusionGate(
        ceiling=params["ceiling"],
        d_mid=params["d_mid"],
        tau=params["tau"],
        w_high=params["w_high"]
    )

    # Load Frozen Scalers and Models
    feat_scaler, stat_scaler, v1_neural, v1_hybrid, v1_uncertainty = load_frozen_artifacts(device)
    v1_neural.eval()
    v1_hybrid.eval()

    v2_ckpt_path = os.path.join(BASE_DIR, "models", "v2", "glucoshield_v2_best.pt")
    ckpt = torch.load(v2_ckpt_path, map_location=device)
    v2_neural = GlucoShieldNeuralForecasterV2().to(device)
    v2_hybrid = GlucoShieldHybridForecasterV2(v2_neural, freeze_neural=False, calib_iterations=5).to(device)
    v2_hybrid.load_state_dict(ckpt)
    v2_hybrid.eval()

    # Load Partition B Data
    hupa_raw = np.load(os.path.join(DATA_DIR_HUPA, "hupa_windows_stride4.npz"))
    hupa_feat = np.load(os.path.join(DATA_DIR_HUPA, "sleep_features.npz"))
    p_hupa = np.load(os.path.join(DATA_DIR_HUPA, "sleep_ablation_predictions.npz"))

    hupa_dyn_raw = hupa_raw["dynamic_raw"]
    hupa_stat_raw = hupa_raw["static_raw"]
    hupa_targets = hupa_raw["targets"]
    hupa_pids = hupa_feat["pids"]
    hupa_parts = hupa_feat["partitions"]
    hupa_aligned = hupa_feat["sleep_aligned"]
    hupa_dur = hupa_feat["dur_hours"]
    hupa_eff = hupa_feat["efficiency"]
    hupa_deep = hupa_feat["deep_pct"]
    hupa_debt = hupa_feat["debt_hours"]
    hupa_tau = hupa_feat["tau_wake_hours"]

    eval_mask = (hupa_parts == "evaluation") & hupa_aligned
    eval_idx = np.where(eval_mask)[0]
    N_eval = len(eval_idx)
    print(f"Sealed Partition B Evaluation Set: {N_eval:,} windows.")

    # Scaled inputs
    N_hupa, T, D = hupa_dyn_raw.shape
    hupa_dyn_scaled = feat_scaler.transform(hupa_dyn_raw.reshape(-1, D)).reshape(N_hupa, T, D).astype(np.float32)
    hupa_stat_scaled = stat_scaler.transform(hupa_stat_raw).astype(np.float32)

    # Context batch
    psi_decay = np.exp(-np.log(2.0) * np.maximum(0.0, hupa_tau) / 6.0).astype(np.float32)
    f_sleep_hupa = np.stack([hupa_dur / 8.0, hupa_eff, hupa_deep, hupa_debt / 4.0, psi_decay], axis=-1).astype(np.float32)
    sin_24 = hupa_dyn_raw[:, -1, 10]
    cos_24 = hupa_dyn_raw[:, -1, 11]
    f_circ = np.stack([sin_24, cos_24, 2.0*sin_24*cos_24, cos_24**2 - sin_24**2], axis=-1).astype(np.float32)

    ctx_eval = PhysiologicalContextBatch(
        f_exercise=torch.zeros(N_eval, 4, device=device),
        m_exercise=torch.zeros(N_eval, 1, device=device),
        f_sleep=torch.tensor(f_sleep_hupa[eval_mask], dtype=torch.float32, device=device),
        m_sleep=torch.ones(N_eval, 1, device=device),
        f_hormonal=torch.zeros(N_eval, 3, device=device),
        m_hormonal=torch.zeros(N_eval, 1, device=device),
        f_circadian=torch.tensor(f_circ[eval_mask], dtype=torch.float32, device=device)
    )

    tar_eval = hupa_targets[eval_mask]
    eval_pids = hupa_pids[eval_mask]
    unique_pids = np.unique(eval_pids)
    short_mask = (hupa_dur[eval_mask] < 6.0)

    std_1h = hupa_dyn_raw[eval_mask, -1, 4]
    t1, t2 = np.percentile(std_1h, [33.3, 66.7])
    low_vol_mask = (std_1h < t1)
    med_vol_mask = (std_1h >= t1) & (std_1h < t2)
    high_vol_mask = (std_1h >= t2)

    # Baseline V1 Predictions
    preds_v1_hybrid = p_hupa["preds_e0"]
    low95_v1 = p_hupa["lower_95_e0"]
    upp95_v1 = p_hupa["upper_95_e0"]
    low80_v1 = p_hupa["lower_80_e0"]
    upp80_v1 = p_hupa["upper_80_e0"]

    # Extract V2 components
    print("\nExtracting V2 predictions on Partition B...")
    batch_size = 256
    v2_y_final = []
    v2_y_neural = []
    v2_y_ode = []
    v2_alphas = []
    v2_residuals = []
    v2_low95 = []
    v2_upp95 = []
    v2_low80 = []
    v2_upp80 = []

    with torch.no_grad():
        for b_start in range(0, N_eval, batch_size):
            b_end = min(b_start + batch_size, N_eval)
            b_idx = eval_idx[b_start:b_end]

            b_dyn_s = torch.tensor(hupa_dyn_scaled[b_idx], dtype=torch.float32, device=device)
            b_dyn_r = torch.tensor(hupa_dyn_raw[b_idx], dtype=torch.float32, device=device)
            b_stat_s = torch.tensor(hupa_stat_scaled[b_idx], dtype=torch.float32, device=device)
            b_stat_r = torch.tensor(hupa_stat_raw[b_idx], dtype=torch.float32, device=device)

            b_ctx = PhysiologicalContextBatch(
                f_exercise=ctx_eval.f_exercise[b_start:b_end],
                m_exercise=ctx_eval.m_exercise[b_start:b_end],
                f_sleep=ctx_eval.f_sleep[b_start:b_end],
                m_sleep=ctx_eval.m_sleep[b_start:b_end],
                f_hormonal=ctx_eval.f_hormonal[b_start:b_end],
                m_hormonal=ctx_eval.m_hormonal[b_start:b_end],
                f_circadian=ctx_eval.f_circadian[b_start:b_end]
            )

            out = v2_hybrid(b_dyn_s, b_dyn_r, b_stat_s, b_stat_r, b_ctx, calibrate=False, ablation_mode="full_v2")
            v2_y_final.append(out["trajectory"].cpu().numpy())
            v2_y_neural.append(out["y_neural"].cpu().numpy())
            v2_y_ode.append(out["y_ode"].cpu().numpy())
            v2_alphas.append(out["alpha"].cpu().numpy())
            v2_residuals.append(out["residual"].cpu().numpy())

            p_int = out["prediction_interval"]
            v2_low95.append(p_int.lower_95.cpu().numpy())
            v2_upp95.append(p_int.upper_95.cpu().numpy())
            v2_low80.append(p_int.lower_80.cpu().numpy())
            v2_upp80.append(p_int.upper_80.cpu().numpy())

    v2_y_final = np.concatenate(v2_y_final, axis=0)
    v2_y_neural = np.concatenate(v2_y_neural, axis=0)
    v2_y_ode = np.concatenate(v2_y_ode, axis=0)
    v2_alphas = np.concatenate(v2_alphas, axis=0)
    v2_residuals = np.concatenate(v2_residuals, axis=0)
    v2_low95 = np.concatenate(v2_low95, axis=0)
    v2_upp95 = np.concatenate(v2_upp95, axis=0)
    v2_low80 = np.concatenate(v2_low80, axis=0)
    v2_upp80 = np.concatenate(v2_upp80, axis=0)

    # --------------------------------------------------------------------------
    # COMPUTE PHASE 13 BLEND
    # --------------------------------------------------------------------------
    print("\nComputing Phase 13 Disagreement-Attenuated Blend on Partition B...")
    blend_p13 = gate_p13.blend(v2_y_neural, v2_y_ode, v2_alphas, residual=v2_residuals)
    p13_y_final = blend_p13["trajectory"]
    p13_alpha_eff = blend_p13["alpha_eff"]
    p13_w_phys = blend_p13["w_phys"]
    p13_disagreement = blend_p13["disagreement"]

    # Uncertainty intervals centered on Phase-13 point forecast
    half_w95 = (v2_upp95 - v2_low95) / 2.0
    half_w80 = (v2_upp80 - v2_low80) / 2.0
    p13_low95 = p13_y_final - half_w95
    p13_upp95 = p13_y_final + half_w95
    p13_low80 = p13_y_final - half_w80
    p13_upp80 = p13_y_final + half_w80

    # --------------------------------------------------------------------------
    # 1. PRIMARY COMPARISON: E0 (Frozen V1) vs E1 (Original V2) vs E2 (Phase 13)
    # --------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("1. PRIMARY CONFIRMATION: E0 (Frozen V1) vs E1 (Original V2) vs E2 (Phase 13)")
    print("=" * 80)

    models_eval = [
        ("E0: Frozen V1 Baseline", preds_v1_hybrid, low95_v1, upp95_v1, low80_v1, upp80_v1, 0.9147, 0.0853),
        ("E1: Original V2 Hybrid", v2_y_final, v2_low95, v2_upp95, v2_low80, v2_upp80, float(np.mean(v2_alphas)), float(np.mean(1.0 - v2_alphas))),
        ("E2: Phase-13 Disagreement-Gated V2", p13_y_final, p13_low95, p13_upp95, p13_low80, p13_upp80, float(np.mean(p13_alpha_eff)), float(np.mean(p13_w_phys)))
    ]

    primary_table = []
    print(f"{'Model / Condition':<35} | {'RMSE':<10} | {'MAE':<10} | {'Bias':<10} | {'Part RMSE':<10} | {'Short RMSE':<10} | {'H-Vol RMSE':<10} | {'95% Cov':<8} | {'80% Cov':<8} | {'Physics Wt':<10}")
    print("-" * 135)

    for name, yp, l95, u95, l80, u80, a_m, p_m in models_eval:
        r = calc_rmse(yp, tar_eval)
        m = calc_mae(yp, tar_eval)
        b = calc_bias(yp, tar_eval)
        p_rmses = [calc_rmse(yp[eval_pids == pid], tar_eval[eval_pids == pid]) for pid in unique_pids]
        p_rmse = float(np.mean(p_rmses))
        r_short = calc_rmse(yp[short_mask], tar_eval[short_mask])
        r_hvol = calc_rmse(yp[high_vol_mask], tar_eval[high_vol_mask])
        c95 = calc_coverage(tar_eval, l95, u95)
        c80 = calc_coverage(tar_eval, l80, u80)
        
        primary_table.append({
            "name": name, "rmse": r, "mae": m, "bias": b, "part_rmse": p_rmse,
            "short_sleep_rmse": r_short, "high_vol_rmse": r_hvol,
            "cov95": c95, "cov80": c80, "mean_physics_weight": p_m * 100.0,
            "mean_neural_weight": a_m * 100.0
        })
        print(f"{name:<35} | {r:8.3f}   | {m:8.3f}   | {b:+8.3f}   | {p_rmse:8.3f}   | {r_short:8.3f}   | {r_hvol:8.3f}   | {c95:6.2f}%  | {c80:6.2f}%  | {p_m*100:8.2f}%")

    # Participant delta comparison (E2 vs E0, and E2 vs E1)
    p_v1_rmses = np.array([calc_rmse(preds_v1_hybrid[eval_pids == pid], tar_eval[eval_pids == pid]) for pid in unique_pids])
    p_v2_rmses = np.array([calc_rmse(v2_y_final[eval_pids == pid], tar_eval[eval_pids == pid]) for pid in unique_pids])
    p_p13_rmses = np.array([calc_rmse(p13_y_final[eval_pids == pid], tar_eval[eval_pids == pid]) for pid in unique_pids])

    deltas_p13_vs_v2 = p_v2_rmses - p_p13_rmses # positive = P13 improved over V2
    deltas_p13_vs_v1 = p_v1_rmses - p_p13_rmses # positive = P13 improved over V1

    n_improved_vs_v2 = int(np.sum(deltas_p13_vs_v2 > 0))
    n_worsened_vs_v2 = int(np.sum(deltas_p13_vs_v2 < 0))
    n_improved_vs_v1 = int(np.sum(deltas_p13_vs_v1 > 0))
    n_worsened_vs_v1 = int(np.sum(deltas_p13_vs_v1 < 0))

    med_delta_v2 = float(np.median(deltas_p13_vs_v2))
    med_delta_v1 = float(np.median(deltas_p13_vs_v1))
    iqr_delta_v1 = float(np.percentile(deltas_p13_vs_v1, 75) - np.percentile(deltas_p13_vs_v1, 25))
    min_delta_v1 = float(np.min(deltas_p13_vs_v1))
    max_delta_v1 = float(np.max(deltas_p13_vs_v1))

    print(f"\nParticipant-Level Transitions:")
    print(f"  Phase-13 vs Original V2: Improved = {n_improved_vs_v2}/23 ({n_improved_vs_v2/23*100:.1f}%) | Worsened = {n_worsened_vs_v2}/23 | Median Gain: +{med_delta_v2:.3f} mg/dL")
    print(f"  Phase-13 vs Frozen V1:   Improved = {n_improved_vs_v1}/23 ({n_improved_vs_v1/23*100:.1f}%) | Worsened = {n_worsened_vs_v1}/23 | Median Delta: {med_delta_v1:+.3f} mg/dL (IQR: {iqr_delta_v1:.3f})")

    # --------------------------------------------------------------------------
    # 2. DISAGREEMENT-SPECIFIC VALIDATION ACROSS 5 BANDS
    # --------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("2. DISAGREEMENT-SPECIFIC VALIDATION ACROSS 5 BANDS")
    print("=" * 80)

    mean_d = np.mean(p13_disagreement, axis=-1)
    bands = [
        ("<10 mg/dL", mean_d < 10.0),
        ("10-20 mg/dL", (mean_d >= 10.0) & (mean_d < 20.0)),
        ("20-30 mg/dL", (mean_d >= 20.0) & (mean_d < 30.0)),
        ("30-50 mg/dL", (mean_d >= 30.0) & (mean_d < 50.0)),
        (">50 mg/dL", mean_d >= 50.0)
    ]

    disagreement_table = []
    print(f"{'Band':<12} | {'Windows':<8} | {'Pct':<6} | {'V1 RMSE':<10} | {'V2 RMSE':<10} | {'P13 RMSE':<10} | {'P13 vs V2':<10} | {'P13 vs V1':<10} | {'P13 Phys Wt':<12}")
    print("-" * 105)

    for b_name, b_m in bands:
        n_w = int(np.sum(b_m))
        pct_w = (n_w / N_eval) * 100.0
        r_v1 = calc_rmse(preds_v1_hybrid[b_m], tar_eval[b_m])
        r_v2 = calc_rmse(v2_y_final[b_m], tar_eval[b_m])
        r_p13 = calc_rmse(p13_y_final[b_m], tar_eval[b_m])
        d_vs_v2 = r_v2 - r_p13
        d_vs_v1 = r_v1 - r_p13
        pw = float(np.mean(p13_w_phys[b_m])) * 100.0
        
        disagreement_table.append({
            "band": b_name, "windows": n_w, "pct": pct_w,
            "v1_rmse": r_v1, "v2_rmse": r_v2, "p13_rmse": r_p13,
            "gain_vs_v2": d_vs_v2, "gain_vs_v1": d_vs_v1, "mean_physics_weight": pw
        })
        print(f"{b_name:<12} | {n_w:6d}   | {pct_w:5.1f}% | {r_v1:8.2f}   | {r_v2:8.2f}   | {r_p13:8.2f}   | {d_vs_v2:+8.2f}   | {d_vs_v1:+8.2f}   | {pw:10.1f}%")

    # --------------------------------------------------------------------------
    # 3. ZERO-CARB-LOGGED EXCURSION VALIDATION
    # --------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("3. EXCURSION VALIDATION: ZERO-CARB-LOGGED VS LOGGED EXCURSIONS")
    print("=" * 80)

    carbs_past_4h = np.sum(hupa_dyn_raw[eval_mask, -16:, 17], axis=-1)
    cgm_past_2h_rise = hupa_dyn_raw[eval_mask, -1, 0] - hupa_dyn_raw[eval_mask, -8, 0]
    unlogged_rise_m = (cgm_past_2h_rise > 30.0) & (carbs_past_4h == 0)
    logged_rise_m = (cgm_past_2h_rise > 30.0) & (carbs_past_4h > 0)

    excursion_table = []
    print(f"{'Condition':<35} | {'Windows':<8} | {'V1 RMSE':<10} | {'V2 RMSE':<10} | {'P13 RMSE':<10} | {'P13 Gain vs V2':<15} | {'P13 Phys Wt':<12}")
    print("-" * 115)

    for cond_name, cond_m in [("Zero-Carb-Logged Rises (>30 mg/dL in 2h)", unlogged_rise_m), ("Logged Carbs Rises (>30 mg/dL in 2h)", logged_rise_m)]:
        n_w = int(np.sum(cond_m))
        r1 = calc_rmse(preds_v1_hybrid[cond_m], tar_eval[cond_m])
        r2 = calc_rmse(v2_y_final[cond_m], tar_eval[cond_m])
        rp13 = calc_rmse(p13_y_final[cond_m], tar_eval[cond_m])
        gain = r2 - rp13
        pw = float(np.mean(p13_w_phys[cond_m])) * 100.0
        excursion_table.append({
            "condition": cond_name, "windows": n_w, "v1_rmse": r1, "v2_rmse": r2,
            "p13_rmse": rp13, "gain_vs_v2": gain, "mean_physics_weight": pw
        })
        print(f"{cond_name:<35} | {n_w:6d}   | {r1:8.2f}   | {r2:8.2f}   | {rp13:8.2f}   | {gain:+12.2f}    | {pw:10.1f}%")

    # --------------------------------------------------------------------------
    # 4. HORIZON-WISE ANALYSIS (V1 vs V2 vs Phase-13)
    # --------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("4. HORIZON-WISE RMSE AND GATING BEHAVIOR")
    print("=" * 80)

    horizons = [1, 2, 4, 8, 12, 16, 20]
    horizon_names = ["+15m", "+30m", "+1h", "+2h", "+3h", "+4h", "+5h"]
    horizon_table = []

    print(f"{'Horizon':<8} | {'Step':<5} | {'V1 RMSE':<10} | {'V2 RMSE':<10} | {'P13 RMSE':<10} | {'P13 vs V2':<10} | {'P13 vs V1':<10} | {'Mean Disagree':<14} | {'P13 Phys Wt':<12}")
    print("-" * 105)

    for h_idx, h_name in zip(horizons, horizon_names):
        r1 = calc_rmse(preds_v1_hybrid[:, h_idx-1], tar_eval[:, h_idx-1])
        r2 = calc_rmse(v2_y_final[:, h_idx-1], tar_eval[:, h_idx-1])
        rp13 = calc_rmse(p13_y_final[:, h_idx-1], tar_eval[:, h_idx-1])
        d_v2 = r2 - rp13
        d_v1 = r1 - rp13
        dis_h = float(np.mean(p13_disagreement[:, h_idx-1]))
        pw_h = float(np.mean(p13_w_phys[:, h_idx-1])) * 100.0

        horizon_table.append({
            "horizon": h_name, "step": h_idx, "v1_rmse": r1, "v2_rmse": r2, "p13_rmse": rp13,
            "gain_vs_v2": d_v2, "gain_vs_v1": d_v1, "disagreement": dis_h, "physics_weight": pw_h
        })
        print(f"{h_name:<8} | {h_idx:3d}   | {r1:8.3f}   | {r2:8.3f}   | {rp13:8.3f}   | {d_v2:+8.3f}   | {d_v1:+8.3f}   | {dis_h:12.2f}   | {pw_h:10.1f}%")

    # --------------------------------------------------------------------------
    # 5. UNCERTAINTY & CALIBRATION RETENTION AUDIT
    # --------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("5. UNCERTAINTY & CALIBRATION RETENTION AUDIT")
    print("=" * 80)

    unc_table = []
    print(f"{'Regime':<30} | {'V1 95% Cov':<12} | {'V2 95% Cov':<12} | {'P13 95% Cov':<12} | {'V1 Width':<12} | {'P13 Width':<12}")
    print("-" * 95)

    for reg_name, reg_m in [("All Windows", np.ones(N_eval, dtype=bool)), ("Low Volatility (<10)", low_vol_mask), ("Med Volatility (10-20)", med_vol_mask), ("High Volatility (>=20)", high_vol_mask)]:
        c1 = calc_coverage(tar_eval[reg_m], low95_v1[reg_m], upp95_v1[reg_m])
        c2 = calc_coverage(tar_eval[reg_m], v2_low95[reg_m], v2_upp95[reg_m])
        cp13 = calc_coverage(tar_eval[reg_m], p13_low95[reg_m], p13_upp95[reg_m])
        w1 = calc_mean_width(low95_v1[reg_m], upp95_v1[reg_m])
        wp13 = calc_mean_width(p13_low95[reg_m], p13_upp95[reg_m])

        unc_table.append({
            "regime": reg_name, "v1_cov": c1, "v2_cov": c2, "p13_cov": cp13,
            "v1_width": w1, "p13_width": wp13
        })
        print(f"{reg_name:<30} | {c1:10.2f}% | {c2:10.2f}% | {cp13:10.2f}% | {w1:10.1f} mg/dL | {wp13:10.1f} mg/dL")

    # --------------------------------------------------------------------------
    # 6. PARTICIPANT-LEVEL ANALYSIS (N=23) & HIGH-DISAGREEMENT OUTLIERS
    # --------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("6. PARTICIPANT-LEVEL ANALYSIS (N=23) & OUTLIER RECOVERY")
    print("=" * 80)

    part_records = []
    print(f"{'PID':<10} | {'Win':<6} | {'V1 RMSE':<10} | {'V2 RMSE':<10} | {'P13 RMSE':<10} | {'P13 vs V2':<10} | {'P13 vs V1':<10} | {'Mean Disagree':<14} | {'High-Dis %':<10}")
    print("-" * 105)

    for pid in unique_pids:
        pm = (eval_pids == pid)
        nw = int(np.sum(pm))
        r1 = calc_rmse(preds_v1_hybrid[pm], tar_eval[pm])
        r2 = calc_rmse(v2_y_final[pm], tar_eval[pm])
        rp13 = calc_rmse(p13_y_final[pm], tar_eval[pm])
        gain_v2 = r2 - rp13
        gain_v1 = r1 - rp13
        dis_p = float(np.mean(mean_d[pm]))
        high_dis_p = float(np.mean(mean_d[pm] >= 50.0)) * 100.0

        part_records.append({
            "pid": pid, "windows": nw, "v1_rmse": r1, "v2_rmse": r2, "p13_rmse": rp13,
            "gain_vs_v2": gain_v2, "gain_vs_v1": gain_v1, "disagreement": dis_p, "high_dis_pct": high_dis_p
        })
        print(f"{pid:<10} | {nw:4d}   | {r1:8.2f}   | {r2:8.2f}   | {rp13:8.2f}   | {gain_v2:+8.2f}   | {gain_v1:+8.2f}   | {dis_p:12.2f}   | {high_dis_p:8.1f}%")

    # --------------------------------------------------------------------------
    # 7. FACTOR-PRESERVATION AUDIT
    # --------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("7. FACTOR-PRESERVATION AUDIT: PRESERVING PHYSIOLOGICAL SIGNAL")
    print("=" * 80)

    disp_neural_vs_ode = float(np.mean(np.sqrt(np.mean((v2_y_neural - v2_y_ode)**2, axis=-1))))
    disp_p13_vs_neural = float(np.mean(np.sqrt(np.mean((p13_y_final - v2_y_neural)**2, axis=-1))))
    disp_p13_vs_ode = float(np.mean(np.sqrt(np.mean((p13_y_final - v2_y_ode)**2, axis=-1))))

    print(f"Physiological Displacement Dynamics:")
    print(f"  Neural vs ODE RMS Divergence:          {disp_neural_vs_ode:.2f} mg/dL")
    print(f"  Phase-13 Hybrid vs Pure Neural:       {disp_p13_vs_neural:.2f} mg/dL (Active Hybrid Physics Displacement)")
    print(f"  Phase-13 Hybrid vs Pure ODE:          {disp_p13_vs_ode:.2f} mg/dL")
    print(f"  Average Phase-13 Physics Weight:       {np.mean(p13_w_phys)*100:.2f}% (Maintained Active Contribution)")

    # --------------------------------------------------------------------------
    # SAVE METRICS TO JSON
    # --------------------------------------------------------------------------
    confirmation_metrics = {
        "frozen_parameters": params,
        "primary_comparison": primary_table,
        "disagreement_breakdown": disagreement_table,
        "excursion_breakdown": excursion_table,
        "horizon_breakdown": horizon_table,
        "uncertainty_retention": unc_table,
        "participant_level": part_records,
        "factor_preservation": {
            "disp_neural_vs_ode": disp_neural_vs_ode,
            "disp_p13_vs_neural": disp_p13_vs_neural,
            "disp_p13_vs_ode": disp_p13_vs_ode,
            "mean_physics_weight": float(np.mean(p13_w_phys)) * 100.0
        }
    }

    out_metrics_path = os.path.join(OUT_DIR, "partition_b_confirmation_metrics.json")
    with open(out_metrics_path, "w") as f:
        json.dump(confirmation_metrics, f, indent=2)
    print(f"\nSaved confirmation metrics to: {out_metrics_path}")

    print("\n" + "=" * 80)
    print("PHASE 13 SEALED PARTITION B CONFIRMATION COMPLETED.")
    print("=" * 80)

if __name__ == "__main__":
    run_confirmation()
