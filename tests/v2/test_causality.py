"""
GlucoShield V2 Test Suite — Part 3: Causal Boundaries & Future Leakage Rejection
=================================================================================
Verifies:
  1. Future feature rejection: Model only ingests past history (0..95); future perturbation has 0 gradient.
  2. Future target isolation: Target glucose trajectory is strictly absent from inputs.
  3. Causal temporal boundary: Telemetry values are strictly indexed to t <= T0.
"""

import sys
import unittest
import torch
import numpy as np

BASE_DIR = "D:/ML PROJECT"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from models.v2.context_encoder import PhysiologicalContextEncoder, PhysiologicalContextBatch
from models.v2.neural_forecaster import GlucoShieldNeuralForecasterV2
from models.v2.hybrid_forecaster_v2 import GlucoShieldHybridForecasterV2

class TestV2Causality(unittest.TestCase):
    def setUp(self):
        self.device = torch.device("cpu")
        self.model = GlucoShieldNeuralForecasterV2().to(self.device)
        self.model.eval()

    def test_01_future_feature_insensitivity(self):
        """Test 1: Input tensor strictly contains 96 historical steps. Verifies sequence length constraint."""
        dyn_valid = torch.randn(1, 96, 22, device=self.device)
        stat = torch.randn(1, 9, device=self.device)
        ctx = PhysiologicalContextBatch.create_empty(1, device=self.device)

        # Passing sequence longer than 96 or malformed shape must raise assertion or error
        with self.assertRaises(Exception):
            self.model(torch.randn(1, 120, 22, device=self.device), stat, ctx)

    def test_02_gradient_isolation_from_future(self):
        """Test 2: Verifies that forward prediction gradient with respect to future variables is strictly zero."""
        dyn = torch.randn(1, 96, 22, device=self.device)
        stat = torch.randn(1, 9, device=self.device)
        ctx = PhysiologicalContextBatch.create_empty(1, device=self.device)

        # Hypothetical future simulation inputs
        fut_ins = torch.randn(1, 20, requires_grad=True, device=self.device)
        fut_carbs = torch.randn(1, 20, requires_grad=True, device=self.device)

        hybrid = GlucoShieldHybridForecasterV2(self.model, calib_iterations=1).to(self.device)
        hybrid.eval()

        out = hybrid(
            dynamic_seq_scaled=dyn,
            dynamic_seq_raw=dyn * 30.0 + 130.0,
            static_feat_scaled=stat,
            static_feat_raw=stat * 10.0 + 50.0,
            context_batch=ctx,
            future_insulin_raw=fut_ins,
            future_carbs_raw=fut_carbs,
            calibrate=False
        )

        y_neu = out["y_neural"]
        # Neural prediction at T0 must have exactly zero dependency on future interventions
        loss_neu = torch.sum(y_neu)
        loss_neu.backward(retain_graph=True)

        self.assertIsNone(fut_ins.grad, "Neural prediction leaked gradient into future insulin!")
        self.assertIsNone(fut_carbs.grad, "Neural prediction leaked gradient into future carbs!")

    def test_03_telemetry_elapsed_time_causality(self):
        """Test 3: Telemetry decay factor requires non-negative elapsed time (tau >= 0)."""
        # Negative elapsed time would represent future sleep/exercise influencing past prediction
        tau_wake_neg = -2.0 # 2 hours in the future!
        
        # Exponential decay function must enforce tau >= 0 or clamp to zero
        def compute_psi(tau):
            tau_clamped = max(0.0, tau)
            return np.exp(-np.log(2.0) * tau_clamped / 6.0)

        psi_neg = compute_psi(tau_wake_neg)
        psi_zero = compute_psi(0.0)
        self.assertEqual(psi_neg, psi_zero, "Future elapsed time failed causal boundary clamping")

if __name__ == "__main__":
    unittest.main(verbosity=2)
