"""
GlucoShield Decision Engine - Clinical Risk Engine & Alert Categorization
========================================================================
Combines neural risk probabilities with trajectory-derived physiological indices
to produce stratified clinical alerts and early warning notifications.
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Any, Optional

@dataclass
class RiskAssessment:
    """Holds comprehensive acute risk evaluation results."""
    primary_status: str              # STABLE | RISING | FALLING | RAPID_DROP | HIGH_UNCERTAINTY
    alert_level: str                 # NONE | INFO | WARNING | CRITICAL
    hypo_risk_1h_prob: float
    hypo_risk_2h_prob: float
    hypo_risk_4h_prob: float
    hyper_risk_2h_prob: float
    hyper_risk_4h_prob: float
    trajectory_nadir_mg_dl: float
    time_to_nadir_min: int
    trajectory_peak_mg_dl: float
    time_to_peak_min: int
    projected_hypo_duration_min: int
    active_alerts: List[str]


class ClinicalRiskEngine:
    """
    Evaluates acute metabolic danger thresholds:
      - Hypoglycemia Level 1: < 70 mg/dL
      - Severe Hypoglycemia Level 2: < 54 mg/dL
      - Hyperglycemia: > 180 mg/dL
      - Severe Hyperglycemia: > 250 mg/dL
      - Rapid Fall Rate: < -2.0 mg/dL/min
    """
    def __init__(
        self,
        hypo_alert_threshold: float = 0.35, # Validated probability threshold for hypo alert
        hyper_alert_threshold: float = 0.50
    ):
        self.hypo_thresh = hypo_alert_threshold
        self.hyper_thresh = hyper_alert_threshold

    def evaluate_risk(
        self,
        current_glucose: float,
        trajectory: np.ndarray,             # (20,) [mg/dL]
        risk_probs: np.ndarray,             # (5,) [h1, h2, h4, H2, H4]
        interval_lower_95: Optional[np.ndarray] = None
    ) -> RiskAssessment:
        """
        Synthesizes neural risk probabilities and trajectory geometry into actionable clinical status.
        """
        h1_p, h2_p, h4_p, H2_p, H4_p = [float(p) for p in risk_probs]
        
        nadir_val = float(np.min(trajectory))
        nadir_idx = int(np.argmin(trajectory))
        time_to_nadir = (nadir_idx + 1) * 15

        peak_val = float(np.max(trajectory))
        peak_idx = int(np.argmax(trajectory))
        time_to_peak = (peak_idx + 1) * 15

        # Count steps below 70 mg/dL in trajectory
        below_70_steps = int(np.sum(trajectory < 70.0))
        hypo_duration_min = below_70_steps * 15

        # Calculate rate of change over first 30 minutes
        delta_30m = trajectory[1] - current_glucose
        rate_per_min = delta_30m / 30.0

        # Determine Primary Status
        if rate_per_min < -1.8:
            status = "RAPID_DROP"
        elif rate_per_min < -0.6:
            status = "FALLING"
        elif rate_per_min > 1.8:
            status = "RAPID_RISE"
        elif rate_per_min > 0.6:
            status = "RISING"
        else:
            status = "STABLE"

        # Generate Active Alerts and Severity Level
        alerts = []
        alert_level = "NONE"

        # Check for Severe Hypo (<54 mg/dL or high 1h probability)
        if nadir_val < 54.0 or h1_p >= 0.60:
            alert_level = "CRITICAL"
            alerts.append(f"CRITICAL: Severe Hypoglycemia projected ({nadir_val:.0f} mg/dL at t+{time_to_nadir}m). Immediate action advised.")
        elif nadir_val < 70.0 or h1_p >= self.hypo_thresh or h2_p >= self.hypo_thresh:
            alert_level = "WARNING" if alert_level != "CRITICAL" else alert_level
            alerts.append(f"WARNING: Hypoglycemia anticipated ({nadir_val:.0f} mg/dL at t+{time_to_nadir}m). Consider checking blood glucose.")
        elif h4_p >= self.hypo_thresh:
            alert_level = "INFO" if alert_level == "NONE" else alert_level
            alerts.append(f"INFO: Elevated 4-hour hypoglycemia probability ({h4_p*100:.0f}%).")

        # Check for Hyperglycemia (>250 mg/dL or high H2/H4 probability)
        if peak_val >= 250.0 or H2_p >= 0.85:
            alert_level = "WARNING" if alert_level != "CRITICAL" else alert_level
            alerts.append(f"WARNING: Severe Hyperglycemia projected ({peak_val:.0f} mg/dL at t+{time_to_peak}m).")
        elif peak_val >= 180.0 and alert_level == "NONE":
            alert_level = "INFO"
            alerts.append(f"INFO: Postprandial glucose expected to exceed 180 mg/dL (Peak: {peak_val:.0f} mg/dL).")

        # Conservative lower-bound safety check: if lower 95% interval drops below 50 mg/dL
        if interval_lower_95 is not None and np.min(interval_lower_95[:8]) < 50.0 and alert_level == "NONE":
            alert_level = "INFO"
            alerts.append("NOTICE: Downside trajectory uncertainty extends into hypoglycemic range.")

        return RiskAssessment(
            primary_status=status,
            alert_level=alert_level,
            hypo_risk_1h_prob=round(h1_p, 4),
            hypo_risk_2h_prob=round(h2_p, 4),
            hypo_risk_4h_prob=round(h4_p, 4),
            hyper_risk_2h_prob=round(H2_p, 4),
            hyper_risk_4h_prob=round(H4_p, 4),
            trajectory_nadir_mg_dl=round(nadir_val, 1),
            time_to_nadir_min=time_to_nadir,
            trajectory_peak_mg_dl=round(peak_val, 1),
            time_to_peak_min=time_to_peak,
            projected_hypo_duration_min=hypo_duration_min,
            active_alerts=alerts
        )
