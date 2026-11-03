"""
GlucoShield Combination C Production Serving Adapter
=====================================================
Integrates the certified Combination C inference architecture:
  1. Point Forecast: Frozen V1 Multi-Task Hybrid Forecaster (MHE + GRU-128)
  2. Prediction Interval Bounds: Frozen Phase-13 Regime-Conditioned Uncertainty
     Head (heteroscedastic dispersion centered symmetrically on the V1 mean)
  3. Safety & Clinical Risk: Evaluated using V1 trajectory, V1 risk probabilities,
     and the calibrated Phase-13 lower prediction bound.

Governance Invariants:
  - V1 Point Trajectory is mathematically preserved (zero drift).
  - V2 degraded point trajectory is NEVER used for point forecasting.
  - Phase-13 uncertainty scaling is applied symmetrically around the V1 mean.
  - Absence of optional wearable context guarantees exact missing-input invariance.
  - Failures in the uncertainty engine raise strict exceptions rather than
    silently returning misleading or collapsed prediction intervals.
"""

import torch
import numpy as np
from typing import Dict, Any, Optional

from physiology.hybrid_fusion import GlucoShieldHybridForecaster
from models.v2.hybrid_forecaster_v2 import GlucoShieldHybridForecasterV2
from models.v2.context_encoder import PhysiologicalContextBatch
from scratch.phase13_disagreement_gate.disagreement_gate import DisagreementAttenuatedFusionGate
from scratch.phase13_patient_specific_ode.patient_ode_adapter import PatientOdeAdapter
from decision_engine.risk_engine import ClinicalRiskEngine, RiskAssessment
from decision_engine.explanation import ClinicalExplainer, ExplanationReport
from decision_engine.safety import SafetyGuardrails
from api.model_registry import ModelVersion, get_model_traceability


class CombinationCProductionAdapter:
    """
    Production serving adapter binding frozen V1 point forecaster with
    frozen Phase-13 regime-conditioned uncertainty dispersion.
    """
    def __init__(
        self,
        v1_hybrid: GlucoShieldHybridForecaster,
        v2_hybrid: GlucoShieldHybridForecasterV2,
        phase13_gate: DisagreementAttenuatedFusionGate,
        risk_engine: Optional[ClinicalRiskEngine] = None,
        explainer: Optional[ClinicalExplainer] = None,
        phase13_adapter: Optional[PatientOdeAdapter] = None,
        device: Optional[torch.device] = None
    ):
        self.device = device or torch.device("cpu")
        self.v1_hybrid = v1_hybrid.to(self.device)
        self.v1_hybrid.eval()

        self.v2_hybrid = v2_hybrid.to(self.device)
        self.v2_hybrid.eval()

        self.phase13_gate = phase13_gate
        self.phase13_adapter = phase13_adapter

        self.risk_engine = risk_engine or ClinicalRiskEngine(hypo_alert_threshold=0.35, hyper_alert_threshold=0.50)
        self.explainer = explainer or ClinicalExplainer()

    def predict(
        self,
        dynamic_seq_scaled: torch.Tensor,   # (1, 96, 22)
        dynamic_seq_raw: torch.Tensor,      # (1, 96, 22)
        static_feat_scaled: torch.Tensor,   # (1, 9)
        static_feat_raw: torch.Tensor,      # (1, 9)
        patient_id: str = "demo_patient_001",
        wearable_context_logged: bool = False
    ) -> Dict[str, Any]:
        """
        Executes certified Combination C inference.

        Returns:
            Dictionary structure matching ForecastResponse schema.
        """
        d_s = dynamic_seq_scaled.to(self.device)
        d_r = dynamic_seq_raw.to(self.device)
        s_s = static_feat_scaled.to(self.device)
        s_r = static_feat_raw.to(self.device)

        # ----------------------------------------------------------------------
        # 1. Point Forecast Generation: Frozen V1 Hybrid Forecaster
        # ----------------------------------------------------------------------
        with torch.no_grad():
            v1_out = self.v1_hybrid(
                d_s, d_r, s_s, s_r, calibrate=True, return_components=True
            )

        y_v1_np = v1_out["trajectory"][0].cpu().numpy()
        y_neural_v1_np = v1_out["y_neural"][0].cpu().numpy()
        y_ode_v1_np = v1_out["y_ode"][0].cpu().numpy()
        alpha_v1_np = v1_out["alpha"][0].cpu().numpy()
        risk_probs_v1_np = v1_out["risk_probs"][0].cpu().numpy()

        # ----------------------------------------------------------------------
        # 2. Uncertainty Quantification: Frozen Phase-13 Uncertainty Engine
        # ----------------------------------------------------------------------
        if self.v2_hybrid is None or self.phase13_gate is None:
            raise RuntimeError(
                "Combination C uncertainty engine failure: Phase-13 components are uninitialized."
            )

        try:
            # Build strictly causal circadian context from observation timestamp harmonics
            sin_24 = d_r[:, -1, 10]
            cos_24 = d_r[:, -1, 11]
            f_circ = torch.stack(
                [sin_24, cos_24, 2.0 * sin_24 * cos_24, cos_24**2 - sin_24**2],
                dim=-1
            ).to(self.device)

            # Unobserved factor channels strictly masked to zero (m=0)
            ctx = PhysiologicalContextBatch(
                f_exercise=torch.zeros(1, 4, device=self.device),
                m_exercise=torch.zeros(1, 1, device=self.device),
                f_sleep=torch.zeros(1, 5, device=self.device),
                m_sleep=torch.zeros(1, 1, device=self.device),
                f_hormonal=torch.zeros(1, 3, device=self.device),
                m_hormonal=torch.zeros(1, 1, device=self.device),
                f_circadian=f_circ
            )

            with torch.no_grad():
                v2_out = self.v2_hybrid(
                    d_s, d_r, s_s, s_r, ctx, calibrate=False, ablation_mode="full_v2"
                )
                y_neural_v2 = v2_out["y_neural"].cpu().numpy()
                y_ode_v2 = v2_out["y_ode"].cpu().numpy()
                alpha_v2 = v2_out["alpha"].cpu().numpy()
                residual_v2 = v2_out["residual"].cpu().numpy()

                # Phase 13 disagreement gating
                blended = self.phase13_gate.blend(y_neural_v2, y_ode_v2, alpha_v2, residual_v2)
                w_phys = blended["w_phys"][0]
                disag = blended["disagreement"][0]

                # Extract regime-conditioned intervals
                p_int = v2_out["prediction_interval"]
                half_w95 = ((p_int.upper_95 - p_int.lower_95) / 2.0).cpu().numpy()[0]
                half_w80 = ((p_int.upper_80 - p_int.lower_80) / 2.0).cpu().numpy()[0]
                std_unc = p_int.std_uncertainty.cpu().numpy()[0]

        except Exception as e:
            raise RuntimeError(
                f"Combination C uncertainty evaluation error: {str(e)}"
            ) from e

        # ----------------------------------------------------------------------
        # 3. Symmetric Interval Centering on Frozen V1 Point Forecast
        # ----------------------------------------------------------------------
        low95 = np.clip(y_v1_np - half_w95, 20.0, 500.0)
        upp95 = np.clip(y_v1_np + half_w95, 20.0, 500.0)
        low80 = np.clip(y_v1_np - half_w80, 20.0, 500.0)
        upp80 = np.clip(y_v1_np + half_w80, 20.0, 500.0)

        # ----------------------------------------------------------------------
        # 4. Current Patient State Extraction
        # ----------------------------------------------------------------------
        current_glucose = float(d_r[0, -1, 0].item())
        current_iob = float(d_r[0, -1, 16].item())
        current_cob = float(d_r[0, -1, 19].item())
        current_vel = float(d_r[0, -1, 1].item())

        # ----------------------------------------------------------------------
        # 5. Clinical Risk Assessment & Explanations
        # ----------------------------------------------------------------------
        risk_assessment = self.risk_engine.evaluate_risk(
            current_glucose=current_glucose,
            trajectory=y_v1_np,
            risk_probs=risk_probs_v1_np,
            interval_lower_95=low95
        )

        explanation = self.explainer.generate_explanation(
            current_glucose=current_glucose,
            trajectory=y_v1_np,
            iob_units=current_iob,
            cob_grams=current_cob,
            mean_alpha=float(np.mean(alpha_v1_np)),
            mean_uncertainty_std=float(np.mean(std_unc)),
            primary_status=risk_assessment.primary_status
        )

        trace = get_model_traceability(ModelVersion.COMBINATION_C.value)
        telemetry = {
            "disagreement_mean_mg_dl": round(float(np.mean(disag)), 2),
            "disagreement_max_mg_dl": round(float(np.max(disag)), 2),
            "physics_contribution_mean_pct": round(float(np.mean(w_phys) * 100.0), 2),
            "physics_ceiling_enforced": bool(np.max(w_phys) <= 0.40001),
            "uncertainty_source": "Phase13_RegimeConditioned",
            "point_source": "V1_Frozen_Hybrid",
            "adapted_si": self.phase13_adapter.config.base_si if self.phase13_adapter else 0.002869,
            "gb_equilibrium": 141.79
        }

        return {
            "disclaimer": SafetyGuardrails.RESEARCH_DISCLAIMER,
            "patient_id": patient_id,
            "current_state": {
                "glucose_mg_dl": round(current_glucose, 1),
                "iob_units": round(current_iob, 2),
                "cob_grams": round(current_cob, 1),
                "velocity_mg_dl_per_15m": round(current_vel, 2),
                "primary_status": risk_assessment.primary_status
            },
            "forecast": {
                "horizon_minutes": [15 * (k + 1) for k in range(20)],
                "point_forecast_mg_dl": [round(float(v), 1) for v in y_v1_np],
                "lower_80_mg_dl": [round(float(v), 1) for v in low80],
                "upper_80_mg_dl": [round(float(v), 1) for v in upp80],
                "lower_95_mg_dl": [round(float(v), 1) for v in low95],
                "upper_95_mg_dl": [round(float(v), 1) for v in upp95],
                "mean_uncertainty_std": round(float(np.mean(std_unc)), 2)
            },
            "hybrid_components": {
                "neural_prediction_mg_dl": [round(float(v), 1) for v in y_neural_v1_np],
                "ode_simulation_mg_dl": [round(float(v), 1) for v in y_ode_v1_np],
                "neural_weight_alpha": [round(float(v), 3) for v in alpha_v1_np],
                "effective_physics_weight": [round(float(v), 3) for v in w_phys],
                "mean_neural_weight_pct": round(float(np.mean(alpha_v1_np)) * 100.0, 1)
            },
            "risk_assessment": {
                "primary_status": risk_assessment.primary_status,
                "alert_level": risk_assessment.alert_level,
                "hypo_1h_prob": risk_assessment.hypo_risk_1h_prob,
                "hypo_2h_prob": risk_assessment.hypo_risk_2h_prob,
                "hypo_4h_prob": risk_assessment.hypo_risk_4h_prob,
                "hyper_2h_prob": risk_assessment.hyper_risk_2h_prob,
                "hyper_4h_prob": risk_assessment.hyper_risk_4h_prob,
                "nadir_mg_dl": risk_assessment.trajectory_nadir_mg_dl,
                "time_to_nadir_min": risk_assessment.time_to_nadir_min,
                "peak_mg_dl": risk_assessment.trajectory_peak_mg_dl,
                "time_to_peak_min": risk_assessment.time_to_peak_min,
                "projected_hypo_duration_min": risk_assessment.projected_hypo_duration_min,
                "active_alerts": risk_assessment.active_alerts
            },
            "explanation": {
                "headline": explanation.headline,
                "trend_summary": explanation.trend_summary,
                "metabolic_factors": explanation.metabolic_factors,
                "hybrid_attribution": explanation.hybrid_attribution,
                "uncertainty_rationale": explanation.uncertainty_rationale,
                "key_takeaway": explanation.key_takeaway
            },
            "wearable_context_logged": wearable_context_logged,
            "record_id": None,
            "model_version": ModelVersion.COMBINATION_C.value,
            "traceability": trace,
            "telemetry": telemetry
        }
