"""
GlucoShield Decision Engine - End-to-End Decision Pipeline
==========================================================
Unified clinical decision-support pipeline integrating Neural Forecaster V1,
Mechanistic Digital Twin, Hybrid Fusion, Uncertainty Intervals, Risk Engine,
Natural Language Explanations, and Counterfactual What-If Simulations.
"""

import torch
import numpy as np
from typing import Dict, Any, Optional, List

from neural.models import GlucoShieldMultiTaskRNN
from physiology.state import MetabolicState
from physiology.parameters import PhysiologicalParameters
from physiology.hybrid_fusion import GlucoShieldHybridForecaster
from physiology.simulator import CounterfactualSimulator
from decision_engine.uncertainty import UncertaintyEstimator, PredictionInterval
from decision_engine.risk_engine import ClinicalRiskEngine, RiskAssessment
from decision_engine.safety import SafetyGuardrails
from decision_engine.explanation import ClinicalExplainer, ExplanationReport

class EndToEndDecisionPipeline:
    """
    Complete end-to-end inference and clinical decision-support engine.
    """
    def __init__(
        self,
        hybrid_model: GlucoShieldHybridForecaster,
        device: torch.device = torch.device("cpu"),
        mc_samples: int = 16
    ):
        self.hybrid_model = hybrid_model.to(device)
        self.hybrid_model.eval()
        self.device = device
        
        self.uncertainty_estimator = UncertaintyEstimator(num_mc_samples=mc_samples)
        self.risk_engine = ClinicalRiskEngine(hypo_alert_threshold=0.35, hyper_alert_threshold=0.50)
        self.explainer = ClinicalExplainer()
        self.simulator = CounterfactualSimulator(horizon_steps=20, dt=1.0)

    def process_patient_window(
        self,
        dynamic_seq_scaled: torch.Tensor,   # (1, 96, 22)
        dynamic_seq_raw: torch.Tensor,      # (1, 96, 22)
        static_feat_scaled: torch.Tensor,   # (1, 9)
        static_feat_raw: torch.Tensor,      # (1, 9)
        what_if_carbs: Optional[float] = None,
        what_if_bolus: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Processes a single patient's 24-hour monitoring window through the entire backend suite.
        """
        # Ensure device
        d_s = dynamic_seq_scaled.to(self.device)
        d_r = dynamic_seq_raw.to(self.device)
        s_s = static_feat_scaled.to(self.device)
        s_r = static_feat_raw.to(self.device)

        current_glucose = float(d_r[0, -1, 0].item())
        current_iob = float(d_r[0, -1, 16].item())
        current_cob = float(d_r[0, -1, 19].item())

        # 1. Forward pass through Hybrid Forecaster
        with torch.no_grad():
            hybrid_out = self.hybrid_model(
                d_s, d_r, s_s, s_r, calibrate=True, return_components=True
            )

        y_hybrid_np = hybrid_out["trajectory"][0].cpu().numpy()
        y_neural_np = hybrid_out["y_neural"][0].cpu().numpy()
        y_ode_np = hybrid_out["y_ode"][0].cpu().numpy()
        alpha_np = hybrid_out["alpha"][0].cpu().numpy()
        risk_probs_np = hybrid_out["risk_probs"][0].cpu().numpy()
        state_t0 = hybrid_out["state_t0"]
        params_calib = hybrid_out["params_calib"]

        # 2. Uncertainty Estimation via MC-Dropout
        _, sigma_neural = self.uncertainty_estimator.estimate_mc_dropout(
            self.hybrid_model.neural_model, d_s, s_s
        )
        sigma_neural_np = sigma_neural[0].cpu().numpy()

        interval = self.uncertainty_estimator.construct_prediction_intervals(
            y_hybrid=y_hybrid_np,
            y_neural=y_neural_np,
            y_ode=y_ode_np,
            sigma_neural=sigma_neural_np
        )

        # 3. Clinical Risk Assessment
        risk_assessment = self.risk_engine.evaluate_risk(
            current_glucose=current_glucose,
            trajectory=y_hybrid_np,
            risk_probs=risk_probs_np,
            interval_lower_95=interval.lower_95
        )

        # 4. Clinical Explanation
        explanation = self.explainer.generate_explanation(
            current_glucose=current_glucose,
            trajectory=y_hybrid_np,
            iob_units=current_iob,
            cob_grams=current_cob,
            mean_alpha=float(np.mean(alpha_np)),
            mean_uncertainty_std=float(np.mean(interval.std_uncertainty)),
            primary_status=risk_assessment.primary_status
        )

        # 5. Counterfactual "What-If" Simulation (if requested)
        what_if_results = None
        if what_if_carbs is not None or what_if_bolus is not None:
            carbs_val = what_if_carbs if what_if_carbs is not None else 0.0
            bolus_val = what_if_bolus if what_if_bolus is not None else 0.0
            
            ins_scen = torch.zeros(1, 20, device=self.device)
            carbs_scen = torch.zeros(1, 20, device=self.device)
            ins_scen[0, 0] = bolus_val
            carbs_scen[0, 0] = carbs_val

            what_if_sim = self.simulator.simulate_scenario(
                state_t0, params_calib, ins_scen, carbs_scen,
                scenario_name=f"what_if_meal_{carbs_val:.0f}g_bolus_{bolus_val:.1f}U"
            )
            what_if_results = {
                "scenario_name": what_if_sim["scenario_name"],
                "simulated_trajectory": what_if_sim["simulated_glucose"][0].cpu().numpy().round(1).tolist(),
                "nadir_glucose": round(what_if_sim["nadir_glucose"].item(), 1),
                "time_to_nadir_min": int(what_if_sim["time_to_nadir_min"].item()),
                "peak_glucose": round(what_if_sim["peak_glucose"].item(), 1),
                "time_to_peak_min": int(what_if_sim["time_to_peak_min"].item()),
                "time_in_range_pct": round(what_if_sim["time_in_range_pct"].item(), 1),
                "warnings": what_if_sim["warnings"]
            }

        return {
            "disclaimer": SafetyGuardrails.RESEARCH_DISCLAIMER,
            "current_state": {
                "glucose_mg_dl": current_glucose,
                "iob_units": current_iob,
                "cob_grams": current_cob,
                "primary_status": risk_assessment.primary_status
            },
            "forecast": {
                "horizon_minutes": [15 * (k + 1) for k in range(20)],
                "point_forecast_mg_dl": y_hybrid_np.round(1).tolist(),
                "lower_80_mg_dl": interval.lower_80.round(1).tolist(),
                "upper_80_mg_dl": interval.upper_80.round(1).tolist(),
                "lower_95_mg_dl": interval.lower_95.round(1).tolist(),
                "upper_95_mg_dl": interval.upper_95.round(1).tolist(),
                "mean_uncertainty_std": round(float(np.mean(interval.std_uncertainty)), 2)
            },
            "hybrid_components": {
                "neural_prediction_mg_dl": y_neural_np.round(1).tolist(),
                "ode_simulation_mg_dl": y_ode_np.round(1).tolist(),
                "neural_weight_alpha": alpha_np.round(3).tolist(),
                "mean_neural_weight_pct": round(float(np.mean(alpha_np)) * 100.0, 1)
            },
            "risk_assessment": {
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
            "what_if_simulation": what_if_results
        }
