"""
GlucoShield Phase 6 — Horizon, Clinical Range, Trend, and Subgroup Analysis
===========================================================================
Computes:
  1. Complete 20-horizon error trajectories & Clarke safety curves
  2. Clinical range stratification (Hypo <70, Euglycemic 70-180, Hyper >180)
  3. Glycemic velocity trend error analysis (Falling Rapidly -> Rising Rapidly)
  4. Subgroup stratification (T1DM vs T2DM, Age, BMI, HbA1c)
  5. Component ablation comparison table
  6. Generates Figure 2 (Horizon Curves) and Figure 3 (Clinical Ranges & Trends)
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

sys.path.insert(0, BASE_DIR)
from baselines.evaluate_baselines import clarke_error_grid

def compute_clarke_ab(y_true, y_pred):
    res = clarke_error_grid(y_true, y_pred)
    return res["Zone_A_pct"], res["Zone_B_pct"], res["Zone_AB_pct"]

def main():
    print("=" * 80)
    print("GLUCOSHIELD PHASE 6 — HORIZON, RANGE, TREND & SUBGROUP ANALYSIS")
    print("=" * 80)

    # 1. Load Data
    meta_test = pd.read_csv(os.path.join(DATA_DIR, "meta_test.csv"))
    y_true = np.load(os.path.join(DATA_DIR, "Y_test_trajectory.npy"))
    x_test_raw = np.load(os.path.join(DATA_DIR, "X_test_raw.npy"))
    static_test_raw = np.load(os.path.join(DATA_DIR, "static_test_raw.npy"))

    models = {
        "Persistence": np.load(os.path.join(RESULTS_DIR, "baselines", "preds_persistence_test.npy")),
        "LinearTrend": np.load(os.path.join(RESULTS_DIR, "baselines", "preds_linear_trend_test.npy")),
        "Ridge": np.load(os.path.join(RESULTS_DIR, "baselines", "preds_classical_ridge_test.npy")),
        "Neural_GRU_V1": np.load(os.path.join(RESULTS_DIR, "neural", "preds_best_neural_test.npy")),
        "Standalone_ODE": np.load(os.path.join(RESULTS_DIR, "digital_twin", "preds_ode_standalone_test.npy")),
        "Hybrid_Forecaster": np.load(os.path.join(RESULTS_DIR, "digital_twin", "preds_hybrid_test.npy"))
    }

    # =========================================================================
    # MILESTONE P6-5: COMPLETE 20-HORIZON ANALYSIS
    # =========================================================================
    print("\n--- [MILESTONE P6-5] Computing 20-Horizon Error Trajectories ---")
    horizon_labels = [f"{(k+1)*15}m" for k in range(20)]
    horizon_minutes = [(k+1)*15 for k in range(20)]

    horizon_table = []
    for k in range(20):
        h_row = {"step": k + 1, "horizon_min": horizon_minutes[k], "label": horizon_labels[k]}
        y_t_k = y_true[:, k]

        for m_name, m_preds in models.items():
            y_p_k = m_preds[:, k]
            diff_k = y_p_k - y_t_k
            h_mae = float(np.mean(np.abs(diff_k)))
            h_rmse = float(np.sqrt(np.mean(diff_k ** 2)))
            za, zb, zab = compute_clarke_ab(y_t_k, y_p_k)

            h_row[f"{m_name}_MAE"] = round(h_mae, 2)
            h_row[f"{m_name}_RMSE"] = round(h_rmse, 2)
            h_row[f"{m_name}_Clarke_AB"] = round(zab, 2)

        horizon_table.append(h_row)

    df_horizon = pd.DataFrame(horizon_table)
    print(f"  Computed 20-step horizon table (15m to 300m / 5h).")

    # =========================================================================
    # MILESTONE P6-6: CLINICAL RANGE & GLUCOSE TREND ANALYSIS
    # =========================================================================
    print("\n--- [MILESTONE P6-6] Computing Clinical Glycemic Range & Trend Stratifications ---")
    
    # Range masks based on true future trajectory values (overall elements)
    y_true_flat = y_true.flatten()
    range_masks = {
        "Hypoglycemia (<70 mg/dL)": y_true_flat < 70.0,
        "Euglycemia (70-180 mg/dL)": (y_true_flat >= 70.0) & (y_true_flat <= 180.0),
        "Hyperglycemia (>180 mg/dL)": y_true_flat > 180.0
    }

    range_results = {}
    for r_name, r_mask in range_masks.items():
        n_elem = int(np.sum(r_mask))
        pct_elem = float(n_elem / len(y_true_flat) * 100.0)
        t_sub = y_true_flat[r_mask]
        
        r_dict = {"sample_points": n_elem, "prevalence_pct": round(pct_elem, 2), "models": {}}
        for m_name, m_preds in models.items():
            p_sub = m_preds.flatten()[r_mask]
            diff_sub = p_sub - t_sub
            r_dict["models"][m_name] = {
                "MAE": round(float(np.mean(np.abs(diff_sub))), 2),
                "RMSE": round(float(np.sqrt(np.mean(diff_sub ** 2))), 2)
            }
        range_results[r_name] = r_dict
        print(f"  {r_name:<28}: N={n_elem:>5,} ({pct_elem:>5.1f}%) | Hybrid MAE={r_dict['models']['Hybrid_Forecaster']['MAE']:>5.2f} | GRU MAE={r_dict['models']['Neural_GRU_V1']['MAE']:>5.2f}")

    # Trend masks based on current glucose velocity channel (Channel 1 at t=0)
    velocities = x_test_raw[:, -1, 1]  # mg/dL per 15 min
    trend_bins = {
        "Falling Rapidly (v < -2.0)": velocities < -2.0,
        "Falling (-2.0 <= v < -0.5)": (velocities >= -2.0) & (velocities < -0.5),
        "Stable (-0.5 <= v <= +0.5)": (velocities >= -0.5) & (velocities <= 0.5),
        "Rising (+0.5 < v <= +2.0)": (velocities > 0.5) & (velocities <= 2.0),
        "Rising Rapidly (v > +2.0)": velocities > 2.0
    }

    trend_results = {}
    for tr_name, tr_mask in trend_bins.items():
        n_seqs = int(np.sum(tr_mask))
        pct_seqs = float(n_seqs / len(velocities) * 100.0)
        t_sub = y_true[tr_mask]

        tr_dict = {"sequence_count": n_seqs, "prevalence_pct": round(pct_seqs, 2), "models": {}}
        for m_name, m_preds in models.items():
            p_sub = m_preds[tr_mask]
            diff_sub = p_sub - t_sub
            tr_dict["models"][m_name] = {
                "MAE": round(float(np.mean(np.abs(diff_sub))), 2),
                "RMSE": round(float(np.sqrt(np.mean(diff_sub ** 2))), 2)
            }
        trend_results[tr_name] = tr_dict
        print(f"  {tr_name:<30}: N={n_seqs:>5,} ({pct_seqs:>5.1f}%) | Hybrid MAE={tr_dict['models']['Hybrid_Forecaster']['MAE']:>5.2f} | GRU MAE={tr_dict['models']['Neural_GRU_V1']['MAE']:>5.2f}")

    # =========================================================================
    # MILESTONE P6-8: SUBGROUP STRATIFICATION
    # =========================================================================
    print("\n--- [MILESTONE P6-8] Subgroup Stratification Analysis ---")
    subgroups = {}

    # A. Diabetes Subgroup
    for d_type in ["T1DM", "T2DM"]:
        mask = (meta_test["diabetes_type"] == d_type).values
        n_pts = meta_test.loc[mask, "patient_id"].nunique()
        n_seqs = int(np.sum(mask))
        t_sub = y_true[mask]
        
        sg_dict = {"patient_count": n_pts, "sequence_count": n_seqs, "is_exploratory": (d_type == "T1DM"), "models": {}}
        for m_name in ["Ridge", "Neural_GRU_V1", "Standalone_ODE", "Hybrid_Forecaster"]:
            p_sub = models[m_name][mask]
            diff_sub = p_sub - t_sub
            za, zb, zab = compute_clarke_ab(t_sub, p_sub)
            sg_dict["models"][m_name] = {
                "MAE": round(float(np.mean(np.abs(diff_sub))), 2),
                "RMSE": round(float(np.sqrt(np.mean(diff_sub ** 2))), 2),
                "Clarke_AB": round(zab, 2)
            }
        subgroups[f"Diabetes_{d_type}"] = sg_dict
        print(f"  {d_type} (N={n_pts} pts, {n_seqs} seqs) [Exploratory={sg_dict['is_exploratory']}]: Hybrid RMSE={sg_dict['models']['Hybrid_Forecaster']['RMSE']:.2f} mg/dL | Clarke A+B={sg_dict['models']['Hybrid_Forecaster']['Clarke_AB']:.2f}%")

    # B. Age Brackets (<55, 55-65, >65)
    ages = static_test_raw[:, 0]
    for a_name, a_mask in [("<55 Years", ages < 55.0), ("55-65 Years", (ages >= 55.0) & (ages <= 65.0)), (">65 Years", ages > 65.0)]:
        n_pts = meta_test.loc[a_mask, "patient_id"].nunique()
        n_seqs = int(np.sum(a_mask))
        t_sub = y_true[a_mask]

        sg_dict = {"patient_count": n_pts, "sequence_count": n_seqs, "models": {}}
        for m_name in ["Ridge", "Neural_GRU_V1", "Standalone_ODE", "Hybrid_Forecaster"]:
            p_sub = models[m_name][a_mask]
            diff_sub = p_sub - t_sub
            za, zb, zab = compute_clarke_ab(t_sub, p_sub)
            sg_dict["models"][m_name] = {
                "MAE": round(float(np.mean(np.abs(diff_sub))), 2),
                "RMSE": round(float(np.sqrt(np.mean(diff_sub ** 2))), 2),
                "Clarke_AB": round(zab, 2)
            }
        subgroups[f"Age_{a_name}"] = sg_dict
        print(f"  Age {a_name:<10} (N={n_pts} pts, {n_seqs} seqs): Hybrid RMSE={sg_dict['models']['Hybrid_Forecaster']['RMSE']:.2f} mg/dL")

    # C. BMI Brackets (<23, 23-26, >26)
    bmis = static_test_raw[:, 1]
    for b_name, b_mask in [("<23 kg/m2", bmis < 23.0), ("23-26 kg/m2", (bmis >= 23.0) & (bmis <= 26.0)), (">26 kg/m2", bmis > 26.0)]:
        n_pts = meta_test.loc[b_mask, "patient_id"].nunique()
        n_seqs = int(np.sum(b_mask))
        t_sub = y_true[b_mask]

        sg_dict = {"patient_count": n_pts, "sequence_count": n_seqs, "models": {}}
        for m_name in ["Ridge", "Neural_GRU_V1", "Standalone_ODE", "Hybrid_Forecaster"]:
            p_sub = models[m_name][b_mask]
            diff_sub = p_sub - t_sub
            za, zb, zab = compute_clarke_ab(t_sub, p_sub)
            sg_dict["models"][m_name] = {
                "MAE": round(float(np.mean(np.abs(diff_sub))), 2),
                "RMSE": round(float(np.sqrt(np.mean(diff_sub ** 2))), 2),
                "Clarke_AB": round(zab, 2)
            }
        subgroups[f"BMI_{b_name}"] = sg_dict
        print(f"  BMI {b_name:<10} (N={n_pts} pts, {n_seqs} seqs): Hybrid RMSE={sg_dict['models']['Hybrid_Forecaster']['RMSE']:.2f} mg/dL")

    # D. HbA1c Brackets (<65, 65-80, >80 mmol/mol)
    hba1cs = static_test_raw[:, 2]
    for h_name, h_mask in [("<65 mmol/mol", hba1cs < 65.0), ("65-80 mmol/mol", (hba1cs >= 65.0) & (hba1cs <= 80.0)), (">80 mmol/mol", hba1cs > 80.0)]:
        n_pts = meta_test.loc[h_mask, "patient_id"].nunique()
        n_seqs = int(np.sum(h_mask))
        t_sub = y_true[h_mask]

        sg_dict = {"patient_count": n_pts, "sequence_count": n_seqs, "models": {}}
        for m_name in ["Ridge", "Neural_GRU_V1", "Standalone_ODE", "Hybrid_Forecaster"]:
            p_sub = models[m_name][h_mask]
            diff_sub = p_sub - t_sub
            za, zb, zab = compute_clarke_ab(t_sub, p_sub)
            sg_dict["models"][m_name] = {
                "MAE": round(float(np.mean(np.abs(diff_sub))), 2),
                "RMSE": round(float(np.sqrt(np.mean(diff_sub ** 2))), 2),
                "Clarke_AB": round(zab, 2)
            }
        subgroups[f"HbA1c_{h_name}"] = sg_dict
        print(f"  HbA1c {h_name:<14} (N={n_pts} pts, {n_seqs} seqs): Hybrid RMSE={sg_dict['models']['Hybrid_Forecaster']['RMSE']:.2f} mg/dL")

    # =========================================================================
    # MILESTONE P6-9: COMPONENT CONTRIBUTION / ABLATION SUMMARY
    # =========================================================================
    print("\n--- [MILESTONE P6-9] Component Contribution Summary Table ---")
    component_table = [
        {"Component": "1. Persistence (Zero-Order Hold)", "Split": "Test", "MAE": 34.14, "RMSE": 49.01, "Clarke_AB": 91.85, "Contribution": "Static baseline assuming no glycemic change"},
        {"Component": "2. Linear Trend Extrapolation", "Split": "Test", "MAE": 55.76, "RMSE": 81.39, "Clarke_AB": 82.10, "Contribution": "Linear velocity projection (diverges at long horizons)"},
        {"Component": "3. Classical Ridge Regularized Baseline", "Split": "Test", "MAE": 25.37, "RMSE": 35.80, "Clarke_AB": 93.31, "Contribution": "L2 linear regularizer over 22-channel flat history"},
        {"Component": "4. Pure Standalone Population ODE", "Split": "Val (Cached)", "MAE": 34.01, "RMSE": 49.74, "Clarke_AB": 91.32, "Contribution": "Uncalibrated first-principles 6-compartment mass balance"},
        {"Component": "5. Biomarker-Prior Personalized ODE", "Split": "Val (Cached)", "MAE": 34.33, "RMSE": 46.58, "Clarke_AB": 90.85, "Contribution": "Tier 1 static MLP mapping 9 biomarkers to baseline parameters"},
        {"Component": "6. Standalone Calibrated ODE (Tier 1+2)", "Split": "Test", "MAE": 40.61, "RMSE": 52.67, "Clarke_AB": 89.65, "Contribution": "Moving horizon calibrated standalone physics simulation"},
        {"Component": "7. Neural Forecaster V1 (GRU-128)", "Split": "Test", "MAE": 24.45, "RMSE": 34.90, "Clarke_AB": 95.28, "Contribution": "Deep recurrent multi-task sequence pattern learning"},
        {"Component": "8. Full Adaptive Gated Hybrid Forecaster", "Split": "Test", "MAE": 24.14, "RMSE": 34.77, "Clarke_AB": 95.36, "Contribution": "Differentiable gated blending of Neural + ODE physics"}
    ]
    for c in component_table:
        print(f"  {c['Component']:<45} | Split: {c['Split']:<12} | MAE={c['MAE']:>5.2f} | RMSE={c['RMSE']:>5.2f} | Clarke A+B={c['Clarke_AB']:>5.2f}%")

    # Save all results to master JSON
    master_results = {
        "horizon_trajectories": df_horizon.to_dict(orient="records"),
        "clinical_ranges": range_results,
        "velocity_trends": trend_results,
        "subgroups": subgroups,
        "component_ablation_table": component_table
    }

    out_json_path = os.path.join(OUT_RES_DIR, "horizon_and_range_metrics.json")
    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump(master_results, f, indent=2)
    print(f"\nSaved horizon and range metrics to: {out_json_path}")

    # =========================================================================
    # PUBLICATION FIGURE 2: HORIZON-WISE ERROR TRAJECTORIES
    # =========================================================================
    print("\n--- Generating Figure 2: Horizon-Wise Error Trajectories ---")
    sns.set_theme(style="whitegrid", font="sans-serif")
    fig, axes = plt.subplots(1, 3, figsize=(18, 5), dpi=300)

    plot_models = ["Ridge", "Neural_GRU_V1", "Standalone_ODE", "Hybrid_Forecaster"]
    plot_labels = ["Ridge Baseline", "Neural GRU V1", "Standalone ODE", "GlucoShield Hybrid"]
    colors = ["#7f7f7f", "#1f77b4", "#e377c2", "#2ca02c"]
    styles = ["--", "-.", ":", "-"]

    # Subplot A: Horizon MAE Curves
    for m, lbl, col, sty in zip(plot_models, plot_labels, colors, styles):
        axes[0].plot(horizon_minutes, df_horizon[f"{m}_MAE"], label=lbl, color=col, linestyle=sty, linewidth=2.2, marker="o", markersize=4)
    axes[0].set_title("A. Forecast MAE Across Future Horizons (15m to 5h)", fontsize=12, fontweight="bold")
    axes[0].set_xlabel("Prediction Horizon (Minutes)", fontsize=11)
    axes[0].set_ylabel("Mean Absolute Error (mg/dL)", fontsize=11)
    axes[0].set_xticks([15, 60, 120, 180, 240, 300])
    axes[0].legend(loc="upper left", frameon=True)

    # Subplot B: Horizon RMSE Curves
    for m, lbl, col, sty in zip(plot_models, plot_labels, colors, styles):
        axes[1].plot(horizon_minutes, df_horizon[f"{m}_RMSE"], label=lbl, color=col, linestyle=sty, linewidth=2.2, marker="s", markersize=4)
    axes[1].set_title("B. Forecast RMSE Across Future Horizons (15m to 5h)", fontsize=12, fontweight="bold")
    axes[1].set_xlabel("Prediction Horizon (Minutes)", fontsize=11)
    axes[1].set_ylabel("Root Mean Squared Error (mg/dL)", fontsize=11)
    axes[1].set_xticks([15, 60, 120, 180, 240, 300])
    axes[1].legend(loc="upper left", frameon=True)

    # Subplot C: Horizon Clarke Error Grid Safe Zone A+B %
    for m, lbl, col, sty in zip(plot_models, plot_labels, colors, styles):
        axes[2].plot(horizon_minutes, df_horizon[f"{m}_Clarke_AB"], label=lbl, color=col, linestyle=sty, linewidth=2.2, marker="^", markersize=4)
    axes[2].axhline(95.0, color="red", linestyle=":", label="Clinical Target (95%)", linewidth=1.5)
    axes[2].set_title("C. Clinical Safety (Clarke Zone A+B %)", fontsize=12, fontweight="bold")
    axes[2].set_xlabel("Prediction Horizon (Minutes)", fontsize=11)
    axes[2].set_ylabel("Zone A+B (%)", fontsize=11)
    axes[2].set_xticks([15, 60, 120, 180, 240, 300])
    axes[2].set_ylim(85, 101)
    axes[2].legend(loc="lower left", frameon=True)

    plt.tight_layout()
    fig2_path = os.path.join(OUT_FIG_DIR, "fig2_horizon_error_trajectories.png")
    plt.savefig(fig2_path, dpi=300)
    plt.close()
    print(f"  Saved Figure 2 to: {fig2_path}")

    # =========================================================================
    # PUBLICATION FIGURE 3: CLINICAL GLYCEMIC RANGES & VELOCITY TRENDS
    # =========================================================================
    print("\n--- Generating Figure 3: Clinical Ranges & Velocity Trends ---")
    fig, axes = plt.subplots(1, 2, figsize=(16, 5), dpi=300)

    # Subplot A: Error by Clinical Range
    range_names = list(range_results.keys())
    range_hyb_mae = [range_results[r]["models"]["Hybrid_Forecaster"]["MAE"] for r in range_names]
    range_gru_mae = [range_results[r]["models"]["Neural_GRU_V1"]["MAE"] for r in range_names]
    range_ridge_mae = [range_results[r]["models"]["Ridge"]["MAE"] for r in range_names]

    x_r = np.arange(len(range_names))
    axes[0].bar(x_r - 0.25, range_ridge_mae, width=0.25, label="Ridge", color="#7f7f7f", alpha=0.85)
    axes[0].bar(x_r, range_gru_mae, width=0.25, label="Neural GRU V1", color="#1f77b4", alpha=0.85)
    axes[0].bar(x_r + 0.25, range_hyb_mae, width=0.25, label="GlucoShield Hybrid", color="#2ca02c", alpha=0.85)
    axes[0].set_xticks(x_r)
    axes[0].set_xticklabels(["Hypoglycemia\n(<70 mg/dL)", "Euglycemia\n(70-180 mg/dL)", "Hyperglycemia\n(>180 mg/dL)"], fontsize=10)
    axes[0].set_title("A. Forecast MAE by Target Glycemic Range", fontsize=12, fontweight="bold")
    axes[0].set_ylabel("MAE (mg/dL)", fontsize=11)
    axes[0].legend(loc="upper left", frameon=True)

    # Subplot B: Error by Glucose Velocity Trend
    trend_labels = ["Falling Rapidly\n(v < -2.0)", "Falling\n(-2 to -0.5)", "Stable\n(-0.5 to +0.5)", "Rising\n(+0.5 to +2)", "Rising Rapidly\n(v > +2.0)"]
    trend_keys = list(trend_results.keys())
    trend_hyb_mae = [trend_results[t]["models"]["Hybrid_Forecaster"]["MAE"] for t in trend_keys]
    trend_gru_mae = [trend_results[t]["models"]["Neural_GRU_V1"]["MAE"] for t in trend_keys]
    trend_ridge_mae = [trend_results[t]["models"]["Ridge"]["MAE"] for t in trend_keys]

    x_t = np.arange(len(trend_labels))
    axes[1].bar(x_t - 0.25, trend_ridge_mae, width=0.25, label="Ridge", color="#7f7f7f", alpha=0.85)
    axes[1].bar(x_t, trend_gru_mae, width=0.25, label="Neural GRU V1", color="#1f77b4", alpha=0.85)
    axes[1].bar(x_t + 0.25, trend_hyb_mae, width=0.25, label="GlucoShield Hybrid", color="#2ca02c", alpha=0.85)
    axes[1].set_xticks(x_t)
    axes[1].set_xticklabels(trend_labels, fontsize=9)
    axes[1].set_title("B. Forecast MAE by Glucose Velocity Trend (t=0)", fontsize=12, fontweight="bold")
    axes[1].set_ylabel("MAE (mg/dL)", fontsize=11)
    axes[1].legend(loc="upper left", frameon=True)

    plt.tight_layout()
    fig3_path = os.path.join(OUT_FIG_DIR, "fig3_clinical_range_and_trends.png")
    plt.savefig(fig3_path, dpi=300)
    plt.close()
    print(f"  Saved Figure 3 to: {fig3_path}")
    print("=" * 80)

if __name__ == "__main__":
    main()
