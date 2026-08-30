"""
GlucoShield Food Vision Evaluation Engine
=========================================
Standalone evaluation suite for macronutrient regression:
  - Per-target MAE (grams / kcal)
  - Per-target RMSE (grams / kcal)
  - Mean Absolute Percentage Error (MAPE %)
  - Pearson Correlation (r) & R^2 Score
  - MC-Dropout Uncertainty calibration
  - Success and failure case identification
"""

import numpy as np
import scipy.stats as stats
from typing import Dict, Any, List, Tuple

TARGET_NAMES = ["Carbohydrates (g)", "Protein (g)", "Total Fat (g)", "Calories (kcal)"]
TARGET_KEYS = ["carbs", "protein", "fat", "calories"]

def evaluate_macronutrient_predictions(
    y_true: np.ndarray,
    y_pred: np.ndarray
) -> Dict[str, Dict[str, float]]:
    """
    Computes comprehensive regression metrics for each macronutrient target.
    
    Args:
      y_true: Array of shape (N, 4) -> [carbs, protein, fat, calories]
      y_pred: Array of shape (N, 4)
    Returns:
      results: Dictionary of metrics per target.
    """
    results = {}
    
    for i, (name, key) in enumerate(zip(TARGET_NAMES, TARGET_KEYS)):
        t = y_true[:, i]
        p = y_pred[:, i]
        diff = p - t

        mae = float(np.mean(np.abs(diff)))
        rmse = float(np.sqrt(np.mean(diff ** 2)))
        
        # Safe MAPE: only for targets > 1.0g to avoid division by near-zero
        nonzero_mask = t > 1.0
        if np.sum(nonzero_mask) > 0:
            mape = float(np.mean(np.abs(diff[nonzero_mask]) / t[nonzero_mask]) * 100.0)
        else:
            mape = 0.0

        # Pearson correlation
        if np.std(t) > 1e-6 and np.std(p) > 1e-6:
            r_val, p_val = stats.pearsonr(t, p)
            r_val = float(r_val)
        else:
            r_val = 0.0

        # R^2 Score
        ss_res = np.sum(diff ** 2)
        ss_tot = np.sum((t - np.mean(t)) ** 2)
        r2 = float(1.0 - (ss_res / (ss_tot + 1e-8)))

        results[key] = {
            "target_name": name,
            "mean_true": round(float(np.mean(t)), 2),
            "mean_pred": round(float(np.mean(p)), 2),
            "MAE": round(mae, 2),
            "RMSE": round(rmse, 2),
            "MAPE_pct": round(mape, 2),
            "Pearson_r": round(r_val, 3),
            "R2_Score": round(r2, 3)
        }

    return results


def evaluate_uncertainty_calibration(
    y_true: np.ndarray,
    y_mean: np.ndarray,
    y_std: np.ndarray,
    z_score: float = 1.96
) -> Dict[str, Dict[str, float]]:
    """
    Evaluates 95% MC-dropout predictive interval calibration.
    """
    calib_results = {}
    
    for i, (name, key) in enumerate(zip(TARGET_NAMES, TARGET_KEYS)):
        t = y_true[:, i]
        m = y_mean[:, i]
        s = y_std[:, i]

        lower = np.maximum(0.0, m - z_score * s)
        upper = m + z_score * s

        covered = (t >= lower) & (t <= upper)
        empirical_coverage = float(np.mean(covered) * 100.0)
        mean_width = float(np.mean(upper - lower))

        calib_results[key] = {
            "target_name": name,
            "nominal_coverage_pct": 95.0,
            "empirical_coverage_pct": round(empirical_coverage, 2),
            "mean_interval_width": round(mean_width, 2)
        }

    return calib_results


def identify_representative_cases(
    dish_ids: List[str],
    y_true: np.ndarray,
    y_pred: np.ndarray
) -> Dict[str, Any]:
    """
    Identifies best, median, and worst prediction cases based on Carbohydrate MAE.
    """
    carb_errors = np.abs(y_pred[:, 0] - y_true[:, 0])
    
    idx_best = int(np.argmin(carb_errors))
    idx_worst = int(np.argmax(carb_errors))
    median_err = float(np.median(carb_errors))
    idx_median = int(np.argmin(np.abs(carb_errors - median_err)))

    def format_case(idx):
        return {
            "dish_id": str(dish_ids[idx]),
            "true_targets": [round(float(v), 1) for v in y_true[idx]],
            "pred_targets": [round(float(v), 1) for v in y_pred[idx]],
            "carb_error_g": round(float(carb_errors[idx]), 2)
        }

    return {
        "best_case": format_case(idx_best),
        "median_case": format_case(idx_median),
        "worst_case": format_case(idx_worst)
    }
