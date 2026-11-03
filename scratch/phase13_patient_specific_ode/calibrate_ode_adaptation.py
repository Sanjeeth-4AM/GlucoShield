"""
Calibration script for Patient-Specific Online ODE Adaptation.
Evaluates a disciplined grid on HUPA-UCM Calibration Partition (11,497 windows).
"""
import os
import sys
import time
import json
import torch
import numpy as np
import dataclasses

BASE_DIR = "D:/ML PROJECT"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from models.v2.neural_forecaster import GlucoShieldNeuralForecasterV2
from models.v2.hybrid_forecaster_v2 import GlucoShieldHybridForecasterV2
from models.v2.context_encoder import PhysiologicalContextBatch
from physiology.state import MetabolicState
from scratch.phase13_disagreement_gate.disagreement_gate import DisagreementAttenuatedFusionGate
from scratch.cgmacros_inference import load_frozen_artifacts

def run_grid():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    out_dir = os.path.join(BASE_DIR, "scratch", "phase13_patient_specific_ode")
    os.makedirs(out_dir, exist_ok=True)

    # Load frozen Phase 13 gate config
    with open("scratch/phase13_disagreement_gate/frozen_gate_config.json") as f:
        cfg = json.load(f)["selected_parameters"]
    gate = DisagreementAttenuatedFusionGate(ceiling=cfg["ceiling"], d_mid=cfg["d_mid"], tau=cfg["tau"], w_high=cfg["w_high"])

    feat_scaler, stat_scaler, _, _, _ = load_frozen_artifacts(device)
    ckpt = torch.load("models/v2/glucoshield_v2_best.pt", map_location=device)
    v2_neural = GlucoShieldNeuralForecasterV2().to(device)
    v2_hybrid = GlucoShieldHybridForecasterV2(v2_neural, freeze_neural=False, calib_iterations=5).to(device)
    v2_hybrid.load_state_dict(ckpt)
    v2_hybrid.eval()

    data_dir = os.path.join(BASE_DIR, "scratch", "phase11_sleep", "data")
    hupa_raw = np.load(os.path.join(data_dir, "hupa_windows_stride4.npz"))
    hupa_feat = np.load(os.path.join(data_dir, "sleep_features.npz"))

    cal_mask = (hupa_feat["partitions"] == "calibration") & hupa_feat["sleep_aligned"]
    cal_idx = np.where(cal_mask)[0]
    N_cal = len(cal_idx)

    pids = hupa_feat["pids"][cal_mask]
    dyn_raw = hupa_raw["dynamic_raw"][cal_mask]
    stat_raw = hupa_raw["static_raw"][cal_mask]
    targets = hupa_raw["targets"][cal_mask]

    dur = hupa_feat["dur_hours"][cal_mask]
    eff = hupa_feat["efficiency"][cal_mask]
    deep = hupa_feat["deep_pct"][cal_mask]
    debt = hupa_feat["debt_hours"][cal_mask]
    tau_w = hupa_feat["tau_wake_hours"][cal_mask]

    N_hupa, T, D = hupa_raw["dynamic_raw"].shape
    dyn_scaled = feat_scaler.transform(dyn_raw.reshape(-1, D)).reshape(N_cal, T, D).astype(np.float32)
    stat_scaled = stat_scaler.transform(stat_raw).astype(np.float32)

    psi_decay = np.exp(-np.log(2.0) * np.maximum(0.0, tau_w) / 6.0).astype(np.float32)
    f_sleep = np.stack([dur / 8.0, eff, deep, debt / 4.0, psi_decay], axis=-1).astype(np.float32)
    sin_24 = dyn_raw[:, -1, 10]
    cos_24 = dyn_raw[:, -1, 11]
    f_circ = np.stack([sin_24, cos_24, 2.0*sin_24*cos_24, cos_24**2 - sin_24**2], axis=-1).astype(np.float32)

    ctx_cal = PhysiologicalContextBatch(
        f_exercise=torch.zeros(N_cal, 4, device=device),
        m_exercise=torch.zeros(N_cal, 1, device=device),
        f_sleep=torch.tensor(f_sleep, dtype=torch.float32, device=device),
        m_sleep=torch.ones(N_cal, 1, device=device),
        f_hormonal=torch.zeros(N_cal, 3, device=device),
        m_hormonal=torch.zeros(N_cal, 1, device=device),
        f_circadian=torch.tensor(f_circ, dtype=torch.float32, device=device)
    )

    # 1. Precompute neural predictions and baseline ODE predictions
    print(f"Precomputing neural and baseline components on {N_cal:,} calibration windows...")
    batch_size = 256
    v2_y_neural = []
    v2_y_ode_base = []
    v2_alphas_base = []
    v2_residuals_base = []
    v2_z_context = []
    v2_low95 = []
    v2_upp95 = []
    v2_low80 = []
    v2_upp80 = []

    with torch.no_grad():
        for b_start in range(0, N_cal, batch_size):
            b_end = min(b_start + batch_size, N_cal)
            b_dyn_s = torch.tensor(dyn_scaled[b_start:b_end], dtype=torch.float32, device=device)
            b_dyn_r = torch.tensor(dyn_raw[b_start:b_end], dtype=torch.float32, device=device)
            b_stat_s = torch.tensor(stat_scaled[b_start:b_end], dtype=torch.float32, device=device)
            b_stat_r = torch.tensor(stat_raw[b_start:b_end], dtype=torch.float32, device=device)
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
            v2_y_ode_base.append(out["y_ode"].cpu().numpy())
            v2_alphas_base.append(out["alpha"].cpu().numpy())
            v2_residuals_base.append(out["residual"].cpu().numpy())
            v2_z_context.append(out["z_context"].cpu().numpy())

            p_int = out["prediction_interval"]
            v2_low95.append(p_int.lower_95.cpu().numpy())
            v2_upp95.append(p_int.upper_95.cpu().numpy())
            v2_low80.append(p_int.lower_80.cpu().numpy())
            v2_upp80.append(p_int.upper_80.cpu().numpy())

    v2_y_neural = np.concatenate(v2_y_neural, axis=0)
    v2_y_ode_base = np.concatenate(v2_y_ode_base, axis=0)
    v2_alphas_base = np.concatenate(v2_alphas_base, axis=0)
    v2_residuals_base = np.concatenate(v2_residuals_base, axis=0)
    v2_z_context = np.concatenate(v2_z_context, axis=0)
    v2_low95 = np.concatenate(v2_low95, axis=0)
    v2_upp95 = np.concatenate(v2_upp95, axis=0)
    v2_low80 = np.concatenate(v2_low80, axis=0)
    v2_upp80 = np.concatenate(v2_upp80, axis=0)

    # Uncertainty width for centering
    half_w95 = (v2_upp95 - v2_low95) / 2.0
    half_w80 = (v2_upp80 - v2_low80) / 2.0

    # Baseline Phase-13 metrics
    blend_base = gate.blend(v2_y_neural, v2_y_ode_base, v2_alphas_base, v2_residuals_base)
    y_final_base = blend_base["trajectory"]
    rmse_base = float(np.sqrt(np.mean((y_final_base - targets) ** 2)))
    mae_base = float(np.mean(np.abs(y_final_base - targets)))
    ode_rmse_base = float(np.sqrt(np.mean((v2_y_ode_base - targets) ** 2)))
    cov95_base = float(np.mean((targets >= (y_final_base - half_w95)) & (targets <= (y_final_base + half_w95)))) * 100.0
    cov80_base = float(np.mean((targets >= (y_final_base - half_w80)) & (targets <= (y_final_base + half_w80)))) * 100.0

    print(f"\n=======================================================")
    print(f"FROZEN PHASE-13 BASELINE (E0) ON CALIBRATION PARTITION:")
    print(f"  Hybrid RMSE: {rmse_base:.3f} mg/dL | MAE: {mae_base:.3f} mg/dL")
    print(f"  ODE RMSE:    {ode_rmse_base:.3f} mg/dL")
    print(f"  95% Cov:     {cov95_base:.2f}% | 80% Cov: {cov80_base:.2f}%")
    print(f"=======================================================\n")

    # Evaluation function for a given configuration
    def evaluate_config(adapt_gb, adapt_si, eta_gb, eta_si, beta, clip_gb, clip_si, deadband, fasting_gb_only=False):
        base_si = 0.002869
        base_gb = 141.79

        adapted_si = np.full(N_cal, base_si, dtype=np.float32)
        adapted_gb = np.full(N_cal, base_gb, dtype=np.float32)

        curr_si = base_si
        curr_gb = base_gb
        prev_pid = None
        prev_ode = None

        adapt_count = 0
        clip_count = 0

        for i in range(N_cal):
            pid = pids[i]
            if pid != prev_pid:
                curr_si = base_si
                curr_gb = base_gb
                prev_pid = pid
                prev_ode = None

            if prev_ode is not None:
                cgm_obs_4 = dyn_raw[i, -4:, 0]
                res_innov = float(np.mean(cgm_obs_4 - prev_ode[:4]))

                if np.abs(res_innov) > deadband:
                    effective_res = res_innov - np.sign(res_innov) * deadband

                    # Gb update
                    if adapt_gb:
                        eligible_gb = True
                        if fasting_gb_only:
                            # Strict fasting check: no carbs in past 4h (16 steps), IOB < 0.2
                            carbs_hist = np.sum(dyn_raw[i, -16:, 17])
                            iob_curr = dyn_raw[i, -1, 16]
                            if carbs_hist > 0.5 or iob_curr > 0.2:
                                eligible_gb = False

                        if eligible_gb:
                            adapt_count += 1
                            delta_gb = eta_gb * effective_res
                            if np.abs(delta_gb) > clip_gb:
                                clip_count += 1
                                delta_gb = np.clip(delta_gb, -clip_gb, clip_gb)
                            cand_gb = np.clip(curr_gb + delta_gb, 70.0, 220.0)
                            curr_gb = beta * curr_gb + (1.0 - beta) * cand_gb

                    # SI update
                    if adapt_si:
                        iob_recent = np.mean(dyn_raw[i, -4:, 16])
                        ins_recent = np.sum(dyn_raw[i, -4:, 15])
                        if iob_recent > 0.2 or ins_recent > 0.1:
                            adapt_count += 1
                            ins_scale = np.clip(iob_recent / 1.0, 0.2, 1.0)
                            delta_log_si = -eta_si * (effective_res / 50.0) * ins_scale
                            if np.abs(delta_log_si) > clip_si:
                                clip_count += 1
                                delta_log_si = np.clip(delta_log_si, -clip_si, clip_si)
                            cand_si = np.clip(curr_si * np.exp(delta_log_si), 1.0e-5, 5.0e-3)
                            curr_si = beta * curr_si + (1.0 - beta) * cand_si

            adapted_si[i] = curr_si
            adapted_gb[i] = curr_gb
            prev_ode = v2_y_ode_base[i]

        # Batched simulation with adapted parameters
        adapted_y_ode = []
        adapted_alphas = []
        adapted_residuals = []

        with torch.no_grad():
            for b_start in range(0, N_cal, batch_size):
                b_end = min(b_start + batch_size, N_cal)
                b_dyn_r = torch.tensor(dyn_raw[b_start:b_end], dtype=torch.float32, device=device)
                b_stat_r = torch.tensor(stat_raw[b_start:b_end], dtype=torch.float32, device=device)
                b_stat_s = torch.tensor(stat_scaled[b_start:b_end], dtype=torch.float32, device=device)

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

                # Gate features
                b_ctx = PhysiologicalContextBatch(
                    f_exercise=ctx_cal.f_exercise[b_start:b_end],
                    m_exercise=ctx_cal.m_exercise[b_start:b_end],
                    f_sleep=ctx_cal.f_sleep[b_start:b_end],
                    m_sleep=ctx_cal.m_sleep[b_start:b_end],
                    f_hormonal=ctx_cal.f_hormonal[b_start:b_end],
                    m_hormonal=ctx_cal.m_hormonal[b_start:b_end],
                    f_circadian=ctx_cal.f_circadian[b_start:b_end]
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

        blend_adapt = gate.blend(v2_y_neural, adapted_y_ode, adapted_alphas, adapted_residuals)
        y_final = blend_adapt["trajectory"]

        rmse = float(np.sqrt(np.mean((y_final - targets) ** 2)))
        mae = float(np.mean(np.abs(y_final - targets)))
        ode_rmse = float(np.sqrt(np.mean((adapted_y_ode - targets) ** 2)))
        mean_disag = float(np.mean(np.abs(v2_y_neural - adapted_y_ode)))
        cov95 = float(np.mean((targets >= (y_final - half_w95)) & (targets <= (y_final + half_w95)))) * 100.0
        cov80 = float(np.mean((targets >= (y_final - half_w80)) & (targets <= (y_final + half_w80)))) * 100.0

        return {
            "adapt_gb": adapt_gb,
            "adapt_si": adapt_si,
            "eta_gb": eta_gb,
            "eta_si": eta_si,
            "beta": beta,
            "clip_gb": clip_gb,
            "clip_si": clip_si,
            "deadband": deadband,
            "fasting_gb_only": fasting_gb_only,
            "rmse": rmse,
            "mae": mae,
            "ode_rmse": ode_rmse,
            "mean_disag": mean_disag,
            "cov95": cov95,
            "cov80": cov80,
            "rmse_gain": rmse_base - rmse,
            "ode_gain": ode_rmse_base - ode_rmse,
            "si_mean": float(np.mean(adapted_si)),
            "si_min": float(np.min(adapted_si)),
            "si_max": float(np.max(adapted_si)),
            "gb_mean": float(np.mean(adapted_gb)),
            "gb_min": float(np.min(adapted_gb)),
            "gb_max": float(np.max(adapted_gb)),
            "adapt_count": int(adapt_count),
            "clip_count": int(clip_count)
        }

    # Predefined grid search
    print("Running predefined calibration grid search...")
    grid_configs = []

    # 1. Ablations
    # E1: Adaptive SI only (varying eta_si and beta)
    for eta_si in [0.01, 0.02, 0.04]:
        for beta in [0.70, 0.80, 0.90]:
            grid_configs.append((False, True, 0.0, eta_si, beta, 5.0, 0.10, 3.0, False, f"E1_SI_eta{eta_si}_b{beta}"))

    # 2. Fasting-only Gb adaptation
    for eta_gb in [0.01, 0.02, 0.05]:
        grid_configs.append((True, False, eta_gb, 0.0, 0.80, 2.0, 0.10, 5.0, True, f"E2_fasting_Gb_eta{eta_gb}"))

    # 3. Combined SI + Fasting Gb
    for eta_si in [0.01, 0.02]:
        for eta_gb in [0.01, 0.02]:
            grid_configs.append((True, True, eta_gb, eta_si, 0.80, 2.0, 0.10, 3.0, True, f"E3_SI{eta_si}_fastingGb{eta_gb}"))

    results = []
    print(f"Total configurations to evaluate: {len(grid_configs)}")
    print(f"{'Config Name':<25} | {'RMSE':<8} | {'Gain':<8} | {'ODE RMSE':<9} | {'ODE Gain':<9} | {'95% Cov':<8} | {'SI Mean':<10} | {'Gb Mean':<8}")
    print("-" * 105)

    for adapt_gb, adapt_si, eta_gb, eta_si, beta, clip_gb, clip_si, deadband, fasting_gb, name in grid_configs:
        t0 = time.time()
        res = evaluate_config(adapt_gb, adapt_si, eta_gb, eta_si, beta, clip_gb, clip_si, deadband, fasting_gb_only=fasting_gb)
        res["name"] = name
        results.append(res)
        dt = time.time() - t0
        print(f"{name:<25} | {res['rmse']:<8.3f} | {res['rmse_gain']:<+8.3f} | {res['ode_rmse']:<9.3f} | {res['ode_gain']:<+9.3f} | {res['cov95']:<8.2f}% | {res['si_mean']:<10.6f} | {res['gb_mean']:<8.1f} ({dt:.1f}s)")

    # Sort results by RMSE gain
    results.sort(key=lambda x: x["rmse_gain"], reverse=True)

    # Save all grid results
    grid_res_path = os.path.join(out_dir, "calibration_grid_results.json")
    with open(grid_res_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved all calibration results to {grid_res_path}")

    # Top winner
    best = results[0]
    print(f"\n=======================================================")
    print(f"TOP CALIBRATION CONFIGURATION: {best['name']}")
    print(f"  Hybrid RMSE: {best['rmse']:.3f} mg/dL (Gain: {best['rmse_gain']:+.3f} mg/dL)")
    print(f"  ODE RMSE:    {best['ode_rmse']:.3f} mg/dL (ODE Gain: {best['ode_gain']:+.3f} mg/dL)")
    print(f"  95% Cov:     {best['cov95']:.2f}% | 80% Cov: {best['cov80']:.2f}%")
    print(f"  Parameters:  SI={best['adapt_si']} (eta={best['eta_si']}), Gb={best['adapt_gb']} (eta={best['eta_gb']}, fasting={best['fasting_gb_only']})")
    print(f"=======================================================")

    # Freeze winning configuration
    config_frozen = {
        "status": "FROZEN_CALIBRATION_SELECTED",
        "selected_configuration": best["name"],
        "parameters": {
            "adapt_si": best["adapt_si"],
            "adapt_gb": best["adapt_gb"],
            "eta_si": best["eta_si"],
            "eta_gb": best["eta_gb"],
            "beta": best["beta"],
            "clip_si": best["clip_si"],
            "clip_gb": best["clip_gb"],
            "deadband": best["deadband"],
            "fasting_gb_only": best["fasting_gb_only"]
        },
        "calibration_metrics": {
            "rmse": best["rmse"],
            "rmse_gain": best["rmse_gain"],
            "mae": best["mae"],
            "ode_rmse": best["ode_rmse"],
            "ode_gain": best["ode_gain"],
            "cov95": best["cov95"],
            "cov80": best["cov80"],
            "mean_disagreement": best["mean_disag"]
        }
    }
    frozen_cfg_path = os.path.join(out_dir, "ode_adaptation_config.json")
    with open(frozen_cfg_path, "w") as f:
        json.dump(config_frozen, f, indent=2)
    print(f"Saved frozen configuration to {frozen_cfg_path}")

if __name__ == "__main__":
    run_grid()
