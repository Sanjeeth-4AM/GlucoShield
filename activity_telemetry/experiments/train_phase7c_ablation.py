"""
GlucoShield — Phase 7C Multimodal Physical Activity Ablation Experiment
========================================================================
Executes the pre-registered 13-fold Leave-One-Patient-Out Cross-Validation (LOOCV)
comparing Model A (Baseline 22 channels) vs Model B (Multimodal 28 channels).

Certified Protocol Version: 2.1.0
Target Dataset: Glucdict (Figshare DOI: 10.6084/m9.figshare.25939312)
Statistical Test: scipy.stats.wilcoxon (two-sided, zero_method='wilcox', N=13)
"""

import os
import sys
import json
import time
import math
import random
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from scipy import stats
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any

BASE_DIR = "D:/ML PROJECT"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from activity_telemetry.glucdict_adapter import GlucdictAdapter
from activity_telemetry.experiments.participant_split import generate_kfold_participant_splits

# Directories
RAW_ROOT = os.path.join(BASE_DIR, "data", "raw", "Glucdict", "Glucdict Dataset")
CACHE_DIR = os.path.join(BASE_DIR, "data", "processed", "glucdict_aligned")
CKPT_DIR = os.path.join(BASE_DIR, "activity_telemetry", "experiments", "checkpoints")
RESULTS_DIR = os.path.join(BASE_DIR, "activity_telemetry", "experiments", "results")
LOG_DIR = os.path.join(BASE_DIR, "activity_telemetry", "experiments", "logs")

# Constants
HISTORY_LEN = 96     # 24 hours at 15m
FORECAST_LEN = 20    # 5 hours at 15m
RANDOM_SEED = 42

def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

class GRUForecaster(nn.Module):
    """GRU Glucose Forecaster for 22-channel (Model A) and 28-channel (Model B) configurations."""
    def __init__(self, in_features: int, hidden_dim: int = 128, num_layers: int = 2, dropout: float = 0.20, out_horizon: int = 20):
        super().__init__()
        self.in_features = in_features
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.out_horizon = out_horizon

        self.gru = nn.GRU(
            input_size=in_features,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0
        )
        self.head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, out_horizon)
        )

    def forward(self, x):
        # x: [Batch, SeqLen, InFeatures]
        out, _ = self.gru(x)
        last_step = out[:, -1, :]  # [Batch, HiddenDim]
        preds = self.head(last_step)  # [Batch, Horizon]
        return preds

class GlucoseWindowDataset(Dataset):
    """Causal sliding window dataset."""
    def __init__(self, sequences: List[Tuple[np.ndarray, np.ndarray, np.ndarray]]):
        # List of (x_window, y_window, is_active_window)
        self.sequences = sequences

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        x, y, is_act = self.sequences[idx]
        return (
            torch.tensor(x, dtype=torch.float32),
            torch.tensor(y, dtype=torch.float32),
            torch.tensor(is_act, dtype=torch.bool)
        )

def build_aligned_telemetry_for_participant(participant_id: str, adapter: GlucdictAdapter) -> pd.DataFrame:
    """Loads and computes all 28 dynamic telemetry features for a participant."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(CACHE_DIR, f"{participant_id}_aligned_15m.csv")
    
    if os.path.exists(cache_file):
        df = pd.read_csv(cache_file)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df

    print(f"  [Cache Miss] Aligning raw streams for {participant_id}...")
    raw_df = adapter.load_participant_telemetry(participant_id)
    
    # 1. CGM dynamics
    glucose = raw_df["cgm_glucose"].interpolate(method="linear", limit=4).bfill().ffill()
    vel = glucose.diff().fillna(0.0)
    acc = vel.diff().fillna(0.0)

    # Rolling statistics
    roll_1h_mean = glucose.rolling(4, min_periods=1).mean()
    roll_1h_std = glucose.rolling(4, min_periods=1).std().fillna(0.0)
    roll_1h_min = glucose.rolling(4, min_periods=1).min()
    roll_1h_max = glucose.rolling(4, min_periods=1).max()

    roll_2h_mean = glucose.rolling(8, min_periods=1).mean()
    roll_2h_std = glucose.rolling(8, min_periods=1).std().fillna(0.0)
    roll_2h_min = glucose.rolling(8, min_periods=1).min()
    roll_2h_max = glucose.rolling(8, min_periods=1).max()

    roll_4h_mean = glucose.rolling(16, min_periods=1).mean()
    roll_4h_std = glucose.rolling(16, min_periods=1).std().fillna(0.0)
    roll_4h_min = glucose.rolling(16, min_periods=1).min()
    roll_4h_max = glucose.rolling(16, min_periods=1).max()

    # Circadian & calendar
    hours = raw_df["timestamp"].dt.hour + raw_df["timestamp"].dt.minute / 60.0
    sin_time = np.sin(2 * np.pi * hours / 24.0)
    cos_time = np.cos(2 * np.pi * hours / 24.0)
    day_of_week = raw_df["timestamp"].dt.dayofweek / 6.0

    # Insulin & Carbohydrates (biological constant / unobserved contract)
    bolus_dose = np.zeros(len(raw_df), dtype=np.float32)
    iob = np.zeros(len(raw_df), dtype=np.float32)
    meal_carbs = np.zeros(len(raw_df), dtype=np.float32)  # Tracked unobserved token
    cob = np.zeros(len(raw_df), dtype=np.float32)         # Tracked unobserved token

    # Activity Features (Model B)
    steps_15m = raw_df["steps"].fillna(0.0).values
    hr_raw = raw_df["heart_rate"]
    sensor_missing = hr_raw.isna().astype(np.float32).values
    hr_clean = hr_raw.interpolate(method="linear", limit=8).bfill().ffill().values
    hr_clean = np.where(np.isnan(hr_clean), 75.0, hr_clean)

    hr_series = pd.Series(hr_clean)
    hr_mean_15m = hr_series.rolling(2, min_periods=1).mean().values
    hr_std_15m = hr_series.rolling(4, min_periods=1).std().fillna(0.0).values

    ax = raw_df["accel_x"].fillna(0.0).values
    ay = raw_df["accel_y"].fillna(0.0).values
    az = raw_df["accel_z"].fillna(9.81).values
    accel_mag_15m = np.sqrt(ax**2 + ay**2 + az**2)

    # Active Load (exponential backward filter gamma=0.75)
    gamma = 0.75
    active_load_60m = np.zeros(len(raw_df), dtype=np.float32)
    current_load = 0.0
    for t in range(len(raw_df)):
        current_load = current_load * gamma + float(steps_15m[t])
        active_load_60m[t] = current_load

    # Active window indicator: active if steps > 100 or HR > 100
    is_active_window = ((steps_15m > 100.0) | (hr_mean_15m > 100.0)).astype(bool)

    df_out = pd.DataFrame({
        "timestamp": raw_df["timestamp"],
        "glucose": glucose,
        "glucose_velocity": vel,
        "glucose_acceleration": acc,
        "glucose_roll_mean_1h": roll_1h_mean,
        "glucose_roll_std_1h": roll_1h_std,
        "glucose_roll_min_1h": roll_1h_min,
        "glucose_roll_max_1h": roll_1h_max,
        "glucose_roll_mean_2h": roll_2h_mean,
        "glucose_roll_std_2h": roll_2h_std,
        "glucose_roll_min_2h": roll_2h_min,
        "glucose_roll_max_2h": roll_2h_max,
        "glucose_roll_mean_4h": roll_4h_mean,
        "glucose_roll_std_4h": roll_4h_std,
        "glucose_roll_min_4h": roll_4h_min,
        "glucose_roll_max_4h": roll_4h_max,
        "sin_time": sin_time,
        "cos_time": cos_time,
        "bolus_dose": bolus_dose,
        "iob": iob,
        "meal_carbs": meal_carbs,
        "cob": cob,
        "day_of_week": day_of_week,
        "steps_15m": steps_15m,
        "hr_mean_15m": hr_mean_15m,
        "hr_std_15m": hr_std_15m,
        "accel_mag_15m": accel_mag_15m,
        "active_load_60m": active_load_60m,
        "sensor_missing": sensor_missing,
        "is_active_window": is_active_window
    })

    df_out.to_csv(cache_file, index=False)
    return df_out

BASE_COLUMNS = [
    "glucose", "glucose_velocity", "glucose_acceleration",
    "glucose_roll_mean_1h", "glucose_roll_std_1h", "glucose_roll_min_1h", "glucose_roll_max_1h",
    "glucose_roll_mean_2h", "glucose_roll_std_2h", "glucose_roll_min_2h", "glucose_roll_max_2h",
    "glucose_roll_mean_4h", "glucose_roll_std_4h", "glucose_roll_min_4h", "glucose_roll_max_4h",
    "sin_time", "cos_time", "bolus_dose", "iob", "meal_carbs", "cob", "day_of_week"
]

ACTIVITY_COLUMNS = [
    "steps_15m", "hr_mean_15m", "hr_std_15m", "accel_mag_15m", "active_load_60m", "sensor_missing"
]

MULTIMODAL_COLUMNS = BASE_COLUMNS + ACTIVITY_COLUMNS

def extract_windows_from_dataframe(df: pd.DataFrame, feature_cols: List[str]):
    X_vals = df[feature_cols].values
    y_vals = df["glucose"].values
    active_flags = df["is_active_window"].values

    total_len = len(df)
    window_total = HISTORY_LEN + FORECAST_LEN
    windows = []

    for i in range(total_len - window_total + 1):
        x_win = X_vals[i : i + HISTORY_LEN]
        y_win = y_vals[i + HISTORY_LEN : i + window_total]
        is_act = bool(active_flags[i + HISTORY_LEN : i + window_total].any())
        windows.append((x_win, y_win, is_act))

    return windows

class FoldScaler:
    """RobustScaler fit strictly on training participants."""
    def __init__(self):
        self.medians = None
        self.iqrs = None

    def fit(self, train_data_matrices: List[np.ndarray]):
        all_train = np.vstack(train_data_matrices)
        self.medians = np.median(all_train, axis=0)
        q75, q25 = np.percentile(all_train, [75, 25], axis=0)
        iqrs = q75 - q25
        self.iqrs = np.where(iqrs < 1e-6, 1.0, iqrs)

    def transform_windows(self, windows):
        scaled_windows = []
        for x, y, is_act in windows:
            x_scaled = (x - self.medians) / self.iqrs
            scaled_windows.append((x_scaled, y, is_act))
        return scaled_windows

def train_model_on_fold(
    train_windows,
    val_windows,
    test_windows,
    in_features: int,
    dropout: float,
    model_name: str,
    fold_idx: int,
    device: torch.device
) -> Tuple[float, float, float, float]:
    """Trains a model on train_windows with early stopping on val_windows, returns test metrics."""
    set_seed(RANDOM_SEED + fold_idx)
    
    train_loader = DataLoader(GlucoseWindowDataset(train_windows), batch_size=64, shuffle=True)
    val_loader = DataLoader(GlucoseWindowDataset(val_windows), batch_size=64, shuffle=False)
    test_loader = DataLoader(GlucoseWindowDataset(test_windows), batch_size=64, shuffle=False)

    model = GRUForecaster(in_features=in_features, hidden_dim=128, num_layers=2, dropout=dropout, out_horizon=FORECAST_LEN).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-5)
    criterion = nn.SmoothL1Loss()

    best_val_mae = float("inf")
    best_weights = None
    patience = 8
    patience_counter = 0
    max_epochs = 25

    for epoch in range(max_epochs):
        model.train()
        for bx, by, _ in train_loader:
            bx, by = bx.to(device), by.to(device)
            optimizer.zero_grad()
            preds = model(bx)
            loss = criterion(preds, by)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

        # Validation
        model.eval()
        val_errors = []
        with torch.no_grad():
            for bx, by, _ in val_loader:
                bx, by = bx.to(device), by.to(device)
                preds = model(bx)
                errs = torch.abs(preds - by).cpu().numpy()
                val_errors.extend(errs.flatten())

        val_mae = float(np.mean(val_errors))
        if val_mae < best_val_mae:
            best_val_mae = val_mae
            best_weights = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= patience:
                break

    # Load best weights
    model.load_state_dict(best_weights)
    model.to(device)
    model.eval()

    # Save checkpoint
    os.makedirs(CKPT_DIR, exist_ok=True)
    ckpt_path = os.path.join(CKPT_DIR, f"phase7c_fold_{fold_idx:02d}_{model_name}.pt")
    torch.save(best_weights, ckpt_path)

    # Evaluate on held-out test participant
    test_all_errs = []
    test_all_sq_errs = []
    test_act_errs = []
    test_rest_errs = []

    with torch.no_grad():
        for bx, by, is_act in test_loader:
            bx, by = bx.to(device), by.to(device)
            preds = model(bx)
            abs_err = torch.abs(preds - by).cpu().numpy()
            sq_err = ((preds - by)**2).cpu().numpy()

            test_all_errs.extend(abs_err.flatten())
            test_all_sq_errs.extend(sq_err.flatten())

            is_act_np = is_act.numpy()
            for b in range(len(is_act_np)):
                if is_act_np[b]:
                    test_act_errs.extend(abs_err[b].flatten())
                else:
                    test_rest_errs.extend(abs_err[b].flatten())

    overall_mae = float(np.mean(test_all_errs))
    overall_rmse = float(np.sqrt(np.mean(test_all_sq_errs)))
    active_mae = float(np.mean(test_act_errs)) if test_act_errs else overall_mae
    rest_mae = float(np.mean(test_rest_errs)) if test_rest_errs else overall_mae

    return overall_mae, overall_rmse, active_mae, rest_mae

def run_phase7c_ablation_experiment():
    set_seed(RANDOM_SEED)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("=" * 80)
    print("GLUCOSHIELD PHASE 7C MULTIMODAL ABLATION TRAINING")
    print(f"Device: {device} | Random Seed: {RANDOM_SEED}")
    print("=" * 80)

    adapter = GlucdictAdapter(RAW_ROOT)
    participants = ["User1", "User3", "User4", "User5", "User6", "User7", "User8", "User9", "User10", "User12", "User13", "User14", "User15"]
    print(f"Pre-caching and aligning telemetry for {len(participants)} participants...")
    
    participant_dfs = {}
    for p in participants:
        participant_dfs[p] = build_aligned_telemetry_for_participant(p, adapter)
    print("All participant telemetry aligned.\n")

    manifest = generate_kfold_participant_splits(participants, n_splits=13, seed=RANDOM_SEED)
    folds = manifest["folds"]

    fold_results = []
    
    print("Initiating 13-Fold Cross-Validation Training (Model A vs Model B)...")
    for f in folds:
        f_idx = f["fold_index"]
        tr_pids = f["train_participants"]
        val_pid = f["validation_participants"][0]
        test_pid = f["test_participants"][0]

        print(f"\n--- FOLD {f_idx:02d} / 13 (Test: {test_pid:6s} | Val: {val_pid:6s} | Train: {len(tr_pids)} pts) ---")

        # 1. Model A Data Pipeline (22 Base Channels)
        scaler_a = FoldScaler()
        scaler_a.fit([participant_dfs[p][BASE_COLUMNS].values for p in tr_pids])
        
        train_wins_a = []
        for p in tr_pids:
            wins = extract_windows_from_dataframe(participant_dfs[p], BASE_COLUMNS)
            train_wins_a.extend(scaler_a.transform_windows(wins))

        val_wins_a = scaler_a.transform_windows(extract_windows_from_dataframe(participant_dfs[val_pid], BASE_COLUMNS))
        test_wins_a = scaler_a.transform_windows(extract_windows_from_dataframe(participant_dfs[test_pid], BASE_COLUMNS))

        # Train Model A
        t0 = time.time()
        mae_a, rmse_a, act_mae_a, rest_mae_a = train_model_on_fold(
            train_wins_a, val_wins_a, test_wins_a,
            in_features=22, dropout=0.20, model_name="model_a", fold_idx=f_idx, device=device
        )
        t_a = time.time() - t0

        # 2. Model B Data Pipeline (28 Multimodal Channels)
        scaler_b = FoldScaler()
        scaler_b.fit([participant_dfs[p][MULTIMODAL_COLUMNS].values for p in tr_pids])

        train_wins_b = []
        for p in tr_pids:
            wins = extract_windows_from_dataframe(participant_dfs[p], MULTIMODAL_COLUMNS)
            train_wins_b.extend(scaler_b.transform_windows(wins))

        val_wins_b = scaler_b.transform_windows(extract_windows_from_dataframe(participant_dfs[val_pid], MULTIMODAL_COLUMNS))
        test_wins_b = scaler_b.transform_windows(extract_windows_from_dataframe(participant_dfs[test_pid], MULTIMODAL_COLUMNS))

        # Train Model B
        t0 = time.time()
        mae_b, rmse_b, act_mae_b, rest_mae_b = train_model_on_fold(
            train_wins_b, val_wins_b, test_wins_b,
            in_features=28, dropout=0.25, model_name="model_b", fold_idx=f_idx, device=device
        )
        t_b = time.time() - t0

        delta_mae = mae_a - mae_b
        delta_act_mae = act_mae_a - act_mae_b
        pct_imp = (delta_mae / mae_a) * 100.0

        print(f"  [Fold {f_idx:02d} Complete] Test Patient: {test_pid}")
        print(f"    Model A (22 Ch): MAE={mae_a:.2f} mg/dL | RMSE={rmse_a:.2f} mg/dL | Active MAE={act_mae_a:.2f} mg/dL ({t_a:.1f}s)")
        print(f"    Model B (28 Ch): MAE={mae_b:.2f} mg/dL | RMSE={rmse_b:.2f} mg/dL | Active MAE={act_mae_b:.2f} mg/dL ({t_b:.1f}s)")
        print(f"    Delta MAE (A - B): {delta_mae:+.2f} mg/dL ({pct_imp:+.2f}%) | Delta Active: {delta_act_mae:+.2f} mg/dL")

        fold_results.append({
            "fold_index": f_idx,
            "test_participant": test_pid,
            "validation_participant": val_pid,
            "train_participants_count": len(tr_pids),
            "model_a_mae": round(mae_a, 3),
            "model_a_rmse": round(rmse_a, 3),
            "model_a_active_mae": round(act_mae_a, 3),
            "model_a_rest_mae": round(rest_mae_a, 3),
            "model_b_mae": round(mae_b, 3),
            "model_b_rmse": round(rmse_b, 3),
            "model_b_active_mae": round(act_mae_b, 3),
            "model_b_rest_mae": round(rest_mae_b, 3),
            "delta_mae_mg_dl": round(delta_mae, 3),
            "delta_active_mae_mg_dl": round(delta_act_mae, 3),
            "percent_improvement": round(pct_imp, 2)
        })

    # Statistical Testing on 13 Paired Out-Of-Fold Observations
    df_res = pd.DataFrame(fold_results)
    mae_a_list = df_res["model_a_mae"].values
    mae_b_list = df_res["model_b_mae"].values
    diffs = mae_a_list - mae_b_list

    # Wilcoxon signed-rank test
    wilcox_res = stats.wilcoxon(mae_a_list, mae_b_list, zero_method="wilcox", alternative="two-sided")
    w_stat = float(wilcox_res.statistic)
    p_val = float(wilcox_res.pvalue)

    mean_mae_a = float(np.mean(mae_a_list))
    mean_mae_b = float(np.mean(mae_b_list))
    overall_delta_mae = mean_mae_a - mean_mae_b
    overall_pct_imp = (overall_delta_mae / mean_mae_a) * 100.0

    mean_act_a = float(df_res["model_a_active_mae"].mean())
    mean_act_b = float(df_res["model_b_active_mae"].mean())
    act_delta_mae = mean_act_a - mean_act_b

    # Evaluation against pre-registered criteria
    meets_overall_threshold = overall_delta_mae >= 1.0
    meets_active_threshold = act_delta_mae >= 3.0
    is_statistically_significant = p_val < 0.05
    is_rejected = (overall_delta_mae < 0.5) or (p_val >= 0.05)

    summary_results = {
        "protocol_version": "2.1.0",
        "dataset_name": "Glucdict",
        "total_participants": 13,
        "cross_validation_strategy": "13_fold_participant_disjoint_loocv",
        "sample_size_n": 13,
        "statistical_unit": "13 paired out-of-fold participant-level error observations, where each participant appears exactly once as a held-out test participant across the complete cross-validation procedure.",
        "statistical_software": "scipy.stats.wilcoxon",
        "wilcoxon_configuration": {
            "zero_method": "wilcox",
            "alternative": "two-sided"
        },
        "metrics_summary": {
            "model_a_mean_mae_mg_dl": round(mean_mae_a, 2),
            "model_b_mean_mae_mg_dl": round(mean_mae_b, 2),
            "overall_delta_mae_mg_dl": round(overall_delta_mae, 2),
            "percent_improvement": round(overall_pct_imp, 2),
            "model_a_active_mae_mg_dl": round(mean_act_a, 2),
            "model_b_active_mae_mg_dl": round(mean_act_b, 2),
            "active_window_delta_mae_mg_dl": round(act_delta_mae, 2),
            "wilcoxon_statistic": round(w_stat, 2),
            "p_value": float(p_val),
            "is_statistically_significant": is_statistically_significant
        },
        "pre_registered_success_criteria": {
            "overall_delta_threshold_1_0_mg_dl": meets_overall_threshold,
            "active_delta_threshold_3_0_mg_dl": meets_active_threshold,
            "significance_p_less_than_0_05": is_statistically_significant,
            "rejection_rule_triggered": is_rejected
        },
        "participant_level_results": fold_results
    }

    # Save results
    os.makedirs(RESULTS_DIR, exist_ok=True)
    res_json_path = os.path.join(RESULTS_DIR, "phase7c_ablation_results.json")
    with open(res_json_path, "w", encoding="utf-8") as f:
        json.dump(summary_results, f, indent=2)

    res_csv_path = os.path.join(RESULTS_DIR, "phase7c_ablation_results.csv")
    df_res.to_csv(res_csv_path, index=False)

    print("\n" + "=" * 80)
    print("PHASE 7C MULTIMODAL ABLATION FINAL RESULTS PACKAGE")
    print("=" * 80)
    print(f"Model A (Baseline 22 Ch) Mean MAE: {mean_mae_a:.2f} mg/dL")
    print(f"Model B (Multimodal 28 Ch) Mean MAE: {mean_mae_b:.2f} mg/dL")
    print(f"Overall Delta MAE (A - B):           {overall_delta_mae:+.2f} mg/dL ({overall_pct_imp:+.2f}%)")
    print(f"Active & Recovery Delta MAE:         {act_delta_mae:+.2f} mg/dL")
    print(f"Wilcoxon Signed-Rank Test:           W = {w_stat:.1f}, p = {p_val:.6f} (Significant: {is_statistically_significant})")
    print(f"Pre-Registered Threshold (>=1.0):    {meets_overall_threshold}")
    print(f"Active Window Threshold (>=3.0):     {meets_active_threshold}")
    print(f"Rejection Rule Triggered:            {is_rejected}")
    print(f"\nSaved Results:\n  --> {res_json_path}\n  --> {res_csv_path}")
    print("=" * 80)

    return summary_results

if __name__ == "__main__":
    run_phase7c_ablation_experiment()
