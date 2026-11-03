"""
Test and compare online adaptation methods on Calibration partition.
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

def evaluate_adaptation_on_calib():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

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

    # 1. Extract baseline neural and unadapted ODE predictions
    print(f"Extracting baseline components on {N_cal:,} calibration windows...")
    batch_size = 256
    v2_y_neural = []
    v2_y_ode_base = []
    v2_alphas_base = []
    v2_residuals_base = []

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

    v2_y_neural = np.concatenate(v2_y_neural, axis=0)
    v2_y_ode_base = np.concatenate(v2_y_ode_base, axis=0)
    v2_alphas_base = np.concatenate(v2_alphas_base, axis=0)
    v2_residuals_base = np.concatenate(v2_residuals_base, axis=0)

    # Baseline Phase-13 metrics
    blend_base = gate.blend(v2_y_neural, v2_y_ode_base, v2_alphas_base, v2_residuals_base)
    y_final_base = blend_base["trajectory"]
    rmse_base = float(np.sqrt(np.mean((y_final_base - targets) ** 2)))
    mae_base = float(np.mean(np.abs(y_final_base - targets)))
    ode_rmse_base = float(np.sqrt(np.mean((v2_y_ode_base - targets) ** 2)))
    print(f"\n--- Baseline E0 (Phase 13 Frozen Gate, Frozen ODE) ---")
    print(f"  Hybrid RMSE: {rmse_base:.3f} mg/dL | MAE: {mae_base:.3f} mg/dL | ODE RMSE: {ode_rmse_base:.3f} mg/dL")

    # Helper function to run sequential adaptation and evaluate
    def run_adaptation_experiment(adapt_gb, adapt_si, eta_gb=0.05, eta_si=0.02, beta=0.8, clip_gb=5.0, clip_si=0.1, deadband=3.0, name="Exp"):
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

        # Sequential pass across the calibration stream
        for i in range(N_cal):
            pid = pids[i]
            if pid != prev_pid:
                curr_si = base_si
                curr_gb = base_gb
                prev_pid = pid
                prev_ode = None

            if prev_ode is not None:
                # 4-step innovation residual
                cgm_obs_4 = dyn_raw[i, -4:, 0]
                res_innov = np.mean(cgm_obs_4 - prev_ode[:4])

                if np.abs(res_innov) > deadband:
                    adapt_count += 1
                    effective_res = res_innov - np.sign(res_innov) * deadband

                    # Gb adaptation
                    if adapt_gb:
                        delta_gb = eta_gb * effective_res
                        if np.abs(delta_gb) > clip_gb:
                            clip_count += 1
                            delta_gb = np.clip(delta_gb, -clip_gb, clip_gb)
                        cand_gb = np.clip(curr_gb + delta_gb, 70.0, 220.0)
                        curr_gb = beta * curr_gb + (1.0 - beta) * cand_gb

                    # SI adaptation
                    if adapt_si:
                        iob_recent = np.mean(dyn_raw[i, -4:, 16])
                        ins_recent = np.sum(dyn_raw[i, -4:, 15])
                        if iob_recent > 0.2 or ins_recent > 0.1:
                            ins_scale = np.clip(iob_recent / 1.0, 0.2, 1.0)
                            delta_log_si = -eta_si * (effective_res / 50.0) * ins_scale
                            if np.abs(delta_log_si) > clip_si:
                                clip_count += 1
                                delta_log_si = np.clip(delta_log_si, -clip_si, clip_si)
                            cand_si = np.clip(curr_si * np.exp(delta_log_si), 1.0e-5, 5.0e-3)
                            curr_si = beta * curr_si + (1.0 - beta) * cand_si

            adapted_si[i] = curr_si
            adapted_gb[i] = curr_gb
            # For next window's innovation, use baseline ODE proxy or adapted ODE
            prev_ode = v2_y_ode_base[i]

        # Now simulate adapted ODE on CUDA in batches
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
                # Compute neural context
                neural_out = v2_neural(
                    torch.tensor(dyn_scaled[b_start:b_end], dtype=torch.float32, device=device),
                    b_stat_s,
                    context_batch=b_ctx
                )
                z_ctx = neural_out["z_context"]

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

                # Residual head
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

        # Blend with Phase-13 gate
        blend_adapt = gate.blend(v2_y_neural, adapted_y_ode, adapted_alphas, adapted_residuals)
        y_final_adapt = blend_adapt["trajectory"]

        rmse = float(np.sqrt(np.mean((y_final_adapt - targets) ** 2)))
        mae = float(np.mean(np.abs(y_final_adapt - targets)))
        ode_rmse = float(np.sqrt(np.mean((adapted_y_ode - targets) ** 2)))
        mean_disag = float(np.mean(np.abs(v2_y_neural - adapted_y_ode)))

        print(f"\n--- {name} ---")
        print(f"  Hybrid RMSE: {rmse:.3f} mg/dL (Gain vs Base: {rmse_base - rmse:+.3f} mg/dL)")
        print(f"  Hybrid MAE:  {mae:.3f} mg/dL (Gain vs Base: {mae_base - mae:+.3f} mg/dL)")
        print(f"  ODE RMSE:    {ode_rmse:.3f} mg/dL (ODE Gain vs Base: {ode_rmse_base - ode_rmse:+.3f} mg/dL)")
        print(f"  Mean Disag:  {mean_disag:.2f} mg/dL (Base Disag: {np.mean(np.abs(v2_y_neural - v2_y_ode_base)):.2f} mg/dL)")
        print(f"  Adapted Gb:  mean={np.mean(adapted_gb):.1f} [{np.min(adapted_gb):.1f}, {np.max(adapted_gb):.1f}]")
        print(f"  Adapted SI:  mean={np.mean(adapted_si):.6f} [{np.min(adapted_si):.6f}, {np.max(adapted_si):.6f}]")
        return rmse, mae, ode_rmse

    # Run the 3 ablations on Calibration Partition:
    print("\nRunning Ablations E1, E2, E3 on Calibration Partition...")
    run_adaptation_experiment(adapt_gb=False, adapt_si=True, name="E1: Adaptive S_I Only")
    run_adaptation_experiment(adapt_gb=True, adapt_si=False, name="E2: Adaptive G_b Only")
    run_adaptation_experiment(adapt_gb=True, adapt_si=True, name="E3: Adaptive S_I + G_b")

if __name__ == "__main__":
    evaluate_adaptation_on_calib()
