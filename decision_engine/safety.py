"""
GlucoShield Decision Engine - Safety Guardrails & Disclaimers
============================================================
Enforces non-prescriptive research boundaries, input validation,
and severe risk notification rules.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class ClinicalAlert:
    severity: str    # INFO | WARNING | CRITICAL
    category: str    # HYPOGLYCEMIA | HYPERGLYCEMIA | UNCERTAINTY | INPUT_VALIDATION
    message: str
    actionable_guidance: str

class SafetyGuardrails:
    """
    Ensures safe, non-prescriptive decision-support operation.
    """
    RESEARCH_DISCLAIMER = (
        "RESEARCH PROTOTYPE NOTICE: GlucoShield predictions, simulations, and risk alerts "
        "are for research, education, and clinical decision-support only. They do NOT constitute "
        "medical prescriptions or automated dosing instructions. Always consult certified healthcare "
        "professionals for insulin adjustments."
    )

    @classmethod
    def validate_inputs(
        cls,
        current_glucose: float,
        proposed_carbs: float,
        proposed_bolus: float
    ) -> List[str]:
        """Validates that incoming parameters are within plausible bounds."""
        warnings = []
        if current_glucose < 30.0 or current_glucose > 600.0:
            warnings.append(f"Input glucose value ({current_glucose:.1f} mg/dL) is outside valid sensor limits [30, 600].")
        if proposed_carbs < 0.0 or proposed_carbs > 350.0:
            warnings.append(f"Proposed meal carb quantity ({proposed_carbs:.1f}g) exceeds realistic single-meal bounds [0, 350g].")
        if proposed_bolus < 0.0 or proposed_bolus > 50.0:
            warnings.append(f"Proposed insulin bolus ({proposed_bolus:.1f} U) exceeds standard safety limits [0, 50 U].")
        return warnings

    @classmethod
    def format_safe_response(
        cls,
        status: str,
        alerts: List[str],
        counterfactual_summary: Optional[Dict] = None
    ) -> Dict:
        return {
            "disclaimer": cls.RESEARCH_DISCLAIMER,
            "status": status,
            "alerts": alerts,
            "counterfactual": counterfactual_summary
        }
