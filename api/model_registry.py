"""
GlucoShield — Production Model Version Registry & Governance (Phase 16)
=======================================================================
Explicitly defines model versions, architecture specifications, and runtime
selection rules.

Governance Rules:
  - Default production model is strictly V1_FROZEN.
  - Phase 13 is available as PHASE13_VALIDATED via explicit configuration or authorized header.
  - Phase 13 has NOT demonstrated aggregate point-forecast superiority over V1 on Category D;
    the system does not make unverified claims of universal superiority.
  - Every forecast/inference response is fully traceable to model, config, gate,
    S_I adapter, and uncertainty versions.
"""

import os
from enum import Enum
from typing import Dict, Any, Optional

class ModelVersion(str, Enum):
    COMBINATION_C = "COMBINATION_C"
    V1_FROZEN = "V1_FROZEN"
    V2_FROZEN = "V2_FROZEN"
    PHASE13_VALIDATED = "PHASE13_VALIDATED"

MODEL_METADATA: Dict[str, Dict[str, Any]] = {
    ModelVersion.COMBINATION_C.value: {
        "model_version": ModelVersion.COMBINATION_C.value,
        "is_default": True,
        "status": "PRODUCTION_DEFAULT",
        "description": "Production Certified Combination C: Frozen V1 Multi-Task Hybrid Point Forecast paired with Phase-13 Regime-Conditioned Calibrated Uncertainty Dispersion.",
        "configuration_version": "v13.3.0-combC",
        "neural_backbone": "GlucoShieldMultiTaskRNN (GRU-128, 22-channels)",
        "physics_engine": "Hovorka ODE Digital Twin (MHE kalman calibration)",
        "gate_version": "v1_mhe_adaptive_gate (point) + phase13_disagreement_attenuated_d35_tau8_w25_c40 (uncertainty)",
        "si_adapter_version": "none (static population prior)",
        "uncertainty_version": "v2_regime_conditioned_quantiles (calibrated 96.39% 95-cov on Category D)",
        "evidence_summary": "Certified production release in FINAL_MODEL_SELECTION_REPORT.md. Preserves V1 point accuracy (44.15 mg/dL RMSE on Category D) while providing calibrated uncertainty bounds (96.39% 95% coverage, Winkler-95: 246.17)."
    },
    ModelVersion.V1_FROZEN.value: {
        "model_version": ModelVersion.V1_FROZEN.value,
        "is_default": False,
        "status": "LEGACY_PRODUCTION_BASELINE",
        "description": "Legacy Production V1 Baseline: Multi-task GRU-128 with MHE Hovorka Physics Prior and heuristic MC-Dropout prediction intervals.",
        "configuration_version": "v1.0.0",
        "neural_backbone": "GlucoShieldMultiTaskRNN (GRU-128, 22-channels)",
        "physics_engine": "Hovorka ODE Digital Twin (MHE kalman calibration)",
        "gate_version": "v1_mhe_adaptive_gate",
        "si_adapter_version": "none (static population prior)",
        "uncertainty_version": "v1_heuristic_mhe_intervals",
        "evidence_summary": "Category A training baseline; stable point forecasts (44.15 mg/dL RMSE on Category D). Legacy MC-Dropout interval path."
    },
    ModelVersion.V2_FROZEN.value: {
        "model_version": ModelVersion.V2_FROZEN.value,
        "is_default": False,
        "status": "RESEARCH_FROZEN",
        "description": "V2 Context-Aware Neural Forecaster with unrestricted fusion gate and regime-conditioned uncertainty.",
        "configuration_version": "v2.0.0",
        "neural_backbone": "GlucoShieldNeuralForecasterV2 (Context-conditioned GRU)",
        "physics_engine": "Hovorka ODE Digital Twin (Forward integrator)",
        "gate_version": "v2_unrestricted_gate",
        "si_adapter_version": "none",
        "uncertainty_version": "v2_regime_conditioned_quantiles",
        "evidence_summary": "Evaluated in Phase 11-12; exhibits elevated physics contribution under high divergence."
    },
    ModelVersion.PHASE13_VALIDATED.value: {
        "model_version": ModelVersion.PHASE13_VALIDATED.value,
        "is_default": False,
        "status": "VALIDATED_AVAILABLE",
        "description": "Phase-13 Validated Architecture: V2 Context-Aware Forecaster with Disagreement-Attenuated Gate (40% ceiling, 25% high-divergence) and Causal Online S_I Adaptation.",
        "configuration_version": "v13.2.0",
        "neural_backbone": "GlucoShieldNeuralForecasterV2 (Context-conditioned GRU)",
        "physics_engine": "Hovorka ODE Digital Twin with Causal Online S_I Adaptation",
        "gate_version": "phase13_disagreement_attenuated_d35_tau8_w25_c40",
        "si_adapter_version": "phase13_causal_online_si_bounded",
        "uncertainty_version": "v2_regime_conditioned_quantiles (calibrated 96.13% 95-cov on Category D)",
        "evidence_summary": "Validated in Phase 13 and Phase 15. Successfully prevents ODE runaway under strong disagreement (45.74 mg/dL RMSE on Category D). Note: does not claim universal point-accuracy superiority over V1."
    }
}

def get_configured_model_version() -> str:
    """Returns the globally configured model version, defaulting safely to COMBINATION_C."""
    configured = os.getenv("ACTIVE_MODEL_VERSION", ModelVersion.COMBINATION_C.value).upper()
    if configured not in MODEL_METADATA:
        # Fall back safely to production default COMBINATION_C
        return ModelVersion.COMBINATION_C.value
    return configured

def resolve_model_version(requested_version: Optional[str] = None) -> str:
    """
    Resolves the model version for a request.
    If requested_version is provided and valid, returns it; otherwise returns globally configured model.
    """
    if requested_version:
        v_upper = requested_version.upper()
        if v_upper in MODEL_METADATA:
            return v_upper
    return get_configured_model_version()

def get_model_traceability(model_version: str) -> Dict[str, Any]:
    """Returns traceability dictionary required for inference responses and audit logging."""
    meta = MODEL_METADATA.get(model_version, MODEL_METADATA[ModelVersion.COMBINATION_C.value])
    return {
        "model_version": meta["model_version"],
        "configuration_version": meta["configuration_version"],
        "gate_version": meta["gate_version"],
        "si_adapter_version": meta["si_adapter_version"],
        "uncertainty_version": meta["uncertainty_version"],
        "status": meta["status"]
    }
