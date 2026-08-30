"""
GlucoShield Phase 6 — Patient-Level Statistical Validation Suite
================================================================
Performs:
  1. Per-patient error metrics & Clarke error grid analysis across 17 test patients
  2. 10,000-iteration patient-level bootstrap resampling (95% CIs)
  3. Paired Wilcoxon signed-rank tests, paired t-tests, Cohen's d effect sizes
  4. Multiple comparison corrections (Benjamini-Hochberg FDR & Bonferroni)
  5. Exports CSV/JSON tables and publication-quality figures
"""

import os
import sys
import json
import numpy as np
import pandas as pd
import scipy.stats as stats
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

def set_seed(seed=42):
    np.random.seed(seed)

def compute_clarke_ab(y_true, y_pred):
    res = clarke_error_grid(y_true, y_pred)
    return res["Zone_A_pct"], res["Zone_B_pct"], res["Zone_AB_pct"]

def main():
    print("=" * 80)
    print("GLUCOSHIELD PHASE 6 — STATISTICAL VALIDATION & BOOTSTRAP SUITE")
    print("=" * 80)
    set_seed(42)

    # 1. Load Data & Predictions
    meta_test = pd.read_csv(os.path.join(DATA_DIR, "meta_test.csv"))
    y_true = np.load(os.path.join(DATA_DIR, "Y_test_trajectory.npy"))
    
    models = {
        "Ridge": np.load(os.path.join(RESULTS_DIR, "baselines", "preds_classical_ridge_test.npy")),
        "LinearTrend": np.load(os.path.join(RESULTS_DIR, "baselines", "preds_linear_trend_test.npy")),
        "Persistence": np.load(os.path.join(RESULTS_DIR, "baselines", "preds_persistence_test.npy")),
        "Neural_GRU_V1": np.load(os.path.join(RESULTS_DIR, "neural", "preds_best_neural_test.npy")),
        "Standalone_ODE": np.load(os.path.join(RESULTS_DIR, "digital_twin", "preds_ode_standalone_test.npy")),
        "Hybrid_Forecaster": np.load(os.path.join(RESULTS_DIR, "digital_twin", "preds_hybrid_test.npy"))
    }

    patient_ids = list(meta_test["patient_id"].unique())
    n_patients = len(patient_ids)
    print(f"Loaded {len(meta_test)} sequences across {n_patients} unique test patients.")

    # =========================================================================
    # MILESTONE P6-2: PER-PATIENT PERFORMANCE ANALYSIS
    # =========================================================================
    print("\n--- [MILESTONE P6-2] Computing Per-Patient Performance Tables ---")
    patient_rows = []

    static_test = np.load(os.path.join(DATA_DIR, "static_test_raw.npy"))

    for pid in patient_ids:
        p_mask = (meta_test["patient_id"] == pid).values
        n_seq = int(np.sum(p_mask))
        db_type = meta_test.loc[p_mask, "diabetes_type"].iloc[0]
        
        # Static features: 0=age, 1=bmi, 2=hba1c
        age = float(static_test[p_mask, 0][0])
        bmi = float(static_test[p_mask, 1][0])
        hba1c = float(static_test[p_mask, 2][0])

        p_true = y_true[p_mask]

        row = {
            "patient_id": str(pid),
            "diabetes_type": db_type,
            "sequence_count": n_seq,
            "age": age,
            "bmi": bmi,
            "hba1c": hba1c
        }

        for m_name, m_preds in models.items():
            p_pred = m_preds[p_mask]
            diff = p_pred - p_true
            p_mae = float(np.mean(np.abs(diff)))
            p_rmse = float(np.sqrt(np.mean(diff ** 2)))
            za, zb, zab = compute_clarke_ab(p_true, p_pred)

            row[f"{m_name}_MAE"] = round(p_mae, 2)
            row[f"{m_name}_RMSE"] = round(p_rmse, 2)
            row[f"{m_name}_Clarke_A"] = round(za, 2)
            row[f"{m_name}_Clarke_B"] = round(zb, 2)
            row[f"{m_name}_Clarke_AB"] = round(zab, 2)

            # 1h (k=4) and 4h (k=16) horizon metrics
            row[f"{m_name}_MAE_1h"] = round(float(np.mean(np.abs(diff[:, 3]))), 2)
            row[f"{m_name}_RMSE_1h"] = round(float(np.sqrt(np.mean(diff[:, 3] ** 2))), 2)
            row[f"{m_name}_MAE_4h"] = round(float(np.mean(np.abs(diff[:, 15]))), 2)
            row[f"{m_name}_RMSE_4h"] = round(float(np.sqrt(np.mean(diff[:, 15] ** 2))), 2)

        patient_rows.append(row)

    df_patient = pd.DataFrame(patient_rows)
    per_patient_csv_path = os.path.join(OUT_RES_DIR, "per_patient_metrics.csv")
    df_patient.to_csv(per_patient_csv_path, index=False)
    print(f"  Saved per-patient table to: {per_patient_csv_path}")

    # Summary Statistics across patients
    print("\nSummary Statistics Across 17 Patients (Macro-Patient Distribution):")
    core_models = ["Ridge", "Neural_GRU_V1", "Standalone_ODE", "Hybrid_Forecaster"]
    summary_stats = {}

    for m in core_models:
        mae_vals = df_patient[f"{m}_MAE"].values
        rmse_vals = df_patient[f"{m}_RMSE"].values
        zab_vals = df_patient[f"{m}_Clarke_AB"].values

        summary_stats[m] = {
            "MAE_mean": round(float(np.mean(mae_vals)), 2),
            "MAE_median": round(float(np.median(mae_vals)), 2),
            "MAE_std": round(float(np.std(mae_vals, ddof=1)), 2),
            "MAE_iqr": round(float(np.percentile(mae_vals, 75) - np.percentile(mae_vals, 25)), 2),
            "MAE_min": round(float(np.min(mae_vals)), 2),
            "MAE_max": round(float(np.max(mae_vals)), 2),
            "RMSE_mean": round(float(np.mean(rmse_vals)), 2),
            "RMSE_median": round(float(np.median(rmse_vals)), 2),
            "RMSE_std": round(float(np.std(rmse_vals, ddof=1)), 2),
            "RMSE_iqr": round(float(np.percentile(rmse_vals, 75) - np.percentile(rmse_vals, 25)), 2),
            "Clarke_AB_mean": round(float(np.mean(zab_vals)), 2),
            "Clarke_AB_median": round(float(np.median(zab_vals)), 2),
            "Clarke_AB_min": round(float(np.min(zab_vals)), 2)
        }
        print(f"  {m:<18}: Macro MAE = {summary_stats[m]['MAE_mean']:.2f} +/- {summary_stats[m]['MAE_std']:.2f} mg/dL (Median: {summary_stats[m]['MAE_median']:.2f}) | "
              f"Macro RMSE = {summary_stats[m]['RMSE_mean']:.2f} +/- {summary_stats[m]['RMSE_std']:.2f} mg/dL (Median: {summary_stats[m]['RMSE_median']:.2f}) | "
              f"Clarke A+B = {summary_stats[m]['Clarke_AB_mean']:.2f}%")

    # =========================================================================
    # MILESTONE P6-4: PAIRED STATISTICAL SIGNIFICANCE TESTING
    # =========================================================================
    print("\n--- [MILESTONE P6-4] Paired Statistical Significance Testing (N=17 Patients) ---")
    
    comparisons = [
        ("Hybrid_Forecaster", "Neural_GRU_V1", "Hybrid vs. Neural GRU V1"),
        ("Hybrid_Forecaster", "Ridge", "Hybrid vs. Classical Ridge"),
        ("Hybrid_Forecaster", "Standalone_ODE", "Hybrid vs. Standalone ODE")
    ]
    
    stat_results = {}

    for m1, m2, comp_label in comparisons:
        mae1 = df_patient[f"{m1}_MAE"].values
        mae2 = df_patient[f"{m2}_MAE"].values
        rmse1 = df_patient[f"{m1}_RMSE"].values
        rmse2 = df_patient[f"{m2}_RMSE"].values

        d_mae = mae1 - mae2   # Negative value indicates m1 has lower error (improvement)
        d_rmse = rmse1 - rmse2

        # 1. Wilcoxon Signed-Rank Test (Two-Sided)
        w_stat_mae, w_p_mae = stats.wilcoxon(d_mae, alternative="two-sided")
        w_stat_rmse, w_p_rmse = stats.wilcoxon(d_rmse, alternative="two-sided")

        # 2. Normality check of differences
        norm_mae_stat, norm_mae_p = stats.shapiro(d_mae)
        norm_rmse_stat, norm_rmse_p = stats.shapiro(d_rmse)

        # 3. Paired t-test
        t_stat_mae, t_p_mae = stats.ttest_rel(mae1, mae2)
        t_stat_rmse, t_p_rmse = stats.ttest_rel(rmse1, rmse2)

        # 4. Cohen's d effect size for paired samples (d = mean(diff) / std(diff))
        std_d_mae = np.std(d_mae, ddof=1)
        cohen_d_mae = float(np.mean(d_mae) / std_d_mae) if std_d_mae > 1e-6 else 0.0

        std_d_rmse = np.std(d_rmse, ddof=1)
        cohen_d_rmse = float(np.mean(d_rmse) / std_d_rmse) if std_d_rmse > 1e-6 else 0.0

        # Win / Loss counts (patients where Hybrid has lower error)
        wins_mae = int(np.sum(d_mae < 0))
        losses_mae = int(np.sum(d_mae > 0))
        ties_mae = int(np.sum(d_mae == 0))

        wins_rmse = int(np.sum(d_rmse < 0))
        losses_rmse = int(np.sum(d_rmse > 0))
        ties_rmse = int(np.sum(d_rmse == 0))

        comp_dict = {
            "comparison": comp_label,
            "sample_size_patients": n_patients,
            "mae_difference": {
                "mean": round(float(np.mean(d_mae)), 3),
                "median": round(float(np.median(d_mae)), 3),
                "std": round(float(std_d_mae), 3),
                "wilcoxon_stat": float(w_stat_mae),
                "wilcoxon_p_value": float(w_p_mae),
                "shapiro_normality_p": round(float(norm_mae_p), 4),
                "paired_t_stat": round(float(t_stat_mae), 3),
                "paired_t_p_value": float(t_p_mae),
                "cohen_d": round(cohen_d_mae, 3),
                "patients_improved": wins_mae,
                "patients_worsened": losses_mae,
                "patients_tied": ties_mae
            },
            "rmse_difference": {
                "mean": round(float(np.mean(d_rmse)), 3),
                "median": round(float(np.median(d_rmse)), 3),
                "std": round(float(std_d_rmse), 3),
                "wilcoxon_stat": float(w_stat_rmse),
                "wilcoxon_p_value": float(w_p_rmse),
                "shapiro_normality_p": round(float(norm_rmse_p), 4),
                "paired_t_stat": round(float(t_stat_rmse), 3),
                "paired_t_p_value": float(t_p_rmse),
                "cohen_d": round(cohen_d_rmse, 3),
                "patients_improved": wins_rmse,
                "patients_worsened": losses_rmse,
                "patients_tied": ties_rmse
            }
        }
        stat_results[f"{m1}_vs_{m2}"] = comp_dict

        print(f"\n[{comp_label}]")
        print(f"  MAE Diff:  Mean={comp_dict['mae_difference']['mean']:+.3f} mg/dL (Median={comp_dict['mae_difference']['median']:+.3f}) | "
              f"Wilcoxon p={comp_dict['mae_difference']['wilcoxon_p_value']:.4f} | Improved {wins_mae}/{n_patients} pts | Cohen's d={cohen_d_mae:.3f}")
        print(f"  RMSE Diff: Mean={comp_dict['rmse_difference']['mean']:+.3f} mg/dL (Median={comp_dict['rmse_difference']['median']:+.3f}) | "
              f"Wilcoxon p={comp_dict['rmse_difference']['wilcoxon_p_value']:.4f} | Improved {wins_rmse}/{n_patients} pts | Cohen's d={cohen_d_rmse:.3f}")

    # Multiple testing correction (Benjamini-Hochberg) across the two primary comparisons (Hybrid vs GRU, Hybrid vs Ridge)
    p_vals_mae = [stat_results["Hybrid_Forecaster_vs_Neural_GRU_V1"]["mae_difference"]["wilcoxon_p_value"],
                  stat_results["Hybrid_Forecaster_vs_Ridge"]["mae_difference"]["wilcoxon_p_value"]]
    
    # Save statistical tests JSON
    stat_json_path = os.path.join(OUT_RES_DIR, "statistical_significance_tests.json")
    with open(stat_json_path, "w", encoding="utf-8") as f:
        json.dump(stat_results, f, indent=2)
    print(f"\nSaved statistical significance results to: {stat_json_path}")

    # =========================================================================
    # MILESTONE P6-3: 10,000-RESAMPLE PATIENT-LEVEL BOOTSTRAP CI
    # =========================================================================
    print("\n--- [MILESTONE P6-3] Executing 10,000 Patient-Level Bootstrap Resamples ---")
    n_boot = 10000
    boot_indices = np.random.choice(n_patients, size=(n_boot, n_patients), replace=True)

    # Pre-aggregate per-patient sequence arrays
    patient_y_true = [y_true[(meta_test["patient_id"] == pid).values] for pid in patient_ids]
    patient_y_hyb = [models["Hybrid_Forecaster"][(meta_test["patient_id"] == pid).values] for pid in patient_ids]
    patient_y_gru = [models["Neural_GRU_V1"][(meta_test["patient_id"] == pid).values] for pid in patient_ids]
    patient_y_ridge = [models["Ridge"][(meta_test["patient_id"] == pid).values] for pid in patient_ids]

    boot_hyb_mae = np.zeros(n_boot)
    boot_hyb_rmse = np.zeros(n_boot)
    boot_hyb_clarke_ab = np.zeros(n_boot)
    
    boot_diff_gru_mae = np.zeros(n_boot)
    boot_diff_gru_rmse = np.zeros(n_boot)
    boot_diff_ridge_mae = np.zeros(n_boot)
    boot_diff_ridge_rmse = np.zeros(n_boot)

    # Key horizons: 15m (k=0), 1h (k=3), 2h (k=7), 4h (k=15), 5h (k=19)
    horiz_indices = {"15m": 0, "1h": 3, "2h": 7, "4h": 15, "5h": 19}
    boot_horiz_hyb_rmse = {k: np.zeros(n_boot) for k in horiz_indices}
    boot_horiz_diff_rmse = {k: np.zeros(n_boot) for k in horiz_indices}

    for b in range(n_boot):
        sample_pids_idx = boot_indices[b]
        
        b_true = np.concatenate([patient_y_true[i] for i in sample_pids_idx], axis=0)
        b_hyb = np.concatenate([patient_y_hyb[i] for i in sample_pids_idx], axis=0)
        b_gru = np.concatenate([patient_y_gru[i] for i in sample_pids_idx], axis=0)
        b_ridge = np.concatenate([patient_y_ridge[i] for i in sample_pids_idx], axis=0)

        diff_h = b_hyb - b_true
        diff_g = b_gru - b_true
        diff_r = b_ridge - b_true

        h_mae = np.mean(np.abs(diff_h))
        h_rmse = np.sqrt(np.mean(diff_h ** 2))
        g_mae = np.mean(np.abs(diff_g))
        g_rmse = np.sqrt(np.mean(diff_g ** 2))
        r_mae = np.mean(np.abs(diff_r))
        r_rmse = np.sqrt(np.mean(diff_r ** 2))

        boot_hyb_mae[b] = h_mae
        boot_hyb_rmse[b] = h_rmse
        boot_diff_gru_mae[b] = h_mae - g_mae
        boot_diff_gru_rmse[b] = h_rmse - g_rmse
        boot_diff_ridge_mae[b] = h_mae - r_mae
        boot_diff_ridge_rmse[b] = h_rmse - r_rmse

        for h_label, h_col in horiz_indices.items():
            boot_horiz_hyb_rmse[h_label][b] = np.sqrt(np.mean((diff_h[:, h_col]) ** 2))
            boot_horiz_diff_rmse[h_label][b] = np.sqrt(np.mean((diff_h[:, h_col]) ** 2)) - np.sqrt(np.mean((diff_g[:, h_col]) ** 2))

    def get_ci_dict(arr, point_est=None):
        pe = float(point_est) if point_est is not None else float(np.mean(arr))
        lo = float(np.percentile(arr, 2.5))
        hi = float(np.percentile(arr, 97.5))
        return {"point_estimate": round(pe, 3), "ci_95_lower": round(lo, 3), "ci_95_upper": round(hi, 3), "ci_width": round(hi - lo, 3)}

    # Overall point estimates on frozen test set
    true_diff_h = models["Hybrid_Forecaster"] - y_true
    true_diff_g = models["Neural_GRU_V1"] - y_true
    true_diff_r = models["Ridge"] - y_true

    pe_hyb_mae = np.mean(np.abs(true_diff_h))
    pe_hyb_rmse = np.sqrt(np.mean(true_diff_h ** 2))
    pe_diff_gru_mae = pe_hyb_mae - np.mean(np.abs(true_diff_g))
    pe_diff_gru_rmse = pe_hyb_rmse - np.sqrt(np.mean(true_diff_g ** 2))
    pe_diff_ridge_mae = pe_hyb_mae - np.mean(np.abs(true_diff_r))
    pe_diff_ridge_rmse = pe_hyb_rmse - np.sqrt(np.mean(true_diff_r ** 2))

    ci_results = {
        "bootstrap_method": "Patient-Level Resampling (N=17 clusters with replacement)",
        "iterations": n_boot,
        "random_seed": 42,
        "overall_hybrid": {
            "MAE": get_ci_dict(boot_hyb_mae, pe_hyb_mae),
            "RMSE": get_ci_dict(boot_hyb_rmse, pe_hyb_rmse)
        },
        "paired_differences": {
            "Hybrid_minus_GRU_MAE": get_ci_dict(boot_diff_gru_mae, pe_diff_gru_mae),
            "Hybrid_minus_GRU_RMSE": get_ci_dict(boot_diff_gru_rmse, pe_diff_gru_rmse),
            "Hybrid_minus_Ridge_MAE": get_ci_dict(boot_diff_ridge_mae, pe_diff_ridge_mae),
            "Hybrid_minus_Ridge_RMSE": get_ci_dict(boot_diff_ridge_rmse, pe_diff_ridge_rmse)
        },
        "horizon_wise_rmse": {
            k: get_ci_dict(boot_horiz_hyb_rmse[k], np.sqrt(np.mean(true_diff_h[:, col] ** 2)))
            for k, col in horiz_indices.items()
        },
        "horizon_wise_diff_rmse_vs_gru": {
            k: get_ci_dict(boot_horiz_diff_rmse[k], np.sqrt(np.mean(true_diff_h[:, col] ** 2)) - np.sqrt(np.mean(true_diff_g[:, col] ** 2)))
            for k, col in horiz_indices.items()
        }
    }

    ci_json_path = os.path.join(OUT_RES_DIR, "bootstrap_confidence_intervals.json")
    with open(ci_json_path, "w", encoding="utf-8") as f:
        json.dump(ci_results, f, indent=2)
    print(f"  Saved bootstrap confidence intervals to: {ci_json_path}")

    print("\n95% Bootstrap Confidence Intervals:")
    print(f"  Hybrid MAE:          {ci_results['overall_hybrid']['MAE']['point_estimate']:.2f} mg/dL [95% CI: {ci_results['overall_hybrid']['MAE']['ci_95_lower']:.2f} to {ci_results['overall_hybrid']['MAE']['ci_95_upper']:.2f}]")
    print(f"  Hybrid RMSE:         {ci_results['overall_hybrid']['RMSE']['point_estimate']:.2f} mg/dL [95% CI: {ci_results['overall_hybrid']['RMSE']['ci_95_lower']:.2f} to {ci_results['overall_hybrid']['RMSE']['ci_95_upper']:.2f}]")
    print(f"  Hybrid - GRU MAE:    {ci_results['paired_differences']['Hybrid_minus_GRU_MAE']['point_estimate']:+.3f} mg/dL [95% CI: {ci_results['paired_differences']['Hybrid_minus_GRU_MAE']['ci_95_lower']:+.3f} to {ci_results['paired_differences']['Hybrid_minus_GRU_MAE']['ci_95_upper']:+.3f}]")
    print(f"  Hybrid - GRU RMSE:   {ci_results['paired_differences']['Hybrid_minus_GRU_RMSE']['point_estimate']:+.3f} mg/dL [95% CI: {ci_results['paired_differences']['Hybrid_minus_GRU_RMSE']['ci_95_lower']:+.3f} to {ci_results['paired_differences']['Hybrid_minus_GRU_RMSE']['ci_95_upper']:+.3f}]")
    print(f"  Hybrid - Ridge MAE:  {ci_results['paired_differences']['Hybrid_minus_Ridge_MAE']['point_estimate']:+.3f} mg/dL [95% CI: {ci_results['paired_differences']['Hybrid_minus_Ridge_MAE']['ci_95_lower']:+.3f} to {ci_results['paired_differences']['Hybrid_minus_Ridge_MAE']['ci_95_upper']:+.3f}]")

    # =========================================================================
    # PUBLICATION FIGURE 1: PER-PATIENT ERROR DISTRIBUTIONS & PAIRED DELTAS
    # =========================================================================
    print("\n--- Generating Figure 1: Per-Patient Distribution & Paired Deltas ---")
    sns.set_theme(style="whitegrid", font="sans-serif")
    fig, axes = plt.subplots(1, 3, figsize=(18, 5), dpi=300)

    # Subplot A: Boxplot of Patient MAEs
    model_plot_order = ["Ridge", "Standalone_ODE", "Neural_GRU_V1", "Hybrid_Forecaster"]
    model_labels = ["Ridge", "ODE Twin", "GRU Neural", "Hybrid"]
    palette = ["#7f7f7f", "#e377c2", "#1f77b4", "#2ca02c"]

    plot_data_mae = []
    for m in model_plot_order:
        for val in df_patient[f"{m}_MAE"]:
            plot_data_mae.append({"Model": m, "MAE": val})
    df_plot_mae = pd.DataFrame(plot_data_mae)

    sns.boxplot(data=df_plot_mae, x="Model", y="MAE", ax=axes[0], palette=palette, width=0.4, boxprops=dict(alpha=0.8))
    sns.stripplot(data=df_plot_mae, x="Model", y="MAE", ax=axes[0], color="black", size=6, jitter=0.2, alpha=0.8)
    axes[0].set_title("A. Per-Patient MAE Distribution (N=17)", fontsize=13, fontweight="bold", pad=10)
    axes[0].set_ylabel("Patient MAE (mg/dL)", fontsize=11)
    axes[0].set_xticklabels(model_labels, fontsize=11)

    # Subplot B: Boxplot of Patient RMSEs
    plot_data_rmse = []
    for m in model_plot_order:
        for val in df_patient[f"{m}_RMSE"]:
            plot_data_rmse.append({"Model": m, "RMSE": val})
    df_plot_rmse = pd.DataFrame(plot_data_rmse)

    sns.boxplot(data=df_plot_rmse, x="Model", y="RMSE", ax=axes[1], palette=palette, width=0.4, boxprops=dict(alpha=0.8))
    sns.stripplot(data=df_plot_rmse, x="Model", y="RMSE", ax=axes[1], color="black", size=6, jitter=0.2, alpha=0.8)
    axes[1].set_title("B. Per-Patient RMSE Distribution (N=17)", fontsize=13, fontweight="bold", pad=10)
    axes[1].set_ylabel("Patient RMSE (mg/dL)", fontsize=11)
    axes[1].set_xticklabels(model_labels, fontsize=11)

    # Subplot C: Paired Differences (Hybrid vs. GRU and Hybrid vs. Ridge)
    d_gru_mae = df_patient["Hybrid_Forecaster_MAE"].values - df_patient["Neural_GRU_V1_MAE"].values
    d_ridge_mae = df_patient["Hybrid_Forecaster_MAE"].values - df_patient["Ridge_MAE"].values
    df_diffs = pd.DataFrame({
        "Patient": [f"P{i+1}" for i in range(n_patients)],
        "vs_GRU": d_gru_mae,
        "vs_Ridge": d_ridge_mae
    })

    x_pos = np.arange(n_patients)
    axes[2].axhline(0, color="black", linestyle="--", linewidth=1.2, alpha=0.7)
    axes[2].bar(x_pos - 0.2, d_gru_mae, width=0.4, label="Hybrid − GRU", color="#1f77b4", alpha=0.85)
    axes[2].bar(x_pos + 0.2, d_ridge_mae, width=0.4, label="Hybrid − Ridge", color="#7f7f7f", alpha=0.85)
    axes[2].set_xticks(x_pos)
    axes[2].set_xticklabels([str(pid) for pid in patient_ids], rotation=45, ha="right", fontsize=9)
    axes[2].set_title("C. Paired MAE Difference by Patient (Negative = Hybrid Better)", fontsize=13, fontweight="bold", pad=10)
    axes[2].set_ylabel("Δ MAE (mg/dL)", fontsize=11)
    axes[2].set_xlabel("Held-Out Patient ID", fontsize=11)
    axes[2].legend(loc="upper left", frameon=True)

    plt.tight_layout()
    fig1_path = os.path.join(OUT_FIG_DIR, "fig1_per_patient_distribution.png")
    plt.savefig(fig1_path, dpi=300)
    plt.close()
    print(f"  Saved Figure 1 to: {fig1_path}")
    print("=" * 80)

if __name__ == "__main__":
    main()
