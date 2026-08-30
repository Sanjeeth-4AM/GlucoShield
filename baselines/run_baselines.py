"""
GlucoShield Baseline Execution & Benchmarking Pipeline
Orchestrates validation tuning, freezes best configurations, evaluates on test set, and saves results.
"""

import os
import sys
import json
import numpy as np
import pandas as pd

# Add repository root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from baselines.persistence import PersistenceForecaster
from baselines.linear_trend import LinearTrendForecaster
from baselines.classical_ml import ClassicalMLForecaster
from baselines.risk_baselines import evaluate_risk_predictions
from baselines.evaluate_baselines import evaluate_trajectory, format_metric_table

def run_all_baselines():
    print("================================================================================")
    print("GLUCOSHIELD: SCIENTIFIC BASELINE BENCHMARKING ENGINE")
    print("================================================================================")

    base_dir = "D:/ML PROJECT"
    final_dir = os.path.join(base_dir, "data", "final")
    results_dir = os.path.join(base_dir, "results", "baselines")
    os.makedirs(results_dir, exist_ok=True)

    # 1. Load Data
    print("\n--- LOADING DATASET V1.0 TENSORS ---")
    X_train_raw = np.load(os.path.join(final_dir, "X_train_raw.npy"))
    static_train_raw = np.load(os.path.join(final_dir, "static_train_raw.npy"))
    Y_train_traj = np.load(os.path.join(final_dir, "Y_train_trajectory.npy"))

    X_val_raw = np.load(os.path.join(final_dir, "X_val_raw.npy"))
    static_val_raw = np.load(os.path.join(final_dir, "static_val_raw.npy"))
    Y_val_traj = np.load(os.path.join(final_dir, "Y_val_trajectory.npy"))
    meta_val = pd.read_csv(os.path.join(final_dir, "meta_val.csv"))

    X_test_raw = np.load(os.path.join(final_dir, "X_test_raw.npy"))
    static_test_raw = np.load(os.path.join(final_dir, "static_test_raw.npy"))
    Y_test_traj = np.load(os.path.join(final_dir, "Y_test_trajectory.npy"))
    meta_test = pd.read_csv(os.path.join(final_dir, "meta_test.csv"))

    val_risk_targets = {
        "hypo_1h": np.load(os.path.join(final_dir, "Y_val_hypo_1h.npy")),
        "hypo_2h": np.load(os.path.join(final_dir, "Y_val_hypo_2h.npy")),
        "hypo_4h": np.load(os.path.join(final_dir, "Y_val_hypo_4h.npy")),
        "hyper_2h": np.load(os.path.join(final_dir, "Y_val_hyper_2h.npy")),
        "hyper_4h": np.load(os.path.join(final_dir, "Y_val_hyper_4h.npy")),
    }

    test_risk_targets = {
        "hypo_1h": np.load(os.path.join(final_dir, "Y_test_hypo_1h.npy")),
        "hypo_2h": np.load(os.path.join(final_dir, "Y_test_hypo_2h.npy")),
        "hypo_4h": np.load(os.path.join(final_dir, "Y_test_hypo_4h.npy")),
        "hyper_2h": np.load(os.path.join(final_dir, "Y_test_hyper_2h.npy")),
        "hyper_4h": np.load(os.path.join(final_dir, "Y_test_hyper_4h.npy")),
    }

    print(f"Loaded Train ({len(X_train_raw)}), Val ({len(X_val_raw)}), Test ({len(X_test_raw)}) successfully.")

    # 2. BASELINE A: Naive Persistence
    print("\n================================================================================")
    print("BASELINE A: NAIVE PERSISTENCE FORECASTER")
    print("================================================================================")
    persist_model = PersistenceForecaster(horizon=20)
    persist_val_preds = persist_model.predict(X_val_raw)
    persist_test_preds = persist_model.predict(X_test_raw)

    persist_val_res = evaluate_trajectory(persist_val_preds, Y_val_traj, meta_val)
    persist_test_res = evaluate_trajectory(persist_test_preds, Y_test_traj, meta_test)
    persist_test_risk = evaluate_risk_predictions(persist_test_preds, test_risk_targets)

    print("[Validation Set Performance]")
    print(format_metric_table(persist_val_res))
    print("\n[Test Set Performance]")
    print(format_metric_table(persist_test_res))

    # 3. BASELINE B: Linear Trend Forecaster (Validation Selection)
    print("\n================================================================================")
    print("BASELINE B: CAUSAL LINEAR TREND FORECASTER (VAL SELECTION)")
    print("================================================================================")
    lookback_options = [4, 8, 16]  # 1h (4 steps), 2h (8 steps), 4h (16 steps)
    best_lookback = None
    best_val_rmse = float("inf")
    trend_val_results = {}

    for lb in lookback_options:
        lt_model = LinearTrendForecaster(lookback_steps=lb, horizon=20)
        lt_val_pred = lt_model.predict(X_val_raw)
        eval_lt_val = evaluate_trajectory(lt_val_pred, Y_val_traj, meta_val)
        val_rmse = eval_lt_val["overall"]["RMSE"]
        val_mae = eval_lt_val["overall"]["MAE"]
        trend_val_results[lb] = eval_lt_val
        print(f"  Lookback {lb:>2} steps ({lb*15:>3} min) -> Val MAE: {val_mae:.2f} mg/dL | Val RMSE: {val_rmse:.2f} mg/dL")
        if val_rmse < best_val_rmse:
            best_val_rmse = val_rmse
            best_lookback = lb

    print(f"\n--> Selected Best Lookback (on Validation ONLY): {best_lookback} steps ({best_lookback*15} min) with Val RMSE = {best_val_rmse:.2f} mg/dL")
    
    # Freeze best configuration and evaluate on test
    best_lt_model = LinearTrendForecaster(lookback_steps=best_lookback, horizon=20)
    lt_val_preds = best_lt_model.predict(X_val_raw)
    lt_test_preds = best_lt_model.predict(X_test_raw)
    lt_val_res = evaluate_trajectory(lt_val_preds, Y_val_traj, meta_val)
    lt_test_res = evaluate_trajectory(lt_test_preds, Y_test_traj, meta_test)
    lt_test_risk = evaluate_risk_predictions(lt_test_preds, test_risk_targets)

    print("\n[Frozen Best Linear Trend Test Performance]")
    print(format_metric_table(lt_test_res))

    # 4. BASELINE C: Classical ML Forecaster (Validation Tuning)
    print("\n================================================================================")
    print("BASELINE C: CLASSICAL MACHINE LEARNING (RIDGE REGRESSION)")
    print("================================================================================")
    alpha_candidates = [0.01, 0.1, 1.0, 10.0, 100.0, 1000.0, 10000.0]
    best_alpha = None
    best_cml_val_rmse = float("inf")
    cml_val_results = {}

    for alpha in alpha_candidates:
        cml = ClassicalMLForecaster(model_type="ridge", alpha=alpha, horizon=20)
        cml.fit(X_train_raw, Y_train_traj, static_train_raw)
        cml_val_pred = cml.predict(X_val_raw, static_val_raw)
        eval_cml_val = evaluate_trajectory(cml_val_pred, Y_val_traj, meta_val)
        val_rmse = eval_cml_val["overall"]["RMSE"]
        val_mae = eval_cml_val["overall"]["MAE"]
        cml_val_results[alpha] = eval_cml_val
        print(f"  Ridge alpha={alpha:>7.2f} -> Val MAE: {val_mae:.2f} mg/dL | Val RMSE: {val_rmse:.2f} mg/dL")
        if val_rmse < best_cml_val_rmse:
            best_cml_val_rmse = val_rmse
            best_alpha = alpha

    print(f"\n--> Selected Best Alpha (on Validation ONLY): alpha={best_alpha} with Val RMSE = {best_cml_val_rmse:.2f} mg/dL")

    # Fit best Ridge model and evaluate on test
    best_cml_model = ClassicalMLForecaster(model_type="ridge", alpha=best_alpha, horizon=20)
    best_cml_model.fit(X_train_raw, Y_train_traj, static_train_raw)
    cml_val_preds = best_cml_model.predict(X_val_raw, static_val_raw)
    cml_test_preds = best_cml_model.predict(X_test_raw, static_test_raw)
    cml_val_res = evaluate_trajectory(cml_val_preds, Y_val_traj, meta_val)
    cml_test_res = evaluate_trajectory(cml_test_preds, Y_test_traj, meta_test)
    cml_test_risk = evaluate_risk_predictions(cml_test_preds, test_risk_targets)

    print("\n[Frozen Best Classical ML Test Performance]")
    print(format_metric_table(cml_test_res))

    # 5. Save Raw Predictions
    print("\n--- SAVING BASELINE ARTIFACTS ---")
    np.save(os.path.join(results_dir, "preds_persistence_test.npy"), persist_test_preds)
    np.save(os.path.join(results_dir, "preds_linear_trend_test.npy"), lt_test_preds)
    np.save(os.path.join(results_dir, "preds_classical_ridge_test.npy"), cml_test_preds)

    # 6. Build Consolidated Comparison Tables
    models_eval = {
        "Persistence": {
            "val_overall": persist_val_res["overall"],
            "test_overall": persist_test_res["overall"],
            "test_macro_patient": persist_test_res["macro_patient"],
            "test_subgroups": persist_test_res["subgroups"],
            "test_horizons": persist_test_res["horizons"],
            "test_risk": persist_test_risk
        },
        "Linear_Trend": {
            "val_overall": lt_val_res["overall"],
            "test_overall": lt_test_res["overall"],
            "test_macro_patient": lt_test_res["macro_patient"],
            "test_subgroups": lt_test_res["subgroups"],
            "test_horizons": lt_test_res["horizons"],
            "test_risk": lt_test_risk,
            "selected_lookback_steps": best_lookback
        },
        "Classical_Ridge": {
            "val_overall": cml_val_res["overall"],
            "test_overall": cml_test_res["overall"],
            "test_macro_patient": cml_test_res["macro_patient"],
            "test_subgroups": cml_test_res["subgroups"],
            "test_horizons": cml_test_res["horizons"],
            "test_risk": cml_test_risk,
            "selected_alpha": best_alpha
        }
    }

    # Save summary JSON
    with open(os.path.join(results_dir, "baseline_summary.json"), "w") as f:
        json.dump(models_eval, f, indent=2)

    # Build CSVs
    # Horizon-wise comparison CSV
    horizon_rows = []
    for h_name in ["15min (k=1)", "30min (k=2)", "45min (k=3)", "1h (k=4)", "2h (k=8)", "3h (k=12)", "4h (k=16)", "5h (k=20)"]:
        row = {"horizon": h_name}
        for m_name in ["Persistence", "Linear_Trend", "Classical_Ridge"]:
            row[f"{m_name}_MAE"] = models_eval[m_name]["test_horizons"][h_name]["MAE"]
            row[f"{m_name}_RMSE"] = models_eval[m_name]["test_horizons"][h_name]["RMSE"]
            row[f"{m_name}_ZoneAB"] = models_eval[m_name]["test_horizons"][h_name]["Zone_AB_pct"]
        horizon_rows.append(row)
    pd.DataFrame(horizon_rows).to_csv(os.path.join(results_dir, "horizon_wise_metrics.csv"), index=False)

    # Subgroup CSV
    subgroup_rows = []
    for m_name in ["Persistence", "Linear_Trend", "Classical_Ridge"]:
        sg = models_eval[m_name]["test_subgroups"]
        subgroup_rows.append({
            "model": m_name,
            "Overall_MAE": models_eval[m_name]["test_overall"]["MAE"],
            "Overall_RMSE": models_eval[m_name]["test_overall"]["RMSE"],
            "Overall_ZoneAB": models_eval[m_name]["test_overall"]["Zone_AB_pct"],
            "T1DM_MAE": sg.get("T1DM", {}).get("MAE", np.nan),
            "T1DM_RMSE": sg.get("T1DM", {}).get("RMSE", np.nan),
            "T1DM_ZoneAB": sg.get("T1DM", {}).get("Zone_AB_pct", np.nan),
            "T2DM_MAE": sg.get("T2DM", {}).get("MAE", np.nan),
            "T2DM_RMSE": sg.get("T2DM", {}).get("RMSE", np.nan),
            "T2DM_ZoneAB": sg.get("T2DM", {}).get("Zone_AB_pct", np.nan),
            "Macro_Patient_MAE": models_eval[m_name]["test_macro_patient"]["macro_patient_mae_mean"],
            "Macro_Patient_RMSE": models_eval[m_name]["test_macro_patient"]["macro_patient_rmse_mean"]
        })
    pd.DataFrame(subgroup_rows).to_csv(os.path.join(results_dir, "subgroup_metrics.csv"), index=False)

    # Risk Metrics CSV
    risk_rows = []
    for m_name in ["Persistence", "Linear_Trend", "Classical_Ridge"]:
        rk = models_eval[m_name]["test_risk"]
        for ev_name, ev_metrics in rk.items():
            risk_rows.append({
                "model": m_name,
                "event": ev_name,
                "Prevalence": ev_metrics["Prevalence"],
                "Sensitivity": ev_metrics["Sensitivity"],
                "Specificity": ev_metrics["Specificity"],
                "Precision": ev_metrics["Precision"],
                "F1": ev_metrics["F1"],
                "Balanced_Accuracy": ev_metrics["Balanced_Accuracy"]
            })
    pd.DataFrame(risk_rows).to_csv(os.path.join(results_dir, "risk_metrics.csv"), index=False)

    # Per-Patient CSV
    patient_rows = []
    for m_name, res_dict in [("Persistence", persist_test_res), ("Linear_Trend", lt_test_res), ("Classical_Ridge", cml_test_res)]:
        for pid, pdata in res_dict["per_patient"].items():
            patient_rows.append({
                "model": m_name,
                "patient_id": pid,
                "diabetes_type": pdata["diabetes_type"],
                "num_sequences": pdata["num_sequences"],
                "MAE": pdata["MAE"],
                "RMSE": pdata["RMSE"]
            })
    pd.DataFrame(patient_rows).to_csv(os.path.join(results_dir, "per_patient_metrics.csv"), index=False)

    # 7. Print Final Comparison Table
    print("\n================================================================================")
    print("FINAL TEST BENCHMARK COMPARISON TABLE (DATASET V1.0 TEST SET)")
    print("================================================================================")
    df_comp = pd.DataFrame(subgroup_rows)
    print(df_comp[["model", "Overall_MAE", "Overall_RMSE", "T1DM_RMSE", "T2DM_RMSE", "Macro_Patient_RMSE", "Overall_ZoneAB"]].to_string(index=False))

    # Identify Best Baseline
    best_model_name = df_comp.sort_values("Overall_RMSE").iloc[0]["model"]
    best_model_rmse = df_comp.sort_values("Overall_RMSE").iloc[0]["Overall_RMSE"]
    best_model_mae = df_comp.sort_values("Overall_RMSE").iloc[0]["Overall_MAE"]
    print(f"\n>>> BEST BASELINE TO BEAT: {best_model_name} (Test RMSE: {best_model_rmse:.2f} mg/dL, Test MAE: {best_model_mae:.2f} mg/dL)")

    return models_eval

if __name__ == "__main__":
    run_all_baselines()
