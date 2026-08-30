"""
GlucoShield Phase 6 — Robustness Stress Testing Suite (Inference-Only)
======================================================================
Evaluates the locked GlucoShield Hybrid Forecaster (Seed 7) under controlled,
causally valid input perturbations:
  1. CGM Sensor Gaussian Noise (sigma in {5, 10, 15, 20} mg/dL)
  2. Missing CGM Data / Dropouts (15m, 30m, 60m, 120m causal backward hold)
  3. Meal Logging Carbohydrate Errors (-50%, -30%, +30%, +50%, Missed 100%)
  4. Insulin Bolus Timing Jitter (+/- 15m, +/- 30m)
Generates Figure 5 (Robustness Degradation Curves).
"""

import os
import sys
import json
import numpy as np
import pandas as pd
import torch
import matplotlib.pyplot as plt
import seaborn as sns
import joblib

# Force unbuffered output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

BASE_DIR = "D:/ML PROJECT"
DATA_DIR = os.path.join(BASE_DIR, "data", "final")
META_DIR = os.path.join(BASE_DIR, "data", "metadata")
MODELS_DIR = os.path.join(BASE_DIR, "models")
OUT_RES_DIR = os.path.join(BASE_DIR, "evaluation", "phase6", "results")
OUT_FIG_DIR = os.path.join(BASE_DIR, "evaluation", "phase6", "figures")

os.makedirs(OUT_RES_DIR, exist_ok=True)
os.makedirs(OUT_FIG_DIR, exist_ok=True)

sys.path.insert(0, BASE_DIR)
from baselines.evaluate_baselines import clarke_error_grid
from neural.models import GlucoShieldMultiTaskRNN
from physiology.hybrid_fusion import AdaptiveFusionGate

def set_seed(seed=42):
    np.random.seed(seed)
    torch.manual_seed(seed)

def compute_clarke_ab(y_true, y_pred):
    res = clarke_error_grid(y_true, y_pred)
    return res["Zone_AB_pct"]

def main():
    print("=" * 80)
    print("GLUCOSHIELD PHASE 6 — ROBUSTNESS STRESS TESTING (INFERENCE ONLY)")
    print("=" * 80)
    set_seed(42)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Executing forward inference on: {device}")

    # 1. Load Clean Frozen Test Inputs & Scalers
    x_test_raw = np.load(os.path.join(DATA_DIR, "X_test_raw.npy"))  # (4113, 96, 22)
    static_test_scaled = np.load(os.path.join(DATA_DIR, "static_test_scaled.npy"))  # (4113, 9)
    y_test_true = np.load(os.path.join(DATA_DIR, "Y_test_trajectory.npy"))  # (4113, 20)
    
    feature_scaler = joblib.load(os.path.join(META_DIR, "feature_scaler.joblib"))
    
    # 2. Load Neural and Hybrid Checkpoints
    neural_ckpt = torch.load(os.path.join(MODELS_DIR, "glucoshield_neural_best.pt"), map_location=device)
    neural_model = GlucoShieldMultiTaskRNN(
        dynamic_dim=22,
        static_dim=9,
        hidden_dim=neural_ckpt["config"]["hidden"],
        num_layers=neural_ckpt["config"]["layers"],
        dropout=0.0,
        cell_type=neural_ckpt["config"]["cell_type"]
    ).to(device)
    neural_model.load_state_dict(neural_ckpt["model_state_dict"])
    neural_model.eval()

    from physiology.hybrid_fusion import GlucoShieldHybridForecaster

    hybrid_ckpt = torch.load(os.path.join(MODELS_DIR, "glucoshield_hybrid_best.pt"), map_location=device)
    hybrid_model = GlucoShieldHybridForecaster(
        neural_model=neural_model,
        freeze_neural=True
    ).to(device)
    hybrid_model.load_state_dict(hybrid_ckpt)
    hybrid_model.eval()

    # Load frozen standalone ODE predictions for baseline fusion
    preds_ode_test = np.load(os.path.join(BASE_DIR, "results", "digital_twin", "preds_ode_standalone_test.npy"))
    t_ode = torch.tensor(preds_ode_test, dtype=torch.float32, device=device)
    t_static = torch.tensor(static_test_scaled, dtype=torch.float32, device=device)

    def run_hybrid_inference(x_raw_perturbed):
        """Runs fast hybrid inference given perturbed raw dynamic inputs."""
        N, T, D = x_raw_perturbed.shape
        x_flat = x_raw_perturbed.reshape(-1, D)
        x_scaled_flat = feature_scaler.transform(x_flat)
        x_scaled = x_scaled_flat.reshape(N, T, D)
        
        t_x = torch.tensor(x_scaled, dtype=torch.float32, device=device)
        
        # Batch inference in chunks of 512
        preds_list = []
        batch_size = 512
        with torch.no_grad():
            for i in range(0, N, batch_size):
                b_x = t_x[i:i+batch_size]
                b_s = t_static[i:i+batch_size]
                b_ode = t_ode[i:i+batch_size]
                
                out = hybrid_model.neural_model(b_x, b_s)
                y_neural = out["trajectory"]
                
                # Dynamic gate features: [vel, accel, roll_std, ins_sum, carb_sum]
                g_vel = b_x[:, -1, 1:2]
                g_acc = b_x[:, -1, 2:3]
                g_std = b_x[:, -1, 3:4]
                g_ins = b_x[:, -1, 5:6]
                g_crb = b_x[:, -1, 6:7]
                g_feat = torch.cat([g_vel, g_acc, g_std, g_ins, g_crb], dim=-1)
                
                alpha = hybrid_model.fusion_gate(g_feat)
                y_fused = alpha * y_neural + (1.0 - alpha) * b_ode
                res_in = torch.cat([y_fused, b_s], dim=-1)
                r_res = hybrid_model.residual_head(res_in)
                y_final = torch.clamp(y_fused + r_res, min=20.0, max=500.0)
                preds_list.append(y_final.cpu().numpy())
                
        return np.concatenate(preds_list, axis=0)
                
        return np.concatenate(preds_list, axis=0)

    # Compute clean unperturbed baseline
    preds_clean = run_hybrid_inference(x_test_raw)
    diff_clean = preds_clean - y_test_true
    clean_mae = float(np.mean(np.abs(diff_clean)))
    clean_rmse = float(np.sqrt(np.mean(diff_clean ** 2)))
    clean_zab = compute_clarke_ab(y_test_true, preds_clean)
    print(f"\nClean Baseline Hybrid: MAE={clean_mae:.2f} mg/dL | RMSE={clean_rmse:.2f} mg/dL | Clarke A+B={clean_zab:.2f}%")

    robustness_results = {
        "clean_baseline": {"MAE": clean_mae, "RMSE": clean_rmse, "Clarke_AB": clean_zab},
        "sensor_noise": {},
        "missing_data": {},
        "meal_error": {},
        "insulin_jitter": {}
    }

    # =========================================================================
    # STRESS TEST 1: CGM SENSOR GAUSSIAN NOISE
    # =========================================================================
    print("\n--- [1] CGM Sensor Gaussian Noise Stress Test ---")
    noise_sigmas = [5.0, 10.0, 15.0, 20.0]
    for sig in noise_sigmas:
        x_noisy = x_test_raw.copy()
        noise = np.random.normal(0.0, sig, size=(x_noisy.shape[0], x_noisy.shape[1], 1))
        x_noisy[:, :, 0:1] += noise  # Add noise to glucose channel
        # Recompute velocity and accel approximately
        x_noisy[:, 1:, 1:2] = (x_noisy[:, 1:, 0:1] - x_noisy[:, :-1, 0:1])
        x_noisy[:, 1:, 2:3] = (x_noisy[:, 1:, 1:2] - x_noisy[:, :-1, 1:2])
        
        preds_p = run_hybrid_inference(x_noisy)
        diff_p = preds_p - y_test_true
        mae_p = float(np.mean(np.abs(diff_p)))
        rmse_p = float(np.sqrt(np.mean(diff_p ** 2)))
        zab_p = compute_clarke_ab(y_test_true, preds_p)
        deg_pct = float((mae_p - clean_mae) / clean_mae * 100.0)

        robustness_results["sensor_noise"][f"sigma_{int(sig)}"] = {
            "sigma_mg_dl": sig,
            "MAE": round(mae_p, 2),
            "RMSE": round(rmse_p, 2),
            "Clarke_AB": round(zab_p, 2),
            "degradation_pct": round(deg_pct, 2)
        }
        print(f"  Noise sigma = {sig:>4.1f} mg/dL: MAE = {mae_p:>5.2f} mg/dL (+{deg_pct:>4.1f}%) | RMSE = {rmse_p:>5.2f} mg/dL | Clarke A+B = {zab_p:>5.2f}%")

    # =========================================================================
    # STRESS TEST 2: MISSING CGM DATA / DROPOUTS (CAUSAL ZERO-ORDER HOLD)
    # =========================================================================
    print("\n--- [2] Missing CGM Data / Dropout Stress Test ---")
    drop_durations = [1, 2, 4, 8]  # 15m, 30m, 60m, 120m
    drop_labels = ["15min", "30min", "60min", "120min"]

    for dur, lbl in zip(drop_durations, drop_labels):
        x_drop = x_test_raw.copy()
        # Hold last valid observation before the gap (strictly causal backward hold)
        for d in range(dur):
            x_drop[:, -1 - d, 0] = x_drop[:, -1 - dur, 0]
            x_drop[:, -1 - d, 1] = 0.0  # Zero velocity during dropout
            x_drop[:, -1 - d, 2] = 0.0  # Zero accel during dropout

        preds_p = run_hybrid_inference(x_drop)
        diff_p = preds_p - y_test_true
        mae_p = float(np.mean(np.abs(diff_p)))
        rmse_p = float(np.sqrt(np.mean(diff_p ** 2)))
        zab_p = compute_clarke_ab(y_test_true, preds_p)
        deg_pct = float((mae_p - clean_mae) / clean_mae * 100.0)

        robustness_results["missing_data"][lbl] = {
            "dropout_steps": dur,
            "dropout_minutes": dur * 15,
            "MAE": round(mae_p, 2),
            "RMSE": round(rmse_p, 2),
            "Clarke_AB": round(zab_p, 2),
            "degradation_pct": round(deg_pct, 2)
        }
        print(f"  Dropout gap = {lbl:>6}: MAE = {mae_p:>5.2f} mg/dL (+{deg_pct:>4.1f}%) | RMSE = {rmse_p:>5.2f} mg/dL | Clarke A+B = {zab_p:>5.2f}%")

    # =========================================================================
    # STRESS TEST 3: MEAL CARBOHYDRATE LOGGING UNCERTAINTY
    # =========================================================================
    print("\n--- [3] Meal Carbohydrate Logging Uncertainty Stress Test ---")
    meal_scales = [0.5, 0.7, 1.3, 1.5, 0.0]
    meal_labels = ["-50% Carbs", "-30% Carbs", "+30% Carbs", "+50% Carbs", "100% Missed Meal"]

    for sc, lbl in zip(meal_scales, meal_labels):
        x_meal = x_test_raw.copy()
        x_meal[:, :, 6] *= sc  # Scale raw carb channel (channel 6)
        x_meal[:, :, 14] *= sc # Scale rolling carb sum (channel 14)

        preds_p = run_hybrid_inference(x_meal)
        diff_p = preds_p - y_test_true
        mae_p = float(np.mean(np.abs(diff_p)))
        rmse_p = float(np.sqrt(np.mean(diff_p ** 2)))
        zab_p = compute_clarke_ab(y_test_true, preds_p)
        deg_pct = float((mae_p - clean_mae) / clean_mae * 100.0)

        robustness_results["meal_error"][lbl] = {
            "scale_factor": sc,
            "MAE": round(mae_p, 2),
            "RMSE": round(rmse_p, 2),
            "Clarke_AB": round(zab_p, 2),
            "degradation_pct": round(deg_pct, 2)
        }
        print(f"  Carb Perturbation = {lbl:<18}: MAE = {mae_p:>5.2f} mg/dL (+{deg_pct:>4.1f}%) | RMSE = {rmse_p:>5.2f} mg/dL | Clarke A+B = {zab_p:>5.2f}%")

    # =========================================================================
    # STRESS TEST 4: INSULIN BOLUS TIMING UNCERTAINTY
    # =========================================================================
    print("\n--- [4] Insulin Bolus Timing Jitter Stress Test ---")
    shift_steps = [-2, -1, 1, 2]  # -30m, -15m, +15m, +30m
    shift_labels = ["-30min (Early)", "-15min (Early)", "+15min (Late)", "+30min (Late)"]

    for sh, lbl in zip(shift_steps, shift_labels):
        x_ins = x_test_raw.copy()
        # Roll insulin channels along time axis
        x_ins[:, :, 5] = np.roll(x_ins[:, :, 5], shift=sh, axis=1)
        if sh > 0:
            x_ins[:, :sh, 5] = 0.0
        elif sh < 0:
            x_ins[:, sh:, 5] = 0.0

        preds_p = run_hybrid_inference(x_ins)
        diff_p = preds_p - y_test_true
        mae_p = float(np.mean(np.abs(diff_p)))
        rmse_p = float(np.sqrt(np.mean(diff_p ** 2)))
        zab_p = compute_clarke_ab(y_test_true, preds_p)
        deg_pct = float((mae_p - clean_mae) / clean_mae * 100.0)

        robustness_results["insulin_jitter"][lbl] = {
            "shift_steps": sh,
            "shift_minutes": sh * 15,
            "MAE": round(mae_p, 2),
            "RMSE": round(rmse_p, 2),
            "Clarke_AB": round(zab_p, 2),
            "degradation_pct": round(deg_pct, 2)
        }
        print(f"  Insulin Shift = {lbl:<18}: MAE = {mae_p:>5.2f} mg/dL (+{deg_pct:>4.1f}%) | RMSE = {rmse_p:>5.2f} mg/dL | Clarke A+B = {zab_p:>5.2f}%")

    # Save to JSON
    out_json_path = os.path.join(OUT_RES_DIR, "robustness_stress_results.json")
    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump(robustness_results, f, indent=2)
    print(f"\nSaved robustness stress results to: {out_json_path}")

    # =========================================================================
    # PUBLICATION FIGURE 5: ROBUSTNESS DEGRADATION MULTIPANEL
    # =========================================================================
    print("\n--- Generating Figure 5: Robustness Degradation Multipanel ---")
    sns.set_theme(style="whitegrid", font="sans-serif")
    fig, axes = plt.subplots(2, 2, figsize=(14, 10), dpi=300)

    # Subplot A: CGM Sensor Noise
    sig_vals = [0.0] + noise_sigmas
    sig_maes = [clean_mae] + [robustness_results["sensor_noise"][f"sigma_{int(s)}"]["MAE"] for s in noise_sigmas]
    axes[0, 0].plot(sig_vals, sig_maes, marker="o", linewidth=2.2, color="#d62728")
    axes[0, 0].axhline(clean_mae, color="black", linestyle="--", alpha=0.6, label=f"Clean MAE ({clean_mae:.2f})")
    axes[0, 0].set_title("A. CGM Sensor Noise Perturbation", fontsize=12, fontweight="bold")
    axes[0, 0].set_xlabel("Gaussian Noise σ (mg/dL)", fontsize=11)
    axes[0, 0].set_ylabel("Hybrid Forecast MAE (mg/dL)", fontsize=11)
    axes[0, 0].legend(loc="upper left", frameon=True)

    # Subplot B: Missing CGM Dropouts
    drop_mins = [0] + [dur * 15 for dur in drop_durations]
    drop_maes = [clean_mae] + [robustness_results["missing_data"][lbl]["MAE"] for lbl in drop_labels]
    axes[0, 1].plot(drop_mins, drop_maes, marker="s", linewidth=2.2, color="#ff7f0e")
    axes[0, 1].axhline(clean_mae, color="black", linestyle="--", alpha=0.6, label=f"Clean MAE ({clean_mae:.2f})")
    axes[0, 1].set_title("B. Missing CGM Dropout Gap (Causal Backward Hold)", fontsize=12, fontweight="bold")
    axes[0, 1].set_xlabel("Dropout Duration (Minutes)", fontsize=11)
    axes[0, 1].set_ylabel("Hybrid Forecast MAE (mg/dL)", fontsize=11)
    axes[0, 1].legend(loc="upper left", frameon=True)

    # Subplot C: Meal Carbohydrate Errors
    m_labels_plot = ["-50%", "-30%", "Clean (0%)", "+30%", "+50%", "Missed (100%)"]
    m_maes_plot = [
        robustness_results["meal_error"]["-50% Carbs"]["MAE"],
        robustness_results["meal_error"]["-30% Carbs"]["MAE"],
        clean_mae,
        robustness_results["meal_error"]["+30% Carbs"]["MAE"],
        robustness_results["meal_error"]["+50% Carbs"]["MAE"],
        robustness_results["meal_error"]["100% Missed Meal"]["MAE"]
    ]
    axes[1, 0].bar(np.arange(len(m_labels_plot)), m_maes_plot, color="#2ca02c", alpha=0.85, width=0.5)
    axes[1, 0].axhline(clean_mae, color="black", linestyle="--", alpha=0.6, label=f"Clean MAE ({clean_mae:.2f})")
    axes[1, 0].set_title("C. Meal Carbohydrate Logging Errors", fontsize=12, fontweight="bold")
    axes[1, 0].set_xticks(np.arange(len(m_labels_plot)))
    axes[1, 0].set_xticklabels(m_labels_plot, fontsize=9)
    axes[1, 0].set_ylabel("Hybrid Forecast MAE (mg/dL)", fontsize=11)
    axes[1, 0].legend(loc="upper left", frameon=True)

    # Subplot D: Insulin Bolus Timing Jitter
    ins_labels_plot = ["-30m", "-15m", "Clean (0m)", "+15m", "+30m"]
    ins_maes_plot = [
        robustness_results["insulin_jitter"]["-30min (Early)"]["MAE"],
        robustness_results["insulin_jitter"]["-15min (Early)"]["MAE"],
        clean_mae,
        robustness_results["insulin_jitter"]["+15min (Late)"]["MAE"],
        robustness_results["insulin_jitter"]["+30min (Late)"]["MAE"]
    ]
    axes[1, 1].plot(np.arange(len(ins_labels_plot)), ins_maes_plot, marker="^", linewidth=2.2, color="#1f77b4")
    axes[1, 1].axhline(clean_mae, color="black", linestyle="--", alpha=0.6, label=f"Clean MAE ({clean_mae:.2f})")
    axes[1, 1].set_title("D. Insulin Bolus Timestamp Uncertainty", fontsize=12, fontweight="bold")
    axes[1, 1].set_xticks(np.arange(len(ins_labels_plot)))
    axes[1, 1].set_xticklabels(ins_labels_plot, fontsize=10)
    axes[1, 1].set_ylabel("Hybrid Forecast MAE (mg/dL)", fontsize=11)
    axes[1, 1].legend(loc="upper left", frameon=True)

    plt.tight_layout()
    fig5_path = os.path.join(OUT_FIG_DIR, "fig5_robustness_degradation_curves.png")
    plt.savefig(fig5_path, dpi=300)
    plt.close()
    print(f"  Saved Figure 5 to: {fig5_path}")
    print("=" * 80)

if __name__ == "__main__":
    main()
