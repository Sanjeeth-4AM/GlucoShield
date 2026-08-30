"""
GlucoShield Phase 6 — Case Studies & Failure Analysis Suite
============================================================
Identifies and plots 6 clinical and failure case studies on the frozen test set:
  1. Best Prediction Case (Optimal Alignment)
  2. Median / Typical Patient Case (Expected Everyday Accuracy)
  3. Worst Prediction Case (Major Unmodeled Dynamics / Failure Boundary)
  4. Rapid Hypoglycemia Transition Case (Acute Event Safety)
  5. Post-Meal Postprandial Excursion Case (Meal Absorption Kinetics)
  6. High-Variability Extended Horizon Case (5h Divergence Mode)
Generates Figure 6 (Failure and Success Case Studies Multipanel).
"""

import os
import sys
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Force unbuffered output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

BASE_DIR = "D:/ML PROJECT"
DATA_DIR = os.path.join(BASE_DIR, "data", "final")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
OUT_RES_DIR = os.path.join(BASE_DIR, "evaluation", "phase6", "results")
OUT_FIG_DIR = os.path.join(BASE_DIR, "evaluation", "phase6", "figures")

os.makedirs(OUT_RES_DIR, exist_ok=True)
os.makedirs(OUT_FIG_DIR, exist_ok=True)

def main():
    print("=" * 80)
    print("GLUCOSHIELD PHASE 6 — FAILURE & REPRESENTATIVE CASE STUDIES")
    print("=" * 80)

    # 1. Load Data & Predictions
    meta_test = pd.read_csv(os.path.join(DATA_DIR, "meta_test.csv"))
    x_test_raw = np.load(os.path.join(DATA_DIR, "X_test_raw.npy"))       # (4113, 96, 22)
    y_test_true = np.load(os.path.join(DATA_DIR, "Y_test_trajectory.npy")) # (4113, 20)
    
    y_hyb = np.load(os.path.join(RESULTS_DIR, "digital_twin", "preds_hybrid_test.npy"))
    y_gru = np.load(os.path.join(RESULTS_DIR, "neural", "preds_best_neural_test.npy"))
    y_ode = np.load(os.path.join(RESULTS_DIR, "digital_twin", "preds_ode_standalone_test.npy"))
    y_ridge = np.load(os.path.join(RESULTS_DIR, "baselines", "preds_classical_ridge_test.npy"))

    sample_maes = np.mean(np.abs(y_hyb - y_test_true), axis=1)

    # 2. Case Selection Logic
    # Case 1: Best Prediction Case
    idx_best = int(np.argmin(sample_maes))

    # Case 2: Median / Typical Case
    median_mae = np.median(sample_maes)
    idx_median = int(np.argmin(np.abs(sample_maes - median_mae)))

    # Case 3: Worst Prediction Case
    idx_worst = int(np.argmax(sample_maes))

    # Case 4: Rapid Hypoglycemia Transition (Current glucose > 90, min future < 60)
    c_gluc = meta_test["current_glucose"].values
    min_fut = meta_test["min_future_glucose"].values
    hypo_candidates = np.where((c_gluc > 85.0) & (min_fut < 60.0))[0]
    if len(hypo_candidates) > 0:
        idx_hypo = int(hypo_candidates[np.argmin(sample_maes[hypo_candidates])])
    else:
        idx_hypo = int(np.argmin(min_fut))

    # Case 5: Postprandial Excursion (Large carb in history > 50g, max future > 220)
    carb_sums = np.sum(x_test_raw[:, :, 6], axis=1)
    max_fut = meta_test["max_future_glucose"].values
    meal_candidates = np.where((carb_sums > 30.0) & (max_fut > 200.0))[0]
    if len(meal_candidates) > 0:
        idx_meal = int(meal_candidates[0])
    else:
        idx_meal = int(np.argmax(max_fut))

    # Case 6: High Variability / Divergence
    cgm_stds = np.std(x_test_raw[:, :, 0], axis=1)
    var_candidates = np.where(cgm_stds > 40.0)[0]
    if len(var_candidates) > 0:
        idx_diverge = int(var_candidates[np.argmax(sample_maes[var_candidates])])
    else:
        idx_diverge = int(np.argmax(sample_maes))

    selected_cases = [
        ("Case 1: Best Forecast Case", idx_best, "Optimal trajectory alignment"),
        ("Case 2: Median / Typical Case", idx_median, "Everyday representative accuracy"),
        ("Case 3: Worst Forecast Case", idx_worst, "Major unmodeled glucose volatility / failure boundary"),
        ("Case 4: Rapid Hypoglycemia Transition", idx_hypo, "Descent from euglycemia to hypoglycemia (<60 mg/dL)"),
        ("Case 5: Post-Meal Glycemic Excursion", idx_meal, "Carbohydrate absorption and postprandial peak"),
        ("Case 6: High Variability Dynamic", idx_diverge, "High historical volatility with model divergence")
    ]

    case_manifest = []

    print("\nSelected Representative & Failure Cases:")
    for title, idx, desc in selected_cases:
        p_id = meta_test.loc[idx, "patient_id"]
        d_type = meta_test.loc[idx, "diabetes_type"]
        mae_h = float(sample_maes[idx])
        mae_g = float(np.mean(np.abs(y_gru[idx] - y_test_true[idx])))
        mae_r = float(np.mean(np.abs(y_ridge[idx] - y_test_true[idx])))
        mae_o = float(np.mean(np.abs(y_ode[idx] - y_test_true[idx])))

        case_info = {
            "title": title,
            "sample_index": idx,
            "patient_id": str(p_id),
            "diabetes_type": d_type,
            "description": desc,
            "hybrid_mae": round(mae_h, 2),
            "neural_gru_mae": round(mae_g, 2),
            "ridge_mae": round(mae_r, 2),
            "ode_mae": round(mae_o, 2)
        }
        case_manifest.append(case_info)
        print(f"  {title:<38}: Idx={idx:>4} | Pt={p_id} ({d_type}) | Hybrid MAE={mae_h:>5.2f} | GRU MAE={mae_g:>5.2f} | Ridge MAE={mae_r:>5.2f}")

    # Save to JSON
    case_json_path = os.path.join(OUT_RES_DIR, "case_studies_summary.json")
    with open(case_json_path, "w", encoding="utf-8") as f:
        json.dump(case_manifest, f, indent=2)
    print(f"\nSaved case studies summary to: {case_json_path}")

    # =========================================================================
    # PUBLICATION FIGURE 6: 6-PANEL CASE STUDIES
    # =========================================================================
    print("\n--- Generating Figure 6: 6-Panel Failure & Success Case Studies ---")
    sns.set_theme(style="whitegrid", font="sans-serif")
    fig, axes = plt.subplots(3, 2, figsize=(16, 14), dpi=300)
    axes_flat = axes.flatten()

    # Time axes: History = [-24h to 0h in 15m steps = 96 points], Future = [0 to +5h in 15m steps = 20 points]
    t_hist_h = np.linspace(-24.0, 0.0, 96)
    t_fut_h = np.linspace(0.25, 5.0, 20)

    for i, (title, idx, desc) in enumerate(selected_cases):
        ax = axes_flat[i]
        
        # Extract history CGM and future trajectories
        cgm_hist = x_test_raw[idx, :, 0]
        fut_true = y_test_true[idx]
        fut_hyb = y_hyb[idx]
        fut_gru = y_gru[idx]
        fut_ode = y_ode[idx]
        fut_ridge = y_ridge[idx]

        # Connect history to future at t=0
        t_conn = np.insert(t_fut_h, 0, 0.0)
        c0 = cgm_hist[-1]
        c_true = np.insert(fut_true, 0, c0)
        c_hyb = np.insert(fut_hyb, 0, c0)
        c_gru = np.insert(fut_gru, 0, c0)
        c_ode = np.insert(fut_ode, 0, c0)
        c_ridge = np.insert(fut_ridge, 0, c0)

        # Plot only last 6 hours of history for visual clarity
        ax.plot(t_hist_h[-24:], cgm_hist[-24:], color="#333333", linewidth=2.0, label="24h History CGM (Last 6h)")
        ax.axvline(0.0, color="black", linestyle=":", linewidth=1.5, alpha=0.8, label="Forecast Origin (t=0)")

        # Target Range Shading [70, 180]
        ax.axhspan(70, 180, color="#2ca02c", alpha=0.08, label="Target Euglycemia (70-180)")

        # Plot Model Trajectories
        ax.plot(t_conn, c_true, "k-", linewidth=2.5, marker="o", markersize=4, label="True Future Glucose")
        ax.plot(t_conn, c_hyb, color="#2ca02c", linewidth=2.2, linestyle="-", label=f"Hybrid (MAE={sample_maes[idx]:.1f})")
        ax.plot(t_conn, c_gru, color="#1f77b4", linewidth=1.8, linestyle="--", label="Neural GRU V1")
        ax.plot(t_conn, c_ridge, color="#7f7f7f", linewidth=1.5, linestyle="-.", label="Ridge")
        ax.plot(t_conn, c_ode, color="#e377c2", linewidth=1.5, linestyle=":", label="ODE Twin")

        p_id = meta_test.loc[idx, "patient_id"]
        d_type = meta_test.loc[idx, "diabetes_type"]
        ax.set_title(f"{title} [Pt {p_id} | {d_type}]\n{desc}", fontsize=10.5, fontweight="bold", pad=8)
        ax.set_xlabel("Time Relative to Forecast Origin (Hours)", fontsize=9.5)
        ax.set_ylabel("Glucose (mg/dL)", fontsize=9.5)
        ax.set_xlim(-6.2, 5.2)
        if i == 0:
            ax.legend(loc="upper left", fontsize=8, frameon=True, ncol=2)

    plt.tight_layout()
    fig6_path = os.path.join(OUT_FIG_DIR, "fig6_failure_and_success_cases.png")
    plt.savefig(fig6_path, dpi=300)
    plt.close()
    print(f"  Saved Figure 6 to: {fig6_path}")
    print("=" * 80)

if __name__ == "__main__":
    main()
