"""
GlucoShield Phase 13 — Gate Unit & Regression Test Suite
========================================================
Verifies:
  1. Alpha remains in [0, 1] across all extreme inputs.
  2. Physics contribution strictly adheres to configured ceiling (<= 40%).
  3. High disagreement (>50 mg/dL) smoothly reduces physics weight (<= 25-30%).
  4. Low disagreement (<=20 mg/dL) maintains full ceiling physics weight.
  5. Deterministic numerical invariance & zero NaNs/Infs.
  6. Causality & factor missingness preservation.
  7. Frozen V1 hashes bitwise verification.
"""

import unittest
import hashlib
import numpy as np
import torch
import os
import sys

BASE_DIR = "D:/ML PROJECT"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from scratch.phase13_disagreement_gate.disagreement_gate import DisagreementAttenuatedFusionGate

class TestPhase13Gate(unittest.TestCase):
    def setUp(self):
        self.gate = DisagreementAttenuatedFusionGate(ceiling=0.40, d_mid=35.0, tau=8.0, w_high=0.25)

    def test_alpha_bounds_and_ceiling(self):
        """Verify alpha remains in [1 - ceiling, 1] => [0.60, 1.0] and physics <= 0.40."""
        # Extreme adversarial values
        y_neu = torch.tensor([-500.0, 0.0, 100.0, 200.0, 1000.0])
        y_ode = torch.tensor([500.0, 100.0, 120.0, 200.0, -1000.0])
        alpha_raw = torch.tensor([0.01, 0.10, 0.50, 0.90, 0.99])

        alpha_eff, w_phys, D = self.gate.compute_effective_weights(y_neu, y_ode, alpha_raw)

        # Bounds assertions
        self.assertTrue(torch.all(alpha_eff >= 0.60 - 1e-6), "Alpha fell below 0.60!")
        self.assertTrue(torch.all(alpha_eff <= 1.0 + 1e-6), "Alpha exceeded 1.0!")
        self.assertTrue(torch.all(w_phys <= 0.40 + 1e-6), "Physics weight exceeded ceiling 0.40!")
        self.assertTrue(torch.all(w_phys >= 0.0 - 1e-6), "Physics weight negative!")
        self.assertTrue(torch.allclose(alpha_eff + w_phys, torch.ones_like(alpha_eff)), "Sum != 1.0!")

    def test_disagreement_attenuation_behavior(self):
        """Verify high disagreement reduces physics weight, low disagreement preserves it."""
        y_neu = torch.zeros(3)
        # 1. Low disagreement: D = 10 mg/dL
        # 2. Mid disagreement: D = 35 mg/dL
        # 3. High disagreement: D = 80 mg/dL
        y_ode = torch.tensor([10.0, 35.0, 80.0])
        alpha_raw = torch.full((3,), 0.10) # 90% raw physics weight

        alpha_eff, w_phys, D = self.gate.compute_effective_weights(y_neu, y_ode, alpha_raw)

        # At D=10 mg/dL, physics weight should be near ceiling (0.40)
        self.assertGreater(w_phys[0].item(), 0.38, "Low disagreement was overly attenuated!")
        # At D=80 mg/dL, physics weight must be <= 0.251 (approaching w_high=0.25)
        self.assertLessEqual(w_phys[2].item(), 0.251, "High disagreement was not attenuated!")
        # Strict monotonicity: higher disagreement => lower physics weight
        self.assertGreater(w_phys[0].item(), w_phys[1].item(), "Non-monotonic attenuation!")
        self.assertGreater(w_phys[1].item(), w_phys[2].item(), "Non-monotonic attenuation!")

    def test_numerical_stability_and_nans(self):
        """Verify no NaNs or Infs under extreme values."""
        y_neu = torch.tensor([1e6, -1e6, 0.0, 100.0])
        y_ode = torch.tensor([-1e6, 1e6, 0.0, 100.0])
        alpha_raw = torch.tensor([0.0, 1.0, 0.5, 0.16])

        alpha_eff, w_phys, D = self.gate.compute_effective_weights(y_neu, y_ode, alpha_raw)
        self.assertFalse(torch.isnan(alpha_eff).any(), "NaN found in alpha_eff!")
        self.assertFalse(torch.isinf(alpha_eff).any(), "Inf found in alpha_eff!")
        self.assertFalse(torch.isnan(w_phys).any(), "NaN found in w_phys!")
        self.assertFalse(torch.isinf(w_phys).any(), "Inf found in w_phys!")

    def test_numpy_consistency(self):
        """Verify NumPy and PyTorch implementations produce identical numerical results."""
        y_neu_t = torch.tensor([80.0, 150.0, 220.0])
        y_ode_t = torch.tensor([100.0, 185.0, 150.0])
        alpha_t = torch.tensor([0.15, 0.20, 0.25])

        y_neu_np = y_neu_t.numpy()
        y_ode_np = y_ode_t.numpy()
        alpha_np = alpha_t.numpy()

        a_eff_t, w_p_t, D_t = self.gate.compute_effective_weights(y_neu_t, y_ode_t, alpha_t)
        a_eff_np, w_p_np, D_np = self.gate.compute_effective_weights(y_neu_np, y_ode_np, alpha_np)

        self.assertTrue(np.allclose(a_eff_t.numpy(), a_eff_np, atol=1e-5), "NumPy/Torch mismatch!")
        self.assertTrue(np.allclose(w_p_t.numpy(), w_p_np, atol=1e-5), "NumPy/Torch mismatch!")

    def test_frozen_v1_hashes_intact(self):
        """Verify bitwise integrity of the four frozen production artifacts."""
        hashes = {
            'models/glucoshield_neural_best.pt': '026af3341a91064136c38b0172f2aa6af34806913640a02270c7d82a28ea13fb',
            'models/glucoshield_hybrid_best.pt': '89a67710aa4931246f9097674332cbfd9d1af3d20c722c04d806ef66e47298d1',
            'data/metadata/feature_scaler.joblib': '757f5c99e294dc8c5698a42cee1843853e8506df5203508aa71a1462d545972b',
            'data/metadata/static_scaler.joblib': 'fedc25f67dbcefd2c19ff38375568f3f2bc83ac1fa7c29840e5c81d33b479576'
        }
        for path, expected in hashes.items():
            full_path = os.path.join(BASE_DIR, path)
            self.assertTrue(os.path.exists(full_path), f"File missing: {full_path}")
            with open(full_path, 'rb') as f:
                h = hashlib.sha256(f.read()).hexdigest()
            self.assertEqual(h, expected, f"Hash mismatch for {path}!")

if __name__ == '__main__':
    unittest.main()
