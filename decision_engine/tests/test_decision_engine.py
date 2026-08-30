"""
GlucoShield Decision Engine - Comprehensive Unit Tests
======================================================
Tests uncertainty estimation, interval calibration, clinical risk categorization,
natural language explanations, safety guardrails, and pipeline integration.
"""

import sys
import os
import unittest
import torch
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from decision_engine.uncertainty import UncertaintyEstimator, PredictionInterval
from decision_engine.calibration import evaluate_interval_calibration
from decision_engine.risk_engine import ClinicalRiskEngine
from decision_engine.safety import SafetyGuardrails
from decision_engine.explanation import ClinicalExplainer
from neural.models import GlucoShieldMultiTaskRNN
from physiology.hybrid_fusion import GlucoShieldHybridForecaster

class TestDecisionEngine(unittest.TestCase):
    def setUp(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def test_01_uncertainty_interval_properties(self):
        """Test 1: 95% interval width must be strictly larger than 80% interval width."""
        estimator = UncertaintyEstimator()
        y_hyb = np.full(20, 120.0)
        y_neu = np.full(20, 125.0)
        y_ode = np.full(20, 115.0)
        sigma_neu = np.full(20, 8.0)

        interval = estimator.construct_prediction_intervals(y_hyb, y_neu, y_ode, sigma_neu)
        
        width_80 = interval.upper_80 - interval.lower_80
        width_95 = interval.upper_95 - interval.lower_95
        
        self.assertTrue(np.all(width_95 > width_80), "95% interval must be strictly wider than 80% interval")
        self.assertTrue(np.all(interval.lower_80 >= 20.0), "Lower bound must respect glucose physical floor")

    def test_02_calibration_evaluation(self):
        """Test 2: Calibration evaluation correctly computes empirical coverage and width."""
        N = 100
        H = 20
        y_true = np.random.normal(120.0, 15.0, (N, H))
        l80 = y_true - 12.0
        u80 = y_true + 12.0
        l95 = y_true - 25.0
        u95 = y_true + 25.0

        calib_res = evaluate_interval_calibration(y_true, l80, u80, l95, u95)
        self.assertEqual(calib_res["overall_coverage_80_pct"], 100.0)
        self.assertEqual(calib_res["overall_coverage_95_pct"], 100.0)
        self.assertAlmostEqual(calib_res["mean_width_80_mg_dl"], 24.0, places=1)

    def test_03_risk_engine_stratification(self):
        """Test 3: Severe nadir (<54 mg/dL) produces CRITICAL alert; mild nadir (<70 mg/dL) produces WARNING."""
        risk_eng = ClinicalRiskEngine()
        
        # Severe crash scenario
        crash_traj = np.linspace(110.0, 48.0, 20)
        crash_probs = np.array([0.75, 0.85, 0.90, 0.10, 0.05])
        res_crit = risk_eng.evaluate_risk(120.0, crash_traj, crash_probs)
        self.assertEqual(res_crit.alert_level, "CRITICAL")
        self.assertIn("Severe Hypoglycemia", res_crit.active_alerts[0])

        # Mild hypo scenario
        mild_traj = np.linspace(100.0, 65.0, 20)
        mild_probs = np.array([0.40, 0.50, 0.55, 0.10, 0.05])
        res_warn = risk_eng.evaluate_risk(105.0, mild_traj, mild_probs)
        self.assertEqual(res_warn.alert_level, "WARNING")

    def test_04_safety_guardrails(self):
        """Test 4: Input validator flags physiologically impossible or extreme dosing."""
        warns = SafetyGuardrails.validate_inputs(current_glucose=15.0, proposed_carbs=500.0, proposed_bolus=80.0)
        self.assertEqual(len(warns), 3)

    def test_05_explainer_attribution(self):
        """Test 5: Explainer generates structured report containing trend, IOB/COB, and hybrid split."""
        explainer = ClinicalExplainer()
        traj = np.linspace(130.0, 185.0, 20)
        rep = explainer.generate_explanation(
            current_glucose=130.0,
            trajectory=traj,
            iob_units=1.5,
            cob_grams=45.0,
            mean_alpha=0.65,
            mean_uncertainty_std=16.5,
            primary_status="RISING"
        )
        self.assertIn("Carbohydrates on Board", rep.metabolic_factors[0])
        self.assertIn("65% Deep Recurrent Sequence Weight", rep.hybrid_attribution)
        self.assertTrue(len(rep.headline) > 0)

if __name__ == "__main__":
    unittest.main(verbosity=2)
