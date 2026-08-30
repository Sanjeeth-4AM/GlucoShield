"""
GlucoShield Decision Engine - Uncertainty Calibration & Coverage Evaluator
==========================================================================
Evaluates empirical prediction interval coverage (80% and 95%), sharpness (interval width),
and horizon-wise reliability across clinical validation cohorts.
"""

import numpy as np
from typing import Dict, Any

def evaluate_interval_calibration(
    y_true: np.ndarray,          # Shape (N, 20) [mg/dL]
    lower_80: np.ndarray,        # Shape (N, 20) [mg/dL]
    upper_80: np.ndarray,        # Shape (N, 20) [mg/dL]
    lower_95: np.ndarray,        # Shape (N, 20) [mg/dL]
    upper_95: np.ndarray         # Shape (N, 20) [mg/dL]
) -> Dict[str, Any]:
    """
    Evaluates empirical prediction interval coverage and width.
    """
    assert y_true.shape == lower_80.shape == upper_80.shape, "Shape mismatch in calibration eval"
    
    # 80% coverage check: (y >= L) & (y <= U)
    covered_80 = (y_true >= lower_80) & (y_true <= upper_80)
    cov_80_overall = float(np.mean(covered_80) * 100.0)
    width_80_overall = float(np.mean(upper_80 - lower_80))

    # 95% coverage check
    covered_95 = (y_true >= lower_95) & (y_true <= upper_95)
    cov_95_overall = float(np.mean(covered_95) * 100.0)
    width_95_overall = float(np.mean(upper_95 - lower_95))

    # Horizon-wise breakdown (20 steps)
    horizon_names = [
        "15min", "30min", "45min", "1h", "1h15m", "1h30m", "1h45m", "2h",
        "2h15m", "2h30m", "2h45m", "3h", "3h15m", "3h30m", "3h45m", "4h",
        "4h15m", "4h30m", "4h45m", "5h"
    ]
    
    horizon_calibration = {}
    for k in range(y_true.shape[1]):
        h_name = horizon_names[k]
        cov_80_k = float(np.mean(covered_80[:, k]) * 100.0)
        cov_95_k = float(np.mean(covered_95[:, k]) * 100.0)
        width_80_k = float(np.mean(upper_80[:, k] - lower_80[:, k]))
        width_95_k = float(np.mean(upper_95[:, k] - lower_95[:, k]))
        
        horizon_calibration[h_name] = {
            "step": k + 1,
            "coverage_80_pct": round(cov_80_k, 2),
            "coverage_95_pct": round(cov_95_k, 2),
            "width_80_mg_dl": round(width_80_k, 2),
            "width_95_mg_dl": round(width_95_k, 2)
        }

    # Winkler Score for 95% Interval (alpha=0.05)
    # Winkler = (U - L) + (2/alpha)*(L - y)*I(y < L) + (2/alpha)*(y - U)*I(y > U)
    alpha = 0.05
    w_width = upper_95 - lower_95
    penalty_low = (2.0 / alpha) * np.maximum(0.0, lower_95 - y_true)
    penalty_high = (2.0 / alpha) * np.maximum(0.0, y_true - upper_95)
    winkler_score = float(np.mean(w_width + penalty_low + penalty_high))

    return {
        "overall_coverage_80_pct": round(cov_80_overall, 2),
        "target_coverage_80_pct": 80.0,
        "overall_coverage_95_pct": round(cov_95_overall, 2),
        "target_coverage_95_pct": 95.0,
        "mean_width_80_mg_dl": round(width_80_overall, 2),
        "mean_width_95_mg_dl": round(width_95_overall, 2),
        "winkler_score_95": round(winkler_score, 2),
        "horizon_breakdown": horizon_calibration
    }
