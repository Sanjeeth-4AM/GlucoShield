"""
GlucoShield Staged Neural Experiment Runner & Validation-Only Model Selection Suite
Conducts staged validation search across GRU/LSTM architectures, capacity, optimization, loss weighting,
meal transforms, and ablations, then freezes the optimal model and evaluates on the test set.
"""

import os
import sys
import json
import time
import torch
import numpy as np
import pandas as pd

# Add repository root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
torch.set_num_threads(16)

from neural.models import GlucoShieldMultiTaskRNN
from neural.dataset import get_neural_dataloaders, compute_training_pos_weights
from neural.train import MultiTaskLoss, train_model, evaluate_model
from baselines.evaluate_baselines import evaluate_trajectory, clarke_error_grid

def set_seed(seed=42):
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)

def run_neural_experiments():
    print("================================================================================")
    print("GLUCOSHIELD: CORE NEURAL MULTI-TASK FORECASTER RESEARCH SUITE")
    print("================================================================================")

    base_dir = "D:/ML PROJECT"
    final_dir = os.path.join(base_dir, "data", "final")
    models_dir = os.path.join(base_dir, "models")
    results_dir = os.path.join(base_dir, "results", "neural")
    experiments_dir = os.path.join(base_dir, "experiments")
    for d in [models_dir, results_dir, experiments_dir]:
        os.makedirs(d, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Hardware execution device: {device} | Threads: {torch.get_num_threads()}")

    # 1. Load Data
    print("\n--- INITIALIZING IN-MEMORY DATASETS & POS_WEIGHTS ---")
    train_loader, val_loader, test_loader = get_neural_dataloaders(data_dir=final_dir, batch_size=256)
    pos_weights = compute_training_pos_weights(data_dir=final_dir).to(device)
    print(f"Training risk positive class weights (smoothed): {pos_weights.cpu().numpy().round(2)}")

    meta_val = pd.read_csv(os.path.join(final_dir, "meta_val.csv"))
    meta_test = pd.read_csv(os.path.join(final_dir, "meta_test.csv"))
    Y_test_traj = np.load(os.path.join(final_dir, "Y_test_trajectory.npy"))

    experiment_log = []

    # ============================================================================
    # STAGE 1: ARCHITECTURE COMPARISON (GRU vs LSTM)
    # ============================================================================
    print("\n================================================================================")
    print("STAGE 1: ARCHITECTURE COMPARISON (GRU vs LSTM)")
    print("================================================================================")
    stage1_results = {}
    for cell in ["gru", "lstm"]:
        set_seed(42)
        print(f"\nTraining {cell.upper()} baseline (hidden=64, layers=1, dropout=0.2, lr=1e-3)...")
        model = GlucoShieldMultiTaskRNN(
            cell_type=cell,
            dynamic_dim=22,
            static_dim=9,
            hidden_dim=64,
            num_layers=1,
            dropout=0.2,
            use_static=True,
            meal_c_max=200.0
        ).to(device)

        loss_fn = MultiTaskLoss(traj_loss_type="huber", lambda_traj=1.0, lambda_risk=5.0, pos_weights=pos_weights)
        res = train_model(model, train_loader, val_loader, meta_val, device, loss_fn, lr=1e-3, max_epochs=8, patience=3, verbose=True)

        val_rmse = res["best_val_eval"]["trajectory"]["overall"]["RMSE"]
        val_mae = res["best_val_eval"]["trajectory"]["overall"]["MAE"]
        hypo4_auprc = res["best_val_eval"]["risk"]["hypo_4h"]["AUPRC"]
        hypo4_sens = res["best_val_eval"]["risk"]["hypo_4h"]["Sensitivity"]
        print(f"--> {cell.upper()} Best Val RMSE: {val_rmse:.2f} mg/dL | Val MAE: {val_mae:.2f} mg/dL | Hypo4h AUPRC: {hypo4_auprc:.3f} | Hypo4h Sens: {hypo4_sens*100:.1f}%")

        stage1_results[cell] = {
            "val_rmse": val_rmse,
            "val_mae": val_mae,
            "hypo4_auprc": hypo4_auprc,
            "hypo4_sens": hypo4_sens,
            "res": res
        }
        experiment_log.append({
            "stage": 1,
            "name": f"Stage1_{cell.upper()}_base",
            "val_rmse": val_rmse,
            "val_mae": val_mae,
            "hypo4_auprc": hypo4_auprc
        })

    best_cell = "gru" if stage1_results["gru"]["val_rmse"] <= stage1_results["lstm"]["val_rmse"] else "lstm"
    print(f"\n>>> STAGE 1 WINNER (Validation ONLY): {best_cell.upper()} (Val RMSE = {stage1_results[best_cell]['val_rmse']:.2f} mg/dL)")

    # ============================================================================
    # STAGE 2: CAPACITY TUNING FOR WINNING CELL TYPE
    # ============================================================================
    print("\n================================================================================")
    print(f"STAGE 2: CAPACITY TUNING ({best_cell.upper()})")
    print("================================================================================")
    capacity_grid = [
        {"hidden": 64, "layers": 1, "dropout": 0.2},
        {"hidden": 96, "layers": 1, "dropout": 0.2},
        {"hidden": 128, "layers": 1, "dropout": 0.2},
        {"hidden": 64, "layers": 2, "dropout": 0.2},
        {"hidden": 96, "layers": 1, "dropout": 0.1},
        {"hidden": 96, "layers": 1, "dropout": 0.3}
    ]
    best_cap = None
    best_cap_rmse = float("inf")
    stage2_results = {}

    for cap in capacity_grid:
        cfg_name = f"h{cap['hidden']}_l{cap['layers']}_d{cap['dropout']}"
        set_seed(42)
        model = GlucoShieldMultiTaskRNN(
            cell_type=best_cell,
            dynamic_dim=22,
            static_dim=9,
            hidden_dim=cap["hidden"],
            num_layers=cap["layers"],
            dropout=cap["dropout"],
            use_static=True,
            meal_c_max=200.0
        ).to(device)

        loss_fn = MultiTaskLoss(traj_loss_type="huber", lambda_traj=1.0, lambda_risk=5.0, pos_weights=pos_weights)
        res = train_model(model, train_loader, val_loader, meta_val, device, loss_fn, lr=1e-3, max_epochs=8, patience=3, verbose=False)

        val_rmse = res["best_val_eval"]["trajectory"]["overall"]["RMSE"]
        val_mae = res["best_val_eval"]["trajectory"]["overall"]["MAE"]
        hypo4_auprc = res["best_val_eval"]["risk"]["hypo_4h"]["AUPRC"]
        print(f"  {cfg_name:<16} -> Val RMSE: {val_rmse:.2f} mg/dL | Val MAE: {val_mae:.2f} mg/dL | Hypo4h AUPRC: {hypo4_auprc:.3f}")

        stage2_results[cfg_name] = {"val_rmse": val_rmse, "val_mae": val_mae, "res": res}
        experiment_log.append({
            "stage": 2,
            "name": f"Stage2_{best_cell.upper()}_{cfg_name}",
            "val_rmse": val_rmse,
            "val_mae": val_mae,
            "hypo4_auprc": hypo4_auprc
        })

        if val_rmse < best_cap_rmse:
            best_cap_rmse = val_rmse
            best_cap = cap

    print(f"\n>>> STAGE 2 WINNER (Validation ONLY): hidden={best_cap['hidden']}, layers={best_cap['layers']}, dropout={best_cap['dropout']} (Val RMSE = {best_cap_rmse:.2f} mg/dL)")

    # ============================================================================
    # STAGE 3: OPTIMIZATION TUNING
    # ============================================================================
    print("\n================================================================================")
    print("STAGE 3: OPTIMIZATION TUNING (LR & WEIGHT DECAY)")
    print("================================================================================")
    opt_grid = [
        {"lr": 2e-3, "wd": 1e-4},
        {"lr": 1e-3, "wd": 1e-4},
        {"lr": 5e-4, "wd": 1e-4},
        {"lr": 1e-3, "wd": 1e-5}
    ]
    best_opt = None
    best_opt_rmse = float("inf")
    stage3_results = {}

    for opt in opt_grid:
        cfg_name = f"lr_{opt['lr']}_wd_{opt['wd']}"
        set_seed(42)
        model = GlucoShieldMultiTaskRNN(
            cell_type=best_cell,
            dynamic_dim=22,
            static_dim=9,
            hidden_dim=best_cap["hidden"],
            num_layers=best_cap["layers"],
            dropout=best_cap["dropout"],
            use_static=True,
            meal_c_max=200.0
        ).to(device)

        loss_fn = MultiTaskLoss(traj_loss_type="huber", lambda_traj=1.0, lambda_risk=5.0, pos_weights=pos_weights)
        res = train_model(model, train_loader, val_loader, meta_val, device, loss_fn, lr=opt["lr"], weight_decay=opt["wd"], max_epochs=8, patience=3, verbose=False)

        val_rmse = res["best_val_eval"]["trajectory"]["overall"]["RMSE"]
        val_mae = res["best_val_eval"]["trajectory"]["overall"]["MAE"]
        hypo4_auprc = res["best_val_eval"]["risk"]["hypo_4h"]["AUPRC"]
        print(f"  {cfg_name:<16} -> Val RMSE: {val_rmse:.2f} mg/dL | Val MAE: {val_mae:.2f} mg/dL | Hypo4h AUPRC: {hypo4_auprc:.3f}")

        stage3_results[cfg_name] = {"val_rmse": val_rmse, "val_mae": val_mae, "res": res}
        experiment_log.append({
            "stage": 3,
            "name": f"Stage3_{cfg_name}",
            "val_rmse": val_rmse,
            "val_mae": val_mae,
            "hypo4_auprc": hypo4_auprc
        })

        if val_rmse < best_opt_rmse:
            best_opt_rmse = val_rmse
            best_opt = opt

    print(f"\n>>> STAGE 3 WINNER (Validation ONLY): lr={best_opt['lr']}, wd={best_opt['wd']} (Val RMSE = {best_opt_rmse:.2f} mg/dL)")

    # ============================================================================
    # STAGE 4: LOSS FUNCTION TUNING
    # ============================================================================
    print("\n================================================================================")
    print("STAGE 4: LOSS FUNCTION COMPARISON (Huber vs MAE vs MSE & Lambda Risk)")
    print("================================================================================")
    loss_configs = [
        {"traj_loss": "huber", "lambda_risk": 5.0},
        {"traj_loss": "mae", "lambda_risk": 5.0},
        {"traj_loss": "mse", "lambda_risk": 5.0},
        {"traj_loss": "huber", "lambda_risk": 2.0},
        {"traj_loss": "huber", "lambda_risk": 10.0}
    ]
    best_loss_cfg = None
    best_loss_rmse = float("inf")

    for lcfg in loss_configs:
        cfg_name = f"{lcfg['traj_loss']}_lrisk_{lcfg['lambda_risk']}"
        set_seed(42)
        model = GlucoShieldMultiTaskRNN(
            cell_type=best_cell,
            dynamic_dim=22,
            static_dim=9,
            hidden_dim=best_cap["hidden"],
            num_layers=best_cap["layers"],
            dropout=best_cap["dropout"],
            use_static=True,
            meal_c_max=200.0
        ).to(device)

        loss_fn = MultiTaskLoss(traj_loss_type=lcfg["traj_loss"], lambda_traj=1.0, lambda_risk=lcfg["lambda_risk"], pos_weights=pos_weights)
        res = train_model(model, train_loader, val_loader, meta_val, device, loss_fn, lr=best_opt["lr"], weight_decay=best_opt["wd"], max_epochs=8, patience=3, verbose=False)

        val_rmse = res["best_val_eval"]["trajectory"]["overall"]["RMSE"]
        val_mae = res["best_val_eval"]["trajectory"]["overall"]["MAE"]
        hypo4_auprc = res["best_val_eval"]["risk"]["hypo_4h"]["AUPRC"]
        print(f"  {cfg_name:<20} -> Val RMSE: {val_rmse:.2f} mg/dL | Val MAE: {val_mae:.2f} mg/dL | Hypo4h AUPRC: {hypo4_auprc:.3f}")

        experiment_log.append({
            "stage": 4,
            "name": f"Stage4_{cfg_name}",
            "val_rmse": val_rmse,
            "val_mae": val_mae,
            "hypo4_auprc": hypo4_auprc
        })

        if val_rmse < best_loss_rmse:
            best_loss_rmse = val_rmse
            best_loss_cfg = lcfg

    print(f"\n>>> STAGE 4 WINNER (Validation ONLY): traj_loss={best_loss_cfg['traj_loss']}, lambda_risk={best_loss_cfg['lambda_risk']} (Val RMSE = {best_loss_rmse:.2f} mg/dL)")

    # ============================================================================
    # STAGE 5: MEAL INPUT TRANSFORM (C_MAX SELECTION)
    # ============================================================================
    print("\n================================================================================")
    print("STAGE 5: MEAL INPUT TRANSFORM SELECTION (C_MAX)")
    print("================================================================================")
    c_max_candidates = [None, 100.0, 150.0, 200.0, 250.0, 300.0]
    best_c_max = None
    best_c_max_rmse = float("inf")

    for cmax in c_max_candidates:
        c_label = f"CMAX_{int(cmax)}" if cmax is not None else "Raw_NoTransform"
        set_seed(42)
        model = GlucoShieldMultiTaskRNN(
            cell_type=best_cell,
            dynamic_dim=22,
            static_dim=9,
            hidden_dim=best_cap["hidden"],
            num_layers=best_cap["layers"],
            dropout=best_cap["dropout"],
            use_static=True,
            meal_c_max=cmax
        ).to(device)

        loss_fn = MultiTaskLoss(traj_loss_type=best_loss_cfg["traj_loss"], lambda_traj=1.0, lambda_risk=best_loss_cfg["lambda_risk"], pos_weights=pos_weights)
        res = train_model(model, train_loader, val_loader, meta_val, device, loss_fn, lr=best_opt["lr"], weight_decay=best_opt["wd"], max_epochs=8, patience=3, verbose=False)

        val_rmse = res["best_val_eval"]["trajectory"]["overall"]["RMSE"]
        val_mae = res["best_val_eval"]["trajectory"]["overall"]["MAE"]
        hypo4_auprc = res["best_val_eval"]["risk"]["hypo_4h"]["AUPRC"]
        print(f"  {c_label:<18} -> Val RMSE: {val_rmse:.2f} mg/dL | Val MAE: {val_mae:.2f} mg/dL | Hypo4h AUPRC: {hypo4_auprc:.3f}")

        experiment_log.append({
            "stage": 5,
            "name": f"Stage5_{c_label}",
            "val_rmse": val_rmse,
            "val_mae": val_mae,
            "hypo4_auprc": hypo4_auprc
        })

        if val_rmse < best_c_max_rmse:
            best_c_max_rmse = val_rmse
            best_c_max = cmax

    print(f"\n>>> STAGE 5 WINNER (Validation ONLY): meal_c_max={best_c_max} (Val RMSE = {best_c_max_rmse:.2f} mg/dL)")

    # ============================================================================
    # CONTROLLED ABLATION STUDY (ON VALIDATION SET)
    # ============================================================================
    print("\n================================================================================")
    print("CONTROLLED ABLATION STUDY (ON VALIDATION SET ONLY)")
    print("================================================================================")
    ablation_results = {}

    # Ablation 1: Full Best Model
    set_seed(42)
    best_model = GlucoShieldMultiTaskRNN(
        cell_type=best_cell,
        dynamic_dim=22,
        static_dim=9,
        hidden_dim=best_cap["hidden"],
        num_layers=best_cap["layers"],
        dropout=best_cap["dropout"],
        use_static=True,
        meal_c_max=best_c_max
    ).to(device)
    loss_fn = MultiTaskLoss(traj_loss_type=best_loss_cfg["traj_loss"], lambda_traj=1.0, lambda_risk=best_loss_cfg["lambda_risk"], pos_weights=pos_weights)
    print("\nTraining Final Full Neural Model (epochs=12)...")
    full_res = train_model(best_model, train_loader, val_loader, meta_val, device, loss_fn, lr=best_opt["lr"], weight_decay=best_opt["wd"], max_epochs=12, patience=4, verbose=True)
    ablation_results["1_Full_Model"] = full_res["best_val_eval"]

    # Ablation 2: No Static Context (Dynamic Sequence Only)
    set_seed(42)
    no_static_model = GlucoShieldMultiTaskRNN(
        cell_type=best_cell,
        dynamic_dim=22,
        static_dim=0,
        hidden_dim=best_cap["hidden"],
        num_layers=best_cap["layers"],
        dropout=best_cap["dropout"],
        use_static=False,
        meal_c_max=best_c_max
    ).to(device)
    no_static_res = train_model(no_static_model, train_loader, val_loader, meta_val, device, loss_fn, lr=best_opt["lr"], weight_decay=best_opt["wd"], max_epochs=10, patience=3, verbose=False)
    ablation_results["2_No_Static_Context"] = no_static_res["best_val_eval"]

    # Ablation 3: No Meal Transform
    set_seed(42)
    no_meal_trans_model = GlucoShieldMultiTaskRNN(
        cell_type=best_cell,
        dynamic_dim=22,
        static_dim=9,
        hidden_dim=best_cap["hidden"],
        num_layers=best_cap["layers"],
        dropout=best_cap["dropout"],
        use_static=True,
        meal_c_max=None
    ).to(device)
    no_meal_trans_res = train_model(no_meal_trans_model, train_loader, val_loader, meta_val, device, loss_fn, lr=best_opt["lr"], weight_decay=best_opt["wd"], max_epochs=10, patience=3, verbose=False)
    ablation_results["3_No_Meal_Transform"] = no_meal_trans_res["best_val_eval"]

    print("\nAblation Comparison Summary (Validation Set):")
    for ab_name, ab_eval in ablation_results.items():
        ov = ab_eval["trajectory"]["overall"]
        r_hypo = ab_eval["risk"]["hypo_4h"]
        print(f"  {ab_name:<22} | Val RMSE: {ov['RMSE']:.2f} mg/dL | Val MAE: {ov['MAE']:.2f} mg/dL | Hypo4h AUPRC: {r_hypo['AUPRC']:.3f} | Clarke A+B: {ov['Zone_AB_pct']:.2f}%")

    # ============================================================================
    # FINAL TEST SET EVALUATION (EXACTLY ONCE ON FROZEN TEST SET)
    # ============================================================================
    print("\n================================================================================")
    print("FINAL EVALUATION ON FROZEN TEST SET (DATASET V1.0)")
    print("================================================================================")
    test_eval = evaluate_model(full_res["model"], test_loader, loss_fn, device, meta_test)
    test_traj = test_eval["trajectory"]
    test_risk = test_eval["risk"]

    print("\n[Final Selected Neural Model Test Results]")
    print(f"  Overall MAE            : {test_traj['overall']['MAE']:.2f} mg/dL")
    print(f"  Overall RMSE           : {test_traj['overall']['RMSE']:.2f} mg/dL")
    print(f"  Clarke Error Grid A+B  : {test_traj['overall']['Zone_AB_pct']:.2f}%")
    print(f"  Macro-Patient RMSE     : {test_traj['macro_patient']['macro_patient_rmse_mean']:.2f} ± {test_traj['macro_patient']['macro_patient_rmse_std']:.2f} mg/dL")
    print(f"  T1DM Subgroup RMSE     : {test_traj['subgroups']['T1DM']['RMSE']:.2f} mg/dL ({test_traj['subgroups']['T1DM']['num_patients']} pts, {test_traj['subgroups']['T1DM']['num_sequences']} seqs)")
    print(f"  T2DM Subgroup RMSE     : {test_traj['subgroups']['T2DM']['RMSE']:.2f} mg/dL ({test_traj['subgroups']['T2DM']['num_patients']} pts, {test_traj['subgroups']['T2DM']['num_sequences']} seqs)")

    print("\n[Horizon-Wise Test Performance]")
    for h_name, h_vals in test_traj["horizons"].items():
        print(f"  {h_name:<16}: RMSE = {h_vals['RMSE']:>5.2f} mg/dL | MAE = {h_vals['MAE']:>5.2f} mg/dL | Clarke A+B = {h_vals['Zone_AB_pct']:>5.2f}%")

    print("\n[Acute Risk Classification Performance on Test Set]")
    for rname, rmetrics in test_risk.items():
        print(f"  {rname:<10}: Sens = {rmetrics['Sensitivity']*100:>5.1f}% | Spec = {rmetrics['Specificity']*100:>5.1f}% | F1 = {rmetrics['F1']:>5.3f} | AUPRC = {rmetrics['AUPRC']:>5.3f} | AUROC = {rmetrics['AUROC']:>5.3f} | Brier = {rmetrics['Brier']:>5.4f}")

    # ============================================================================
    # SAVE CHECKPOINTS, PREDICTIONS & SUMMARY MANIFEST
    # ============================================================================
    print("\n--- SAVING BEST MODEL CHECKPOINTS & ARTIFACTS ---")
    torch.save({
        "model_state_dict": full_res["model"].state_dict(),
        "config": {
            "cell_type": best_cell,
            "dynamic_dim": 22,
            "static_dim": 9,
            "hidden_dim": best_cap["hidden"],
            "num_layers": best_cap["layers"],
            "dropout": best_cap["dropout"],
            "use_static": True,
            "meal_c_max": best_c_max,
            "horizon": 20,
            "lr": best_opt["lr"],
            "weight_decay": best_opt["wd"],
            "traj_loss": best_loss_cfg["traj_loss"],
            "lambda_risk": best_loss_cfg["lambda_risk"],
            "best_epoch": full_res["best_epoch"]
        },
        "test_metrics": test_traj["overall"]
    }, os.path.join(models_dir, "glucoshield_neural_best.pt"))

    # Save predictions
    np.save(os.path.join(results_dir, "preds_best_neural_test.npy"), test_eval["preds_traj"])
    np.save(os.path.join(results_dir, "probs_best_neural_test.npy"), test_eval["probs_risk"])

    # Comparison with Ridge Baseline
    ridge_test_rmse = 35.80
    ridge_test_mae = 25.37
    neural_test_rmse = test_traj["overall"]["RMSE"]
    neural_test_mae = test_traj["overall"]["MAE"]
    rmse_impr_abs = ridge_test_rmse - neural_test_rmse
    rmse_impr_pct = (rmse_impr_abs / ridge_test_rmse) * 100.0
    mae_impr_abs = ridge_test_mae - neural_test_mae
    mae_impr_pct = (mae_impr_abs / ridge_test_mae) * 100.0

    summary_out = {
        "model_name": f"GlucoShield_MultiTask_{best_cell.upper()}_Best",
        "selected_configuration": {
            "cell_type": best_cell,
            "hidden_dim": best_cap["hidden"],
            "num_layers": best_cap["layers"],
            "dropout": best_cap["dropout"],
            "use_static": True,
            "meal_c_max": best_c_max,
            "learning_rate": best_opt["lr"],
            "weight_decay": best_opt["wd"],
            "traj_loss_type": best_loss_cfg["traj_loss"],
            "lambda_risk": best_loss_cfg["lambda_risk"],
            "best_training_epoch": full_res["best_epoch"]
        },
        "validation_performance": full_res["best_val_eval"]["trajectory"]["overall"],
        "test_performance": test_traj,
        "test_risk_classification": test_risk,
        "baseline_comparison": {
            "ridge_test_rmse": ridge_test_rmse,
            "neural_test_rmse": neural_test_rmse,
            "rmse_improvement_abs_mg_dl": round(rmse_impr_abs, 2),
            "rmse_improvement_pct": round(rmse_impr_pct, 2),
            "ridge_test_mae": ridge_test_mae,
            "neural_test_mae": neural_test_mae,
            "mae_improvement_abs_mg_dl": round(mae_impr_abs, 2),
            "mae_improvement_pct": round(mae_impr_pct, 2)
        },
        "ablations": {
            k: {
                "val_rmse": v["trajectory"]["overall"]["RMSE"],
                "val_mae": v["trajectory"]["overall"]["MAE"],
                "hypo_4h_auprc": v["risk"]["hypo_4h"]["AUPRC"]
            } for k, v in ablation_results.items()
        },
        "experiment_log": experiment_log
    }

    with open(os.path.join(results_dir, "neural_summary.json"), "w") as f:
        json.dump(summary_out, f, indent=2)

    print(f"\nNeural Research Suite completed successfully! Artifacts saved to {results_dir}")
    return summary_out

if __name__ == "__main__":
    run_neural_experiments()
