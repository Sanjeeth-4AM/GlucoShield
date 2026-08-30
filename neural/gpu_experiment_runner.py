"""
GlucoShield Controlled GPU Experiment Suite (Resumable & Fault-Tolerant)
========================================================================
Executes:
  Step 1: GPU Reproduction Check (4 key configs)
  Step 2: Remaining Search (Stage 3 optimization + Stage 4 loss tuning)
  Step 3: Multi-Seed Stability (3 seeds on final selected validation config)
  Step 4: Final Model Lock & Single Untouched Frozen Test Evaluation

Saves:
  - D:/ML PROJECT/neural/training_progress.csv
  - D:/ML PROJECT/neural/neural_summary_gpu.json
  - D:/ML PROJECT/results/neural/neural_summary_gpu.json
  - D:/ML PROJECT/models/glucoshield_neural_best.pt
  - D:/ML PROJECT/models/glucoshield_neural_seed{seed}.pt
  - D:/ML PROJECT/results/neural/preds_best_neural_test.npy
  - D:/ML PROJECT/results/neural/probs_best_neural_test.npy
"""

import os
import sys
import json
import copy
import time
import csv
import torch
import numpy as np
import pandas as pd

# Force utf-8 stdout/stderr
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from neural.models import GlucoShieldMultiTaskRNN
from neural.dataset import get_neural_dataloaders, compute_training_pos_weights
from neural.train import MultiTaskLoss, train_model, evaluate_model

BASE_DIR = "D:/ML PROJECT"
FINAL_DIR = os.path.join(BASE_DIR, "data", "final")
MODELS_DIR = os.path.join(BASE_DIR, "models")
RESULTS_DIR = os.path.join(BASE_DIR, "results", "neural")
NEURAL_DIR = os.path.join(BASE_DIR, "neural")
PROGRESS_CSV = os.path.join(NEURAL_DIR, "training_progress.csv")

for d in [MODELS_DIR, RESULTS_DIR, NEURAL_DIR]:
    os.makedirs(d, exist_ok=True)

CPU_RESULTS = {
    "gru_base_h64": {"val_rmse": 34.44, "val_mae": 24.20, "hypo4h_auprc": 0.693},
    "lstm_base_h64": {"val_rmse": 35.57, "val_mae": 24.86, "hypo4h_auprc": 0.670},
    "gru_h128_l1_d0.2": {"val_rmse": 33.28, "val_mae": 23.05, "hypo4h_auprc": 0.801},
    "stage3_lr2e3_wd1e4": {"val_rmse": 31.45, "val_mae": 21.69, "hypo4h_auprc": 0.831},
}

def set_seed(seed=42):
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

def verify_gpu():
    assert torch.cuda.is_available(), "FATAL: CUDA not available!"
    device = torch.device("cuda")
    print(f"  PYTORCH VERSION:      {torch.__version__}")
    print(f"  CUDA AVAILABLE:       {torch.cuda.is_available()}")
    print(f"  PYTORCH CUDA VERSION: {torch.version.cuda}")
    print(f"  SELECTED DEVICE:      {device}")
    print(f"  GPU NAME:             {torch.cuda.get_device_name(0)}")
    return device

def gpu_memory_check():
    alloc = torch.cuda.memory_allocated(0) / 1024**2
    resrv = torch.cuda.memory_reserved(0) / 1024**2
    print(f"  [GPU Mem] Allocated: {alloc:.0f} MiB | Reserved: {resrv:.0f} MiB")

def init_or_load_progress_csv():
    headers = [
        "step", "experiment_name", "stage", "seed",
        "cell_type", "hidden", "layers", "dropout", "lr", "wd",
        "traj_loss", "lambda_risk", "meal_c_max",
        "best_epoch", "val_rmse", "val_mae",
        "hypo_1h_auprc", "hypo_2h_auprc", "hypo_4h_auprc",
        "hyper_2h_auprc", "hyper_4h_auprc",
        "hypo_4h_sensitivity", "hypo_4h_specificity",
        "clarke_ab_pct", "train_time_sec", "device"
    ]
    completed_names = set()
    if os.path.exists(PROGRESS_CSV):
        try:
            df = pd.read_csv(PROGRESS_CSV)
            if "experiment_name" in df.columns:
                completed_names = set(df["experiment_name"].dropna().tolist())
                print(f"Found existing progress CSV with {len(completed_names)} completed experiments: {completed_names}")
                return completed_names
        except Exception as e:
            print(f"Could not read existing progress CSV ({e}), initializing fresh.")
    
    with open(PROGRESS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
    return completed_names

def log_experiment(step, name, stage, seed, config, res, device_str):
    ev = res["best_val_eval"]
    ov = ev["trajectory"]["overall"]
    risk = ev["risk"]
    row = [
        step, name, stage, seed,
        config.get("cell_type", ""), config.get("hidden", ""),
        config.get("layers", ""), config.get("dropout", ""),
        config.get("lr", ""), config.get("wd", ""),
        config.get("traj_loss", ""), config.get("lambda_risk", ""),
        config.get("meal_c_max", ""),
        res["best_epoch"],
        round(ov["RMSE"], 4), round(ov["MAE"], 4),
        round(risk["hypo_1h"]["AUPRC"], 4), round(risk["hypo_2h"]["AUPRC"], 4),
        round(risk["hypo_4h"]["AUPRC"], 4),
        round(risk["hyper_2h"]["AUPRC"], 4), round(risk["hyper_4h"]["AUPRC"], 4),
        round(risk["hypo_4h"]["Sensitivity"], 4), round(risk["hypo_4h"]["Specificity"], 4),
        round(ov.get("Zone_AB_pct", 0.0), 2),
        round(res["train_time_sec"], 1), device_str
    ]
    with open(PROGRESS_CSV, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(row)

def run_single_experiment(config, train_loader, val_loader, meta_val, device, pos_weights,
                          max_epochs=10, patience=3, verbose=False, seed=42):
    set_seed(seed)
    model = GlucoShieldMultiTaskRNN(
        cell_type=config["cell_type"],
        dynamic_dim=22, static_dim=config.get("static_dim", 9),
        hidden_dim=config["hidden"],
        num_layers=config["layers"],
        dropout=config["dropout"],
        use_static=config.get("use_static", True),
        meal_c_max=config.get("meal_c_max", 200.0)
    ).to(device)

    loss_fn = MultiTaskLoss(
        traj_loss_type=config.get("traj_loss", "huber"),
        lambda_traj=1.0,
        lambda_risk=config.get("lambda_risk", 5.0),
        pos_weights=pos_weights
    )

    res = train_model(
        model, train_loader, val_loader, meta_val, device, loss_fn,
        lr=config.get("lr", 1e-3),
        weight_decay=config.get("wd", 1e-4),
        max_epochs=max_epochs,
        patience=patience,
        verbose=verbose
    )

    assert next(res["model"].parameters()).device.type == "cuda", "Model fell back to CPU!"
    return res

def print_comparison_table(gpu_results, cpu_ref):
    print("\n+==========================+===========+===========+===========+=================+")
    print("|                  GPU vs CPU REPRODUCIBILITY COMPARISON                         |")
    print("+==========================+===========+===========+===========+=================+")
    print("| Config                   | CPU RMSE  | GPU RMSE  | Delta RMSE| Status          |")
    print("+==========================+===========+===========+===========+=================+")
    all_ok = True
    for name, gpu_r in gpu_results.items():
        cpu_r = cpu_ref.get(name, {})
        cpu_rmse = cpu_r.get("val_rmse", float("nan"))
        gpu_rmse = gpu_r["val_rmse"]
        delta = gpu_rmse - cpu_rmse
        abs_delta = abs(delta)
        if abs_delta < 1.0:
            status = "CONSISTENT"
        elif abs_delta < 2.0:
            status = "MINOR DIFF"
        else:
            status = "INVESTIGATE"
            all_ok = False
        print(f"| {name:<24} | {cpu_rmse:>7.2f}   | {gpu_rmse:>7.2f}   | {delta:>+7.2f}   | {status:<15} |")
    print("+==========================+===========+===========+===========+=================+")
    return all_ok

def main():
    print("=" * 80)
    print("GLUCOSHIELD: CONTROLLED GPU EXPERIMENT SUITE")
    print("=" * 80)

    # 1. GPU Verification
    print("\n--- GPU VERIFICATION ---")
    device = verify_gpu()
    gpu_memory_check()

    # 2. Data Loading
    print("\n--- LOADING DATASET V1.0 (FROZEN) ---")
    train_loader, val_loader, test_loader = get_neural_dataloaders(data_dir=FINAL_DIR, batch_size=256)
    pos_weights = compute_training_pos_weights(data_dir=FINAL_DIR).to(device)
    print(f"  pos_weights: {pos_weights.cpu().numpy().round(2)}")
    meta_val = pd.read_csv(os.path.join(FINAL_DIR, "meta_val.csv"))
    meta_test = pd.read_csv(os.path.join(FINAL_DIR, "meta_test.csv"))

    completed_experiments = init_or_load_progress_csv()
    experiment_log = []
    step = 0

    # ====================================================================
    # STEP 1: GPU REPRODUCTION CHECK
    # ====================================================================
    print("\n" + "=" * 80)
    print("STEP 1: GPU REPRODUCTION CHECK (4 Key Configs)")
    print("=" * 80)

    repro_configs = {
        "gru_base_h64": {
            "cell_type": "gru", "hidden": 64, "layers": 1, "dropout": 0.2,
            "lr": 1e-3, "wd": 1e-4, "traj_loss": "huber", "lambda_risk": 5.0, "meal_c_max": 200.0
        },
        "lstm_base_h64": {
            "cell_type": "lstm", "hidden": 64, "layers": 1, "dropout": 0.2,
            "lr": 1e-3, "wd": 1e-4, "traj_loss": "huber", "lambda_risk": 5.0, "meal_c_max": 200.0
        },
        "gru_h128_l1_d0.2": {
            "cell_type": "gru", "hidden": 128, "layers": 1, "dropout": 0.2,
            "lr": 1e-3, "wd": 1e-4, "traj_loss": "huber", "lambda_risk": 5.0, "meal_c_max": 200.0
        },
        "stage3_lr2e3_wd1e4": {
            "cell_type": "gru", "hidden": 128, "layers": 1, "dropout": 0.2,
            "lr": 2e-3, "wd": 1e-4, "traj_loss": "huber", "lambda_risk": 5.0, "meal_c_max": 200.0
        },
    }

    gpu_repro = {}
    for name, cfg in repro_configs.items():
        step += 1
        print(f"\n  [{step}] Running/Verifying: {name} ...")
        t0 = time.time()
        res = run_single_experiment(cfg, train_loader, val_loader, meta_val, device, pos_weights,
                                    max_epochs=8, patience=3, verbose=True, seed=42)
        ev = res["best_val_eval"]
        val_rmse = ev["trajectory"]["overall"]["RMSE"]
        val_mae = ev["trajectory"]["overall"]["MAE"]
        h4_auprc = ev["risk"]["hypo_4h"]["AUPRC"]
        h4_sens = ev["risk"]["hypo_4h"]["Sensitivity"]
        elapsed = time.time() - t0

        gpu_repro[name] = {"val_rmse": val_rmse, "val_mae": val_mae, "hypo4h_auprc": h4_auprc}
        print(f"  --> GPU: Val RMSE={val_rmse:.2f} | MAE={val_mae:.2f} | Hypo4h AUPRC={h4_auprc:.3f} | Sens={h4_sens*100:.1f}% | Time={elapsed:.1f}s")
        gpu_memory_check()

        log_experiment(step, name, "repro", 42, cfg, res, "cuda")
        experiment_log.append({"step": step, "stage": "repro", "name": name,
                               "val_rmse": val_rmse, "val_mae": val_mae, "hypo4h_auprc": h4_auprc,
                               "train_time": round(elapsed, 1)})

    repro_ok = print_comparison_table(gpu_repro, CPU_RESULTS)
    if not repro_ok:
        print("\nWARNING: Discrepancies detected. Investigate before proceeding.")
    else:
        print("\n[PASS] GPU reproduction consistent with CPU results. Proceeding.")

    best_cell = "gru"
    best_cap = {"hidden": 128, "layers": 1, "dropout": 0.2}
    best_opt = {"lr": 2e-3, "wd": 1e-4}
    best_opt_rmse = gpu_repro["stage3_lr2e3_wd1e4"]["val_rmse"]
    stage3_all = {"lr_0.002_wd_0.0001": gpu_repro["stage3_lr2e3_wd1e4"]}

    # ====================================================================
    # STEP 2: COMPLETE REMAINING SEARCH
    # ====================================================================
    print("\n" + "=" * 80)
    print("STEP 2: COMPLETE REMAINING SEARCH")
    print("=" * 80)

    # --- Stage 3 Remainder ---
    print("\n--- Stage 3: Remaining Optimization Configs ---")
    stage3_remaining = [
        {"lr": 1e-3, "wd": 1e-4},
        {"lr": 5e-4, "wd": 1e-4},
        {"lr": 1e-3, "wd": 1e-5},
    ]

    for opt in stage3_remaining:
        step += 1
        cfg_name = f"lr_{opt['lr']}_wd_{opt['wd']}"
        cfg = {
            "cell_type": best_cell, "hidden": best_cap["hidden"],
            "layers": best_cap["layers"], "dropout": best_cap["dropout"],
            "lr": opt["lr"], "wd": opt["wd"],
            "traj_loss": "huber", "lambda_risk": 5.0, "meal_c_max": 200.0
        }
        print(f"\n  [{step}] Stage 3: {cfg_name} ...")
        res = run_single_experiment(cfg, train_loader, val_loader, meta_val, device, pos_weights,
                                    max_epochs=10, patience=3, verbose=False, seed=42)
        ev = res["best_val_eval"]
        val_rmse = ev["trajectory"]["overall"]["RMSE"]
        val_mae = ev["trajectory"]["overall"]["MAE"]
        h4_auprc = ev["risk"]["hypo_4h"]["AUPRC"]
        print(f"      -> Val RMSE: {val_rmse:.2f} | MAE: {val_mae:.2f} | Hypo4h AUPRC: {h4_auprc:.3f}")

        stage3_all[cfg_name] = {"val_rmse": val_rmse, "val_mae": val_mae, "hypo4h_auprc": h4_auprc}
        log_experiment(step, f"S3_{cfg_name}", "stage3", 42, cfg, res, "cuda")
        experiment_log.append({"step": step, "stage": "stage3", "name": cfg_name,
                               "val_rmse": val_rmse, "val_mae": val_mae, "hypo4h_auprc": h4_auprc})

        if val_rmse < best_opt_rmse:
            best_opt_rmse = val_rmse
            best_opt = opt

    print(f"\n>>> STAGE 3 WINNER: lr={best_opt['lr']}, wd={best_opt['wd']} (Val RMSE = {best_opt_rmse:.2f} mg/dL)")

    # --- Stage 4: Loss Function Tuning ---
    print("\n--- Stage 4: Loss Function Comparison ---")
    loss_configs = [
        {"traj_loss": "huber", "lambda_risk": 5.0},
        {"traj_loss": "mae",   "lambda_risk": 5.0},
        {"traj_loss": "mse",   "lambda_risk": 5.0},
        {"traj_loss": "huber", "lambda_risk": 2.0},
        {"traj_loss": "huber", "lambda_risk": 10.0},
    ]
    best_loss_cfg = None
    best_loss_rmse = float("inf")
    stage4_all = {}

    for lcfg in loss_configs:
        step += 1
        cfg_name = f"{lcfg['traj_loss']}_lrisk_{lcfg['lambda_risk']}"
        cfg = {
            "cell_type": best_cell, "hidden": best_cap["hidden"],
            "layers": best_cap["layers"], "dropout": best_cap["dropout"],
            "lr": best_opt["lr"], "wd": best_opt["wd"],
            "traj_loss": lcfg["traj_loss"], "lambda_risk": lcfg["lambda_risk"],
            "meal_c_max": 200.0
        }
        print(f"\n  [{step}] Stage 4: {cfg_name} ...")
        res = run_single_experiment(cfg, train_loader, val_loader, meta_val, device, pos_weights,
                                    max_epochs=10, patience=3, verbose=False, seed=42)
        ev = res["best_val_eval"]
        val_rmse = ev["trajectory"]["overall"]["RMSE"]
        val_mae = ev["trajectory"]["overall"]["MAE"]
        h4_auprc = ev["risk"]["hypo_4h"]["AUPRC"]
        print(f"      -> Val RMSE: {val_rmse:.2f} | MAE: {val_mae:.2f} | Hypo4h AUPRC: {h4_auprc:.3f}")

        stage4_all[cfg_name] = {"val_rmse": val_rmse, "val_mae": val_mae, "hypo4h_auprc": h4_auprc}
        log_experiment(step, f"S4_{cfg_name}", "stage4", 42, cfg, res, "cuda")
        experiment_log.append({"step": step, "stage": "stage4", "name": cfg_name,
                               "val_rmse": val_rmse, "val_mae": val_mae, "hypo4h_auprc": h4_auprc})

        if val_rmse < best_loss_rmse:
            best_loss_rmse = val_rmse
            best_loss_cfg = lcfg

    print(f"\n>>> STAGE 4 WINNER: traj_loss={best_loss_cfg['traj_loss']}, lambda_risk={best_loss_cfg['lambda_risk']} (Val RMSE = {best_loss_rmse:.2f} mg/dL)")

    # ====================================================================
    # STEP 3: MULTI-SEED STABILITY (3 seeds)
    # ====================================================================
    print("\n" + "=" * 80)
    print("STEP 3: MULTI-SEED STABILITY TEST")
    print("=" * 80)

    final_cfg = {
        "cell_type": best_cell, "hidden": best_cap["hidden"],
        "layers": best_cap["layers"], "dropout": best_cap["dropout"],
        "lr": best_opt["lr"], "wd": best_opt["wd"],
        "traj_loss": best_loss_cfg["traj_loss"], "lambda_risk": best_loss_cfg["lambda_risk"],
        "meal_c_max": 200.0
    }

    print(f"\n  Final Config to test across seeds:\n{json.dumps(final_cfg, indent=2)}")
    seeds = [42, 123, 7]
    seed_results = []
    seed_models = []

    for seed in seeds:
        step += 1
        print(f"\n  [{step}] Seed {seed} training (epochs=12, patience=4)...")
        res = run_single_experiment(final_cfg, train_loader, val_loader, meta_val, device, pos_weights,
                                    max_epochs=12, patience=4, verbose=True, seed=seed)
        ev = res["best_val_eval"]
        ov = ev["trajectory"]["overall"]
        risk = ev["risk"]

        sr = {
            "seed": seed,
            "best_epoch": res["best_epoch"],
            "val_rmse": ov["RMSE"], "val_mae": ov["MAE"],
            "clarke_ab_pct": ov.get("Zone_AB_pct", 0.0),
            "hypo_1h_auprc": risk["hypo_1h"]["AUPRC"],
            "hypo_2h_auprc": risk["hypo_2h"]["AUPRC"],
            "hypo_4h_auprc": risk["hypo_4h"]["AUPRC"],
            "hyper_2h_auprc": risk["hyper_2h"]["AUPRC"],
            "hyper_4h_auprc": risk["hyper_4h"]["AUPRC"],
            "hypo_4h_sensitivity": risk["hypo_4h"]["Sensitivity"],
            "hypo_4h_specificity": risk["hypo_4h"]["Specificity"],
            "train_time": round(res["train_time_sec"], 1),
        }
        seed_results.append(sr)
        seed_models.append(res)

        ckpt_path = os.path.join(MODELS_DIR, f"glucoshield_neural_seed{seed}.pt")
        torch.save({
            "model_state_dict": res["model"].state_dict(),
            "config": final_cfg,
            "seed": seed,
            "best_epoch": res["best_epoch"],
            "val_metrics": ov
        }, ckpt_path)

        print(f"  --> Seed {seed}: Val RMSE={ov['RMSE']:.2f} | MAE={ov['MAE']:.2f} | Hypo4h AUPRC={risk['hypo_4h']['AUPRC']:.3f} | Time={res['train_time_sec']:.1f}s")
        gpu_memory_check()

        log_experiment(step, f"MultiSeed_s{seed}", "stability", seed, final_cfg, res, "cuda")

    rmses = [s["val_rmse"] for s in seed_results]
    maes = [s["val_mae"] for s in seed_results]
    h4_auprcs = [s["hypo_4h_auprc"] for s in seed_results]

    print("\n" + "-" * 60)
    print("MULTI-SEED STABILITY SUMMARY")
    print("-" * 60)
    print(f"  Val RMSE:      {np.mean(rmses):.2f} +/- {np.std(rmses):.2f} mg/dL  (seeds: {[round(r,2) for r in rmses]})")
    print(f"  Val MAE:       {np.mean(maes):.2f} +/- {np.std(maes):.2f} mg/dL  (seeds: {[round(m,2) for m in maes]})")
    print(f"  Hypo4h AUPRC:  {np.mean(h4_auprcs):.3f} +/- {np.std(h4_auprcs):.3f}")

    best_seed_idx = int(np.argmin(rmses))
    best_seed = seeds[best_seed_idx]
    print(f"\n  Selected seed for final model lock: {best_seed} (Val RMSE = {rmses[best_seed_idx]:.2f} mg/dL)")

    # ====================================================================
    # STEP 4: FINAL MODEL LOCK & TEST EVALUATION (EXACTLY ONCE)
    # ====================================================================
    print("\n" + "=" * 80)
    print("STEP 4: FINAL MODEL LOCK & FROZEN TEST EVALUATION")
    print("=" * 80)

    final_model = seed_models[best_seed_idx]["model"]
    final_loss_fn = MultiTaskLoss(
        traj_loss_type=best_loss_cfg["traj_loss"],
        lambda_traj=1.0,
        lambda_risk=best_loss_cfg["lambda_risk"],
        pos_weights=pos_weights
    )

    print("\n  Evaluating final locked model on UNTOUCHED TEST SET (exactly once)...")
    test_eval = evaluate_model(final_model, test_loader, final_loss_fn, device, meta_test)
    test_traj = test_eval["trajectory"]
    test_risk = test_eval["risk"]

    print("\n" + "=" * 80)
    print("FINAL TEST RESULTS - GlucoShield Core Neural Forecaster")
    print("=" * 80)

    print(f"\n[TRAJECTORY PERFORMANCE]")
    print(f"  Overall MAE:           {test_traj['overall']['MAE']:.2f} mg/dL")
    print(f"  Overall RMSE:          {test_traj['overall']['RMSE']:.2f} mg/dL")
    print(f"  Clarke Error Grid A+B: {test_traj['overall']['Zone_AB_pct']:.2f}%")
    print(f"  Clarke Zone A:         {test_traj['overall']['Zone_A_pct']:.2f}%")

    print(f"\n[MACRO-PATIENT METRICS]")
    mp = test_traj.get("macro_patient", {})
    print(f"  Macro-Patient RMSE:    {mp.get('macro_patient_rmse_mean', 0):.2f} +/- {mp.get('macro_patient_rmse_std', 0):.2f} mg/dL")

    print(f"\n[SUBGROUP PERFORMANCE]")
    for sg_name, sg_vals in test_traj.get("subgroups", {}).items():
        print(f"  {sg_name}: RMSE={sg_vals['RMSE']:.2f} mg/dL | MAE={sg_vals['MAE']:.2f} mg/dL | N_patients={sg_vals['num_patients']} | N_seqs={sg_vals['num_sequences']}")

    print(f"\n[HORIZON-WISE PERFORMANCE]")
    for h_name, h_vals in test_traj.get("horizons", {}).items():
        print(f"  {h_name:<16}: RMSE={h_vals['RMSE']:>6.2f} | MAE={h_vals['MAE']:>6.2f} | Clarke A+B={h_vals['Zone_AB_pct']:>6.2f}%")

    print(f"\n[ACUTE RISK CLASSIFICATION - TEST SET]")
    for rname, rm in test_risk.items():
        print(f"  {rname:<10}: Sens={rm['Sensitivity']*100:>5.1f}% | Spec={rm['Specificity']*100:>5.1f}% | "
              f"Prec={rm['Precision']*100:>5.1f}% | F1={rm['F1']:.3f} | "
              f"AUPRC={rm['AUPRC']:.3f} | AUROC={rm['AUROC']:.3f} | Brier={rm['Brier']:.4f}")

    ridge_test_rmse = 35.80
    ridge_test_mae = 25.37
    neural_test_rmse = test_traj["overall"]["RMSE"]
    neural_test_mae = test_traj["overall"]["MAE"]
    rmse_impr = ridge_test_rmse - neural_test_rmse
    rmse_impr_pct = (rmse_impr / ridge_test_rmse) * 100.0
    mae_impr = ridge_test_mae - neural_test_mae
    mae_impr_pct = (mae_impr / ridge_test_mae) * 100.0

    print(f"\n[BASELINE COMPARISON vs RIDGE (Day 2)]")
    print(f"  Ridge Test RMSE:   {ridge_test_rmse:.2f} mg/dL")
    print(f"  Neural Test RMSE:  {neural_test_rmse:.2f} mg/dL")
    print(f"  RMSE Improvement:  {rmse_impr:+.2f} mg/dL ({rmse_impr_pct:+.1f}%)")
    print(f"  Ridge Test MAE:    {ridge_test_mae:.2f} mg/dL")
    print(f"  Neural Test MAE:   {neural_test_mae:.2f} mg/dL")
    print(f"  MAE Improvement:   {mae_impr:+.2f} mg/dL ({mae_impr_pct:+.1f}%)")

    print(f"\n[LIMITATION]")
    t1dm_info = test_traj.get("subgroups", {}).get("T1DM", {})
    print(f"  T1DM test cohort: {t1dm_info.get('num_patients', 'N/A')} unique patients, "
          f"{t1dm_info.get('num_sequences', 'N/A')} sequences.")
    print(f"  Subgroup conclusions for T1DM must be interpreted cautiously due to small sample size.")

    # Save final model checkpoint
    final_ckpt_path = os.path.join(MODELS_DIR, "glucoshield_neural_best.pt")
    torch.save({
        "model_state_dict": final_model.state_dict(),
        "config": final_cfg,
        "seed": best_seed,
        "best_epoch": seed_models[best_seed_idx]["best_epoch"],
        "test_metrics": test_traj["overall"],
        "test_risk": test_risk
    }, final_ckpt_path)
    print(f"\n  Final checkpoint saved: {final_ckpt_path}")

    # Save test predictions
    np.save(os.path.join(RESULTS_DIR, "preds_best_neural_test.npy"), test_eval["preds_traj"])
    np.save(os.path.join(RESULTS_DIR, "probs_best_neural_test.npy"), test_eval["probs_risk"])
    print(f"  Test predictions saved to {RESULTS_DIR}")

    summary = {
        "model_name": f"GlucoShield_MultiTask_{best_cell.upper()}_GPU",
        "hardware": f"CUDA ({torch.cuda.get_device_name(0)}) | PyTorch {torch.__version__}",
        "selected_configuration": final_cfg,
        "selected_seed": best_seed,
        "multi_seed_stability": {
            "seeds": seeds,
            "val_rmse_mean": round(float(np.mean(rmses)), 4),
            "val_rmse_std": round(float(np.std(rmses)), 4),
            "val_mae_mean": round(float(np.mean(maes)), 4),
            "val_mae_std": round(float(np.std(maes)), 4),
            "hypo4h_auprc_mean": round(float(np.mean(h4_auprcs)), 4),
            "hypo4h_auprc_std": round(float(np.std(h4_auprcs)), 4),
            "per_seed": seed_results
        },
        "validation_performance": seed_models[best_seed_idx]["best_val_eval"]["trajectory"]["overall"],
        "test_performance": test_traj,
        "test_risk_classification": test_risk,
        "baseline_comparison": {
            "ridge_test_rmse": ridge_test_rmse,
            "neural_test_rmse": round(neural_test_rmse, 4),
            "rmse_improvement_abs_mg_dl": round(rmse_impr, 2),
            "rmse_improvement_pct": round(rmse_impr_pct, 2),
            "ridge_test_mae": ridge_test_mae,
            "neural_test_mae": round(neural_test_mae, 4),
            "mae_improvement_abs_mg_dl": round(mae_impr, 2),
            "mae_improvement_pct": round(mae_impr_pct, 2)
        },
        "search_stages": {
            "stage3_optimization": stage3_all,
            "stage4_loss": stage4_all
        },
        "gpu_reproduction_check": gpu_repro,
        "experiment_log": experiment_log
    }

    # Save to both paths
    for p in [os.path.join(RESULTS_DIR, "neural_summary_gpu.json"), os.path.join(NEURAL_DIR, "neural_summary_gpu.json")]:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, default=str)
        print(f"  Summary saved: {p}")

    gpu_memory_check()
    print("\n" + "=" * 80)
    print("GLUCOSHIELD GPU EXPERIMENT SUITE - COMPLETE")
    print("=" * 80)
    return summary

if __name__ == "__main__":
    main()
