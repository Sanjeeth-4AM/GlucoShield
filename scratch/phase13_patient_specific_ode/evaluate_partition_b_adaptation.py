"""
GlucoShield Phase 13 — Sealed Partition B Confirmation of Patient-Specific ODE Adaptation
========================================================================================
Executes ONE-TIME unbiased evaluation of the frozen Patient-Specific Online ODE Adapter
combined with the frozen Phase-13 Disagreement-Attenuated Gate on sealed Partition B (10,785 windows).

GOVERNANCE:
  - Both Gate and Adaptation hyperparameters are strictly frozen from Calibration Partition.
  - Zero tuning or iterative adjustment on Partition B.
  - All outputs saved under scratch/phase13_patient_specific_ode/.
"""

import os
import sys
import json
import time
import dataclasses
import numpy as np
import torch
from scipy import stats

BASE_DIR = "D:/ML PROJECT"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from models.v2.context_encoder import PhysiologicalContextBatch
from models.v2.neural_forecaster import GlucoShieldNeuralForecasterV2
from models.v2.hybrid_forecaster_v2 import GlucoShieldHybridForecasterV2
from physiology.state import MetabolicState
from scratch.cgmacros_inference import load_frozen_artifacts
from scratch.phase13_disagreement_gate.disagreement_gate import DisagreementAttenuatedFusionGate
from scratch.phase13_patient_specific_ode.patient_ode_adapter import PatientOdeAdapter, PatientOdeConfig

DATA_DIR = os.path.join(BASE_DIR, "scratch", "phase11_sleep", "data")
OUT_DIR = os.path.join(BASE_DIR, "scratch", "phase13_patient_specific_ode")

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

def run_evaluation():
    print("=" * 80)
    print("PHASE 13: SEALED PARTITION B CONFIRMATION — PATIENT-SPECIFIC ODE ADAPTATION")
    print("=" * 80)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # Load frozen Phase 13 gate configuration
    p13_cfg_path = os.path.join(BASE_DIR, "scratch", "phase13_disagreement_gate", "frozen_gate_config.json")
    with open(p13_cfg_path) as f:
        frozen_gate_cfg = json.load(f)["selected_parameters"]
    gate = DisagreementAttenuatedFusionGate(
        ceiling=frozen_gate_cfg["ceiling"],
        d_mid=frozen_gate_cfg["d_mid"],
        tau=frozen_gate_cfg["tau"],
        w_high=frozen_gate_cfg["w_high"]
    )
    print(f"Loaded Frozen Phase 13 Gate: ceiling={gate.ceiling:.2f}, d_mid={gate.d_mid:.1f}, tau={gate.tau:.1f}, w_high={gate.w_high:.2f}")

    # Load frozen ODE adaptation configuration
    ode_cfg_path = os.path.join(OUT_DIR, "ode_adaptation_config.json")
    with open(ode_cfg_path) as f:
        frozen_ode_cfg = json.load(f)["parameters"]
    print(f"Loaded Frozen ODE Adaptation Config:")
    print(f"  adapt_si={frozen_ode_cfg['adapt_si']}, adapt_gb={frozen_ode_cfg['adapt_gb']}, eta_si={frozen_ode_cfg['eta_si']}, beta={frozen_ode_cfg['beta']}")

    adapter_config = PatientOdeConfig(
        adapt_si=frozen_ode_cfg["adapt_si"],
        adapt_gb=frozen_ode_cfg["adapt_gb"],
        eta_si=frozen_ode_cfg["eta_si"],
        eta_gb=frozen_ode_cfg["eta_gb"],
        beta=frozen_ode_cfg["beta"],
        clip_si=frozen_ode_cfg["clip_si"],
        clip_gb=frozen_ode_cfg["clip_gb"],
        deadband=frozen_ode_cfg["deadband"]
    )
    adapter = PatientOdeAdapter(adapter_config)

    # Load models
    feat_scaler, stat_scaler, _, _, _ = load_frozen_artifacts(device)
    ckpt = torch.load("models/v2/glucoshield_v2_best.pt", map_location=device)
    v2_neural = GlucoShieldNeuralForecasterV2().to(device)
    v2_hybrid = GlucoShieldHybridForecasterV2(v2_neural, freeze_neural=False, calib_iterations=5).to(device)
    v2_hybrid.load_state_dict(ckpt)
    v2_hybrid.eval()

    # Load Partition B Data
    hupa_raw = np.load(os.path.join(DATA_DIR, "hupa_windows_stride4.npz"))
    hupa_feat = np.load(os.path.join(DATA_DIR, "sleep_features.npz"))
    p_hupa = np.load(os.path.join(DATA_DIR, "sleep_ablation_predictions.npz"))

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

    # 1. Extract V2 Baseline Components (Neural, Frozen ODE, Gate, Uncertainty)
    print("\nExtracting baseline V2 components on Partition B...")
    batch_size = 256
    v2_y_final = []
    v2_y_neural = []
    v2_y_ode = []
    v2_alphas = []
    v2_residuals = []
    v2_z_context = []
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
            v2_z_context.append(out["z_context"].cpu().numpy())

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
    v2_z_context = np.concatenate(v2_z_context, axis=0)
    v2_low95 = np.concatenate(v2_low95, axis=0)
    v2_upp95 = np.concatenate(v2_upp95, axis=0)
    v2_low80 = np.concatenate(v2_low80, axis=0)
    v2_upp80 = np.concatenate(v2_upp80, axis=0)

    # Uncertainty width
    half_w95 = (v2_upp95 - v2_low95) / 2.0
    half_w80 = (v2_upp80 - v2_low80) / 2.0

    # Phase-13 Frozen Gate with Frozen ODE
    blend_p13 = gate.blend(y_neural=v2_y_neural, y_ode=v2_y_ode, alpha_raw=v2_alphas, residual=v2_residuals)
    p13_y_final = blend_p13["trajectory"]
    p13_alpha_eff = blend_p13["alpha_eff"]
    p13_w_phys = blend_p13["w_phys"]
    p13_low95 = p13_y_final - half_w95
    p13_upp95 = p13_y_final + half_w95
    p13_low80 = p13_y_final - half_w80
    p13_upp80 = p13_y_final + half_w80

    # 2. Execute Sequential Online Adaptation on Partition B
    print("\nExecuting Sequential Patient-Specific Online Adaptation on Partition B...")
    t0_adapt = time.time()
    dyn_eval_raw = hupa_dyn_raw[eval_mask]
    adapted_si, adapted_gb, audit_summary = adapter.process_stream(
        pids=eval_pids,
        dyn_raw=dyn_eval_raw,
        ode_proxy_predictions=v2_y_ode
    )
    dt_adapt = time.time() - t0_adapt
    print(f"Sequential parameter adaptation completed in {dt_adapt:.3f}s for {N_eval:,} windows.")

    # 3. Simulate Adapted ODE Forward and Re-Gate with Frozen Phase-13 Gate
    print("Simulating adapted ODE forward and evaluating Phase-13 + Adapted ODE...")
    adapted_y_ode = []
    adapted_alphas = []
    adapted_residuals = []

    with torch.no_grad():
        for b_start in range(0, N_eval, batch_size):
            b_end = min(b_start + batch_size, N_eval)
            b_idx = eval_idx[b_start:b_end]

            b_dyn_r = torch.tensor(hupa_dyn_raw[b_idx], dtype=torch.float32, device=device)
            b_stat_r = torch.tensor(hupa_stat_raw[b_idx], dtype=torch.float32, device=device)
            b_stat_s = torch.tensor(hupa_stat_scaled[b_idx], dtype=torch.float32, device=device)

            b_si = torch.tensor(adapted_si[b_start:b_end], dtype=torch.float32, device=device)
            b_gb = torch.tensor(adapted_gb[b_start:b_end], dtype=torch.float32, device=device)

            params_prior = v2_hybrid.prior_net(b_stat_r)
            params_ode = dataclasses.replace(params_prior, S_I=b_si, G_b=b_gb)

            state_t0 = MetabolicState.create_initial_state(
                initial_glucose=b_dyn_r[:, -1, 0],
                initial_iob=b_dyn_r[:, -1, 16],
                initial_cob=b_dyn_r[:, -1, 19],
                device=device
            )
            future_ins = torch.zeros(b_end - b_start, 20, device=device)
            future_carbs = torch.zeros(b_end - b_start, 20, device=device)

            b_y_ode, _ = v2_hybrid.integrator.forward_simulate(state_t0, future_ins, future_carbs, params_ode)

            b_ctx = PhysiologicalContextBatch(
                f_exercise=ctx_eval.f_exercise[b_start:b_end],
                m_exercise=ctx_eval.m_exercise[b_start:b_end],
                f_sleep=ctx_eval.f_sleep[b_start:b_end],
                m_sleep=ctx_eval.m_sleep[b_start:b_end],
                f_hormonal=ctx_eval.f_hormonal[b_start:b_end],
                m_hormonal=ctx_eval.m_hormonal[b_start:b_end],
                f_circadian=ctx_eval.f_circadian[b_start:b_end]
            )
            factor_masks = torch.cat([b_ctx.m_exercise, b_ctx.m_sleep, b_ctx.m_hormonal], dim=-1)
            b_y_neural = torch.tensor(v2_y_neural[b_start:b_end], dtype=torch.float32, device=device)
            z_ctx = torch.tensor(v2_z_context[b_start:b_end], dtype=torch.float32, device=device)

            phi_gate = v2_hybrid.fusion_gate.extract_gating_features(
                dynamic_seq_raw=b_dyn_r,
                y_neural=b_y_neural,
                y_ode=b_y_ode,
                z_context=z_ctx,
                future_ins=future_ins,
                future_carbs=future_carbs,
                factor_masks=factor_masks
            )
            b_alpha = v2_hybrid.fusion_gate(phi_gate)

            b_alpha_p13, _, _ = gate.compute_effective_weights(b_y_neural, b_y_ode, b_alpha)
            b_y_hybrid = b_alpha_p13 * b_y_neural + (1.0 - b_alpha_p13) * b_y_ode
            res_in = torch.cat([b_y_hybrid, z_ctx, b_stat_s], dim=-1)
            b_res = v2_hybrid.residual_head(res_in)

            adapted_y_ode.append(b_y_ode.cpu().numpy())
            adapted_alphas.append(b_alpha.cpu().numpy())
            adapted_residuals.append(b_res.cpu().numpy())

    adapted_y_ode = np.concatenate(adapted_y_ode, axis=0)
    adapted_alphas = np.concatenate(adapted_alphas, axis=0)
    adapted_residuals = np.concatenate(adapted_residuals, axis=0)

    # Blend with Phase-13 Disagreement Gate
    blend_adapt = gate.blend(
        y_neural=v2_y_neural,
        y_ode=adapted_y_ode,
        alpha_raw=adapted_alphas,
        residual=adapted_residuals
    )
    adapt_y_final = blend_adapt["trajectory"]
    adapt_alpha_eff = blend_adapt["alpha_eff"]
    adapt_w_phys = blend_adapt["w_phys"]
    adapt_disagreement = blend_adapt["disagreement"]

    # Uncertainty preservation (intervals centered on final point forecast)
    adapt_low95 = adapt_y_final - half_w95
    adapt_upp95 = adapt_y_final + half_w95
    adapt_low80 = adapt_y_final - half_w80
    adapt_upp80 = adapt_y_final + half_w80

    # --------------------------------------------------------------------------
    # PRIMARY BENCHMARK TABLE
    # --------------------------------------------------------------------------
    models_eval = [
        ("E0: Frozen V1 Baseline", preds_v1_hybrid, low95_v1, upp95_v1, low80_v1, upp80_v1, 0.9147, 0.0853),
        ("E1: Original V2 Hybrid", v2_y_final, v2_low95, v2_upp95, v2_low80, v2_upp80, float(np.mean(v2_alphas)), float(np.mean(1.0 - v2_alphas))),
        ("E2: Phase-13 Disagreement Gate", p13_y_final, p13_low95, p13_upp95, p13_low80, p13_upp80, float(np.mean(p13_alpha_eff)), float(np.mean(p13_w_phys))),
        ("E3: Phase-13 + Adaptive ODE", adapt_y_final, adapt_low95, adapt_upp95, adapt_low80, adapt_upp80, float(np.mean(adapt_alpha_eff)), float(np.mean(adapt_w_phys)))
    ]

    print("\n" + "=" * 95)
    print(f"{'Model / Architecture Condition':<35} | {'RMSE':<9} | {'MAE':<9} | {'Bias':<8} | {'Part RMSE':<10} | {'Short RMSE':<10} | {'H-Vol RMSE':<10} | {'95% Cov':<8} | {'80% Cov':<8} | {'Phys Wt':<8}")
    print("-" * 125)

    primary_results = {}
    for name, pred, l95, u95, l80, u80, a_eff, w_eff in models_eval:
        rmse_val = calc_rmse(pred, tar_eval)
        mae_val = calc_mae(pred, tar_eval)
        bias_val = calc_bias(pred, tar_eval)
        cov95_val = calc_coverage(tar_eval, l95, u95)
        cov80_val = calc_coverage(tar_eval, l80, u80)
        short_rmse = calc_rmse(pred[short_mask], tar_eval[short_mask])
        hvol_rmse = calc_rmse(pred[high_vol_mask], tar_eval[high_vol_mask])

        p_rmses = []
        for p in unique_pids:
            p_mask = (eval_pids == p)
            p_rmses.append(calc_rmse(pred[p_mask], tar_eval[p_mask]))
        part_rmse = float(np.mean(p_rmses))

        primary_results[name] = {
            "rmse": rmse_val, "mae": mae_val, "bias": bias_val,
            "part_rmse": part_rmse, "short_rmse": short_rmse, "hvol_rmse": hvol_rmse,
            "cov95": cov95_val, "cov80": cov80_val,
            "phys_weight": w_eff * 100.0,
            "mean_width_95": calc_mean_width(l95, u95),
            "mean_width_80": calc_mean_width(l80, u80)
        }
        print(f"{name:<35} | {rmse_val:<9.3f} | {mae_val:<9.3f} | {bias_val:<8.3f} | {part_rmse:<10.3f} | {short_rmse:<10.3f} | {hvol_rmse:<10.3f} | {cov95_val:<8.2f}% | {cov80_val:<8.2f}% | {w_eff*100:<8.2f}%")

    # --------------------------------------------------------------------------
    # HORIZON-WISE ANALYSIS
    # --------------------------------------------------------------------------
    print("\n" + "=" * 90)
    print("HORIZON-WISE ACCURACY BREAKDOWN (+15m to +5h)")
    print("=" * 90)
    steps_to_eval = [1, 2, 4, 8, 12, 16, 20]
    horizon_names = ["+15m", "+30m", "+1h", "+2h", "+3h", "+4h", "+5h"]
    horizon_results = {}

    print(f"{'Horizon':<8} | {'Step':<5} | {'V1 RMSE':<9} | {'V2 RMSE':<9} | {'Phase-13':<9} | {'Adaptive':<9} | {'Adapt vs P13':<12} | {'Adapt vs V1':<12}")
    print("-" * 90)

    for h_name, step in zip(horizon_names, steps_to_eval):
        h_idx = step - 1
        v1_h = calc_rmse(preds_v1_hybrid[:, h_idx], tar_eval[:, h_idx])
        v2_h = calc_rmse(v2_y_final[:, h_idx], tar_eval[:, h_idx])
        p13_h = calc_rmse(p13_y_final[:, h_idx], tar_eval[:, h_idx])
        adapt_h = calc_rmse(adapt_y_final[:, h_idx], tar_eval[:, h_idx])
        gain_vs_p13 = p13_h - adapt_h
        gain_vs_v1 = v1_h - adapt_h

        horizon_results[h_name] = {
            "step": step,
            "v1_rmse": v1_h, "v2_rmse": v2_h, "p13_rmse": p13_h, "adapt_rmse": adapt_h,
            "gain_vs_p13": gain_vs_p13, "gain_vs_v1": gain_vs_v1
        }
        print(f"{h_name:<8} | {step:<5} | {v1_h:<9.3f} | {v2_h:<9.3f} | {p13_h:<9.3f} | {adapt_h:<9.3f} | {gain_vs_p13:<+12.3f} | {gain_vs_v1:<+12.3f}")

    # --------------------------------------------------------------------------
    # DISAGREEMENT BANDS AUDIT
    # --------------------------------------------------------------------------
    print("\n" + "=" * 90)
    print("DISAGREEMENT BANDS AUDIT (Neural vs Adapted ODE)")
    print("=" * 90)
    mean_dis_p13 = np.mean(np.abs(v2_y_neural - v2_y_ode), axis=-1)
    mean_dis_adapt = np.mean(np.abs(v2_y_neural - adapted_y_ode), axis=-1)

    bands = [
        ("<10 mg/dL", (mean_dis_p13 < 10.0)),
        ("10-20 mg/dL", (mean_dis_p13 >= 10.0) & (mean_dis_p13 < 20.0)),
        ("20-30 mg/dL", (mean_dis_p13 >= 20.0) & (mean_dis_p13 < 30.0)),
        ("30-50 mg/dL", (mean_dis_p13 >= 30.0) & (mean_dis_p13 < 50.0)),
        (">50 mg/dL", (mean_dis_p13 >= 50.0))
    ]

    print(f"{'Band':<12} | {'Windows':<8} | {'V1 RMSE':<9} | {'V2 RMSE':<9} | {'P13 RMSE':<9} | {'Adapt RMSE':<10} | {'ODE Base':<9} | {'ODE Adapt':<9} | {'Phys Wt':<8}")
    print("-" * 105)

    band_results = {}
    for b_name, b_mask in bands:
        n_w = int(np.sum(b_mask))
        v1_r = calc_rmse(preds_v1_hybrid[b_mask], tar_eval[b_mask])
        v2_r = calc_rmse(v2_y_final[b_mask], tar_eval[b_mask])
        p13_r = calc_rmse(p13_y_final[b_mask], tar_eval[b_mask])
        ad_r = calc_rmse(adapt_y_final[b_mask], tar_eval[b_mask])
        ode_base_r = calc_rmse(v2_y_ode[b_mask], tar_eval[b_mask])
        ode_ad_r = calc_rmse(adapted_y_ode[b_mask], tar_eval[b_mask])
        pw = float(np.mean(adapt_w_phys[b_mask])) * 100.0

        band_results[b_name] = {
            "windows": n_w, "v1_rmse": v1_r, "v2_rmse": v2_r, "p13_rmse": p13_r, "adapt_rmse": ad_r,
            "ode_base_rmse": ode_base_r, "ode_adapt_rmse": ode_ad_r, "phys_weight": pw
        }
        print(f"{b_name:<12} | {n_w:<8} | {v1_r:<9.2f} | {v2_r:<9.2f} | {p13_r:<9.2f} | {ad_r:<10.2f} | {ode_base_r:<9.2f} | {ode_ad_r:<9.2f} | {pw:<8.2f}%")

    # --------------------------------------------------------------------------
    # UNLOGGED EXCURSIONS TEST (Section 12)
    # --------------------------------------------------------------------------
    print("\n" + "=" * 90)
    print("UNLOGGED EXCURSIONS TEST (Zero-Carb-Logged Rises > 30 mg/dL in 2 Hours)")
    print("=" * 90)
    cgm_end = dyn_eval_raw[:, -1, 0]
    cgm_2h_ago = dyn_eval_raw[:, -9, 0]
    cgm_rise_2h = cgm_end - cgm_2h_ago
    carbs_logged_2h = np.sum(dyn_eval_raw[:, -8:, 17], axis=-1)

    unlogged_rise_mask = (cgm_rise_2h > 30.0) & (carbs_logged_2h <= 0.1)
    logged_rise_mask = (cgm_rise_2h > 30.0) & (carbs_logged_2h > 0.1)

    print(f"Unlogged rises windows: {np.sum(unlogged_rise_mask):,} | Logged rises windows: {np.sum(logged_rise_mask):,}")
    unlogged_eval = {
        "Unlogged Rises": unlogged_rise_mask,
        "Logged Rises": logged_rise_mask
    }
    unlogged_results = {}

    print(f"{'Condition':<16} | {'Windows':<8} | {'V1 RMSE':<9} | {'V2 RMSE':<9} | {'P13 RMSE':<9} | {'Adapt RMSE':<10} | {'ODE Base':<9} | {'ODE Adapt':<9} | {'Disag Base':<10} | {'Disag Adapt':<11}")
    print("-" * 115)

    for cond_name, c_mask in unlogged_eval.items():
        n_c = int(np.sum(c_mask))
        v1_r = calc_rmse(preds_v1_hybrid[c_mask], tar_eval[c_mask])
        v2_r = calc_rmse(v2_y_final[c_mask], tar_eval[c_mask])
        p13_r = calc_rmse(p13_y_final[c_mask], tar_eval[c_mask])
        ad_r = calc_rmse(adapt_y_final[c_mask], tar_eval[c_mask])
        ode_b = calc_rmse(v2_y_ode[c_mask], tar_eval[c_mask])
        ode_ad = calc_rmse(adapted_y_ode[c_mask], tar_eval[c_mask])
        dis_b = float(np.mean(np.abs(v2_y_neural[c_mask] - v2_y_ode[c_mask])))
        dis_ad = float(np.mean(np.abs(v2_y_neural[c_mask] - adapted_y_ode[c_mask])))

        unlogged_results[cond_name] = {
            "windows": n_c, "v1_rmse": v1_r, "v2_rmse": v2_r, "p13_rmse": p13_r, "adapt_rmse": ad_r,
            "ode_base_rmse": ode_b, "ode_adapt_rmse": ode_ad, "disag_base": dis_b, "disag_adapt": dis_ad
        }
        print(f"{cond_name:<16} | {n_c:<8} | {v1_r:<9.2f} | {v2_r:<9.2f} | {p13_r:<9.2f} | {ad_r:<10.2f} | {ode_b:<9.2f} | {ode_ad:<9.2f} | {dis_b:<10.2f} | {dis_ad:<11.2f}")

    # --------------------------------------------------------------------------
    # PARTICIPANT-LEVEL & OUTLIER AUDIT (Section 10)
    # --------------------------------------------------------------------------
    print("\n" + "=" * 90)
    print("PARTICIPANT-LEVEL AUDIT (All N=23 Participants)")
    print("=" * 90)
    participant_results = {}
    print(f"{'PID':<11} | {'Windows':<8} | {'V1 RMSE':<8} | {'P13 RMSE':<8} | {'Adapt RMSE':<10} | {'Gain vs P13':<12} | {'SI Median':<10} | {'SI IQR':<8} | {'Adapt %':<8}")
    print("-" * 95)

    for p in unique_pids:
        p_mask = (eval_pids == p)
        n_p = int(np.sum(p_mask))
        v1_p = calc_rmse(preds_v1_hybrid[p_mask], tar_eval[p_mask])
        p13_p = calc_rmse(p13_y_final[p_mask], tar_eval[p_mask])
        ad_p = calc_rmse(adapt_y_final[p_mask], tar_eval[p_mask])
        gain_p13 = p13_p - ad_p

        p_si = adapted_si[p_mask]
        si_med = float(np.median(p_si))
        si_iqr = float(np.percentile(p_si, 75) - np.percentile(p_si, 25))
        audit_p = audit_summary.get(p, {})

        participant_results[p] = {
            "windows": n_p,
            "v1_rmse": v1_p, "p13_rmse": p13_p, "adapt_rmse": ad_p, "gain_vs_p13": gain_p13,
            "si_median": si_med, "si_iqr": si_iqr,
            "adapt_pct": audit_p.get("adapt_pct", 0.0),
            "clip_pct": audit_p.get("clip_pct", 0.0),
            "max_abs_si_change": audit_p.get("max_abs_si_change", 0.0),
            "max_abs_gb_change": audit_p.get("max_abs_gb_change", 0.0)
        }
        print(f"{p:<11} | {n_p:<8} | {v1_p:<8.2f} | {p13_p:<8.2f} | {ad_p:<10.2f} | {gain_p13:<+12.3f} | {si_med:<10.6f} | {si_iqr:<8.6f} | {audit_p.get('adapt_pct', 0.0):<8.1f}%")

    # --------------------------------------------------------------------------
    # SAVE ALL CONFIRMATION METRICS
    # --------------------------------------------------------------------------
    final_output = {
        "status": "PARTITION_B_FINAL_CONFIRMATION_COMPLETE",
        "primary_results": primary_results,
        "horizon_results": horizon_results,
        "band_results": band_results,
        "unlogged_results": unlogged_results,
        "participant_results": participant_results,
        "audit_summary": audit_summary
    }

    metrics_save_path = os.path.join(OUT_DIR, "partition_b_adaptation_metrics.json")
    with open(metrics_save_path, "w") as f:
        json.dump(final_output, f, indent=2)
    print(f"\nAll confirmation metrics successfully saved to {metrics_save_path}")

if __name__ == "__main__":
    run_evaluation()
