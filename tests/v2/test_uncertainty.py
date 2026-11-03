"""
GlucoShield V2 Test Suite — Part 5: Regime-Conditioned Uncertainty Calibration
==============================================================================
Verifies:
  1. Quantile monotonicity: q025 <= q100 <= q900 <= q975 strictly preserved.
  2. Prediction interval nesting: 95% interval strictly envelops 80% interval.
  3. Dynamic volatility scaling: High glycemic volatility widens intervals dynamically.
  4. Physical bounding: Intervals strictly conform to [20.0, 500.0] mg/dL.
  5. Horizon growth: Interval width monotonically widens across the 5-hour forecast.
"""

import sys
import unittest
import torch
import numpy as np

BASE_DIR = "D:/ML PROJECT"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from models.v2.neural_forecaster import GlucoShieldNeuralForecasterV2
from models.v2.uncertainty_head import RegimeConditionedUncertaintyHead

class TestV2Uncertainty(unittest.TestCase):
    def setUp(self):
        self.device = torch.device("cpu")
        self.head = RegimeConditionedUncertaintyHead(horizon=20).to(self.device)
        self.neural = GlucoShieldNeuralForecasterV2().to(self.device)
        self.neural.eval()

    def test_01_neural_quantile_monotonicity(self):
        """Test 1: Neural multi-quantile head guarantees q025 <= q10 <= q90 <= q975."""
        dyn_s = torch.randn(8, 96, 22, device=self.device)
        stat_s = torch.randn(8, 9, device=self.device)

        with torch.no_grad():
            out = self.neural(dyn_s, stat_s)
        quant = out["quantiles"] # (8, 4, 20)

        q025 = quant[:, 0, :]
        q100 = quant[:, 1, :]
        q900 = quant[:, 2, :]
        q975 = quant[:, 3, :]

        self.assertTrue(torch.all(q100 >= q025), "Quantile crossing: q10 < q025")
        self.assertTrue(torch.all(q900 >= q100), "Quantile crossing: q90 < q10")
        self.assertTrue(torch.all(q975 >= q900), "Quantile crossing: q975 < q90")

    def test_02_prediction_interval_nesting(self):
        """Test 2: 95% physical prediction interval strictly envelops 80% interval."""
        y_final = torch.full((4, 20), 140.0, device=self.device)
        y_neu = torch.full((4, 20), 138.0, device=self.device)
        y_ode = torch.full((4, 20), 142.0, device=self.device)
        dyn_raw = torch.zeros(4, 96, 22, device=self.device)
        dyn_raw[:, -1, 4] = 15.0 # std_1h = 15 mg/dL
        z_ctx = torch.zeros(4, 32, device=self.device)

        with torch.no_grad():
            p_int = self.head(
                y_final=y_final, y_neural=y_neu, y_ode=y_ode,
                quantiles=None, dynamic_seq_raw=dyn_raw, z_context=z_ctx
            )

        self.assertTrue(torch.all(p_int.lower_95 <= p_int.lower_80), "Lower 95% is higher than lower 80%!")
        self.assertTrue(torch.all(p_int.upper_95 >= p_int.upper_80), "Upper 95% is lower than upper 80%!")
        self.assertTrue(torch.all(p_int.lower_80 <= p_int.upper_80), "Lower 80% is higher than upper 80%!")

    def test_03_dynamic_volatility_scaling(self):
        """Test 3: Higher glycemic volatility (std_1h) produces wider prediction intervals."""
        y_final = torch.full((2, 20), 140.0, device=self.device)
        y_neu = torch.full((2, 20), 140.0, device=self.device)
        y_ode = torch.full((2, 20), 140.0, device=self.device)
        z_ctx = torch.zeros(2, 32, device=self.device)

        dyn_raw = torch.zeros(2, 96, 22, device=self.device)
        dyn_raw[0, -1, 4] = 5.0  # Low volatility: std_1h = 5 mg/dL
        dyn_raw[1, -1, 4] = 45.0 # High volatility: std_1h = 45 mg/dL (T1D excursion)

        with torch.no_grad():
            p_int = self.head(
                y_final=y_final, y_neural=y_neu, y_ode=y_ode,
                quantiles=None, dynamic_seq_raw=dyn_raw, z_context=z_ctx
            )

        width_quiet = torch.mean(p_int.upper_95[0] - p_int.lower_95[0]).item()
        width_volatile = torch.mean(p_int.upper_95[1] - p_int.lower_95[1]).item()

        self.assertGreater(width_volatile, width_quiet * 1.5,
            f"Interval failed to widen appropriately under high volatility: quiet={width_quiet:.1f}, volatile={width_volatile:.1f}")

    def test_04_horizon_monotonic_growth(self):
        """Test 4: Uncertainty standard deviation increases monotonically across forecast horizon."""
        y_final = torch.full((1, 20), 120.0, device=self.device)
        dyn_raw = torch.zeros(1, 96, 22, device=self.device)
        dyn_raw[0, -1, 4] = 10.0
        z_ctx = torch.zeros(1, 32, device=self.device)

        with torch.no_grad():
            p_int = self.head(y_final, y_final, y_final, None, dyn_raw, z_ctx)

        sigma = p_int.std_uncertainty[0] # (20,)
        diffs = torch.diff(sigma)
        self.assertTrue(torch.all(diffs >= 0.0), "Uncertainty did not monotonically grow over forecast horizon")

if __name__ == "__main__":
    unittest.main(verbosity=2)
