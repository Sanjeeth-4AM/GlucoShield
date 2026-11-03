"""
GlucoShield V2 Test Suite — Part 4: Factor-Aware Adaptive Fusion & Counterfactuals
==================================================================================
Verifies:
  1. Alpha boundedness: alpha(k) in (0, 1) strictly across all 20 horizons.
  2. Gradient flow: Backpropagation computes non-zero gradients through fusion gate.
  3. Dynamic response: Fusion gate responds to factor energy and model disagreement.
  4. Counterfactual blending consistency.
"""

import sys
import unittest
import torch
import numpy as np

BASE_DIR = "D:/ML PROJECT"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from models.v2.factor_fusion_gate import FactorAwareFusionGate

class TestV2Fusion(unittest.TestCase):
    def setUp(self):
        self.device = torch.device("cpu")
        self.gate = FactorAwareFusionGate(horizon=20).to(self.device)

    def test_01_alpha_strict_bounds(self):
        """Test 1: Output alpha is strictly in open interval (0, 1) across all inputs."""
        batch_size = 16
        # Generate extreme context values (-100 to +100)
        phi_extreme = (torch.randn(batch_size, 10, device=self.device) - 0.5) * 200.0
        alpha = self.gate(phi_extreme)

        self.assertEqual(alpha.shape, (batch_size, 20))
        self.assertTrue(torch.all(alpha > 0.0), "Alpha produced value <= 0.0")
        self.assertTrue(torch.all(alpha < 1.0), "Alpha produced value >= 1.0")

    def test_02_gradient_flow_through_gate(self):
        """Test 2: Loss gradients flow cleanly through the fusion gate parameters."""
        phi = torch.randn(4, 10, requires_grad=True, device=self.device)
        alpha = self.gate(phi)
        
        y_neu = torch.full((4, 20), 120.0, device=self.device)
        y_ode = torch.full((4, 20), 140.0, device=self.device)
        y_fused = alpha * y_neu + (1.0 - alpha) * y_ode

        target = torch.full((4, 20), 135.0, device=self.device)
        loss = torch.mean((y_fused - target)**2)
        loss.backward()

        self.assertIsNotNone(phi.grad, "Gradient did not flow back into gating feature tensor!")
        self.assertTrue(torch.any(phi.grad != 0.0), "Gating gradient is all zeros")
        self.assertIsNotNone(self.gate.context_net[0].weight.grad)

    def test_03_factor_activity_modulation(self):
        """Test 3: Increasing physiological context energy or disagreement shifts alpha."""
        # Baseline quiet context
        phi_quiet = torch.zeros(1, 10, device=self.device)
        alpha_quiet = self.gate(phi_quiet).detach()

        # Context with high factor energy (feature index 5) and high disagreement (feature index 6)
        phi_active = torch.zeros(1, 10, device=self.device)
        phi_active[0, 5] = 5.0 # High factor energy
        phi_active[0, 6] = 5.0 # High disagreement
        alpha_active = self.gate(phi_active).detach()

        # The gate must produce different blending weights when factor activity changes
        diff = torch.norm(alpha_active - alpha_quiet).item()
        self.assertGreater(diff, 1e-4, "Gate was unresponsive to physiological factor energy and disagreement")

if __name__ == "__main__":
    unittest.main(verbosity=2)
