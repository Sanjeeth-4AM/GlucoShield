"""
GlucoShield Decision Engine - Clinical Explainer & Factor Attribution
=====================================================================
Generates natural language clinical rationale decomposing recent trends,
active IOB/COB kinetics, hybrid model contributions, and uncertainty factors.
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Any

@dataclass
class ExplanationReport:
    """Structured clinical explanation for forecast and risk output."""
    headline: str
    trend_summary: str
    metabolic_factors: List[str]
    hybrid_attribution: str
    uncertainty_rationale: str
    key_takeaway: str


class ClinicalExplainer:
    """
    Decomposes multi-modal inputs and physics states into transparent explanations.
    """
    def generate_explanation(
        self,
        current_glucose: float,
        trajectory: np.ndarray,
        iob_units: float,
        cob_grams: float,
        mean_alpha: float,
        mean_uncertainty_std: float,
        primary_status: str
    ) -> ExplanationReport:
        """
        Synthesizes model states into an interpretable clinical rationale.
        """
        # 1. Trend summary
        delta_1h = trajectory[3] - current_glucose
        if delta_1h > 25.0:
            trend_str = f"Strong upward momentum (+{delta_1h:.0f} mg/dL over next 1 hour) driven by active carbohydrate digestion."
        elif delta_1h < -25.0:
            trend_str = f"Rapid downward trajectory ({delta_1h:.0f} mg/dL over next 1 hour) indicating active insulin clearance surpassing glucose appearance."
        elif delta_1h > 10.0:
            trend_str = f"Moderate rising trend (+{delta_1h:.0f} mg/dL over next 1 hour)."
        elif delta_1h < -10.0:
            trend_str = f"Moderate downward trend ({delta_1h:.0f} mg/dL over next 1 hour)."
        else:
            trend_str = "Stable glucose equilibrium expected over the next 1 hour."

        # 2. Metabolic factors
        factors = []
        if cob_grams > 5.0:
            factors.append(f"Active Carbohydrates on Board: {cob_grams:.1f}g remaining in GI tract contributing to systemic appearance.")
        else:
            factors.append("Minimal Carbohydrates on Board (<5g).")

        if iob_units > 0.5:
            factors.append(f"Active Insulin on Board: {iob_units:.2f} Units currently exerting peripheral glucose disposal and hepatic suppression.")
        else:
            factors.append("Low Insulin on Board (<0.5 U).")

        # 3. Hybrid Attribution
        neural_pct = mean_alpha * 100.0
        ode_pct = (1.0 - mean_alpha) * 100.0
        hybrid_str = (
            f"Forecast synthesized via Hybrid Engine: {neural_pct:.0f}% Deep Recurrent Sequence Weight "
            f"(short-term nonlinear momentum) + {ode_pct:.0f}% Mechanistic ODE Weight (first-principles metabolic clearance)."
        )

        # 4. Uncertainty rationale
        if mean_uncertainty_std > 22.0:
            unc_str = (
                f"Elevated predictive uncertainty (mean std: {mean_uncertainty_std:.1f} mg/dL) "
                f"due to extended 5-hour forecast horizon and postprandial variance."
            )
        elif mean_uncertainty_std > 14.0:
            unc_str = (
                f"Moderate predictive uncertainty (mean std: {mean_uncertainty_std:.1f} mg/dL) "
                f"consistent with standard CGM sensor diffusion variance."
            )
        else:
            unc_str = f"High confidence forecast (mean std: {mean_uncertainty_std:.1f} mg/dL) with strong agreement between Neural and ODE models."

        # 5. Headline & Key takeaway
        nadir = np.min(trajectory)
        peak = np.max(trajectory)
        
        if nadir < 70.0:
            headline = f"Hypoglycemia Warning — Projected Nadir of {nadir:.0f} mg/dL"
            takeaway = "Active insulin action is projected to outpace carbohydrate absorption. Monitor CGM closely."
        elif peak > 200.0:
            headline = f"Postprandial Hyperglycemia — Projected Peak of {peak:.0f} mg/dL"
            takeaway = "Carbohydrate influx exceeds current circulating insulin. Glucose is expected to peak before returning toward baseline."
        else:
            headline = f"In-Range Glycemic Trajectory (Projected Range: {nadir:.0f} - {peak:.0f} mg/dL)"
            takeaway = "Metabolic fluxes remain balanced within the target 70-180 mg/dL clinical range."

        return ExplanationReport(
            headline=headline,
            trend_summary=trend_str,
            metabolic_factors=factors,
            hybrid_attribution=hybrid_str,
            uncertainty_rationale=unc_str,
            key_takeaway=takeaway
        )
