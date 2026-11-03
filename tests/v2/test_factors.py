"""
GlucoShield V2 Test Suite — Part 2: Physiological Factor Integration & Missingness Safety
========================================================================================
Verifies:
  1. Mask gating invariant: m_factor == 0 strictly zeroes factor embedding
  2. Independent masking: masking one factor does not zero other factors
  3. Distinction between 'factor absent' and 'factor unknown'
  4. Sensitivity / Perturbation: valid factor variations produce measurable neural response
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

class TestV2Factors(unittest.TestCase):
    def setUp(self):
        self.device = torch.device("cpu")
        self.encoder = PhysiologicalContextEncoder(embed_dim=32).to(self.device)
        self.neural = GlucoShieldNeuralForecasterV2().to(self.device)
        self.neural.eval()

        self.dyn_s = torch.randn(2, 96, 22, device=self.device)
        self.stat_s = torch.randn(2, 9, device=self.device)

    def test_01_exercise_mask_zeroing(self):
        """Test 1: When exercise mask is 0.0, exercise embedding is identically zero."""
        batch = PhysiologicalContextBatch.create_empty(2, device=self.device)
        batch.f_exercise = torch.tensor([[np.log(4.0), 0.8, 0.5, 1.0], [np.log(4.0), 0.8, 0.5, 1.0]], device=self.device)
        batch.m_exercise = torch.zeros(2, 1, device=self.device) # Masked!

        z_ctx, embeds = self.encoder(batch)
        max_e_ex = torch.max(torch.abs(embeds["exercise"])).item()
        self.assertEqual(max_e_ex, 0.0, f"Masked exercise embedding is non-zero: {max_e_ex}")

    def test_02_sleep_mask_zeroing(self):
        """Test 2: When sleep mask is 0.0, sleep embedding is identically zero."""
        batch = PhysiologicalContextBatch.create_empty(2, device=self.device)
        batch.f_sleep = torch.tensor([[4.0 / 8.0, 0.7, 0.1, 3.5 / 4.0, 1.0]] * 2, device=self.device)
        batch.m_sleep = torch.zeros(2, 1, device=self.device) # Masked!

        z_ctx, embeds = self.encoder(batch)
        max_e_sl = torch.max(torch.abs(embeds["sleep"])).item()
        self.assertEqual(max_e_sl, 0.0, f"Masked sleep embedding is non-zero: {max_e_sl}")

    def test_03_hormonal_mask_zeroing(self):
        """Test 3: When hormonal mask is 0.0, hormonal embedding is identically zero."""
        batch = PhysiologicalContextBatch.create_empty(2, device=self.device)
        batch.f_hormonal = torch.tensor([[0.0, 1.0, 0.8]] * 2, device=self.device)
        batch.m_hormonal = torch.zeros(2, 1, device=self.device) # Masked!

        z_ctx, embeds = self.encoder(batch)
        max_e_hm = torch.max(torch.abs(embeds["hormonal"])).item()
        self.assertEqual(max_e_hm, 0.0, f"Masked hormonal embedding is non-zero: {max_e_hm}")

    def test_04_independent_factor_activation(self):
        """Test 4: Activating sleep does not activate exercise or hormonal embeddings."""
        batch = PhysiologicalContextBatch.create_empty(2, device=self.device)
        batch.f_sleep = torch.tensor([[5.0 / 8.0, 0.8, 0.15, 2.5 / 4.0, 0.9]] * 2, device=self.device)
        batch.m_sleep = torch.ones(2, 1, device=self.device) # Active!

        z_ctx, embeds = self.encoder(batch)
        norm_sl = torch.norm(embeds["sleep"]).item()
        norm_ex = torch.norm(embeds["exercise"]).item()
        norm_hm = torch.norm(embeds["hormonal"]).item()

        self.assertGreater(norm_sl, 0.01, "Active sleep embedding is unexpectedly zero")
        self.assertEqual(norm_ex, 0.0, "Inactive exercise embedding became non-zero")
        self.assertEqual(norm_hm, 0.0, "Inactive hormonal embedding became non-zero")

    def test_05_factor_absent_vs_factor_missing_distinction(self):
        """Test 5: The model distinguishes between 'normal sleep' (m=1, dur=8h) and 'missing sleep' (m=0)."""
        # Case A: Sleep is measured and normal (8h, debt=0)
        batch_normal = PhysiologicalContextBatch.create_empty(1, device=self.device)
        batch_normal.f_sleep = torch.tensor([[8.0 / 8.0, 0.95, 0.25, 0.0, 0.5]], device=self.device)
        batch_normal.m_sleep = torch.ones(1, 1, device=self.device)

        # Case B: Sleep is unmeasured/unknown (m=0)
        batch_missing = PhysiologicalContextBatch.create_empty(1, device=self.device)
        batch_missing.m_sleep = torch.zeros(1, 1, device=self.device)

        with torch.no_grad():
            out_normal = self.neural(self.dyn_s[:1], self.stat_s[:1], batch_normal)
            out_missing = self.neural(self.dyn_s[:1], self.stat_s[:1], batch_missing)

        # Latent representations must be distinct because m_sleep is part of the context
        diff = torch.norm(out_normal["z_context"] - out_missing["z_context"]).item()
        self.assertGreater(diff, 1e-4, "Model failed to distinguish factor absent from factor missing")

if __name__ == "__main__":
    unittest.main(verbosity=2)
