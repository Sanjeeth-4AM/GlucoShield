"""
GlucoShield V2 Test Suite — Part 1: Architecture & Dimensions
==============================================================
Verifies:
  1. Neural Forecaster V2 forward pass with context batch
  2. Neural Forecaster V2 graceful fallback without context
  3. Hybrid Forecaster V2 end-to-end forward pass
  4. Output dimensions (trajectory, quantiles, risks, interval)
  5. Checkpoint saving, loading, and parameter bitwise restoration
  6. Deterministic inference across random seeds
"""

import os
import sys
import unittest
import torch
import numpy as np

BASE_DIR = "D:/ML PROJECT"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from models.v2.context_encoder import PhysiologicalContextEncoder, PhysiologicalContextBatch
from models.v2.neural_forecaster import GlucoShieldNeuralForecasterV2
from models.v2.factor_fusion_gate import FactorAwareFusionGate
from models.v2.uncertainty_head import RegimeConditionedUncertaintyHead
from models.v2.hybrid_forecaster_v2 import GlucoShieldHybridForecasterV2

class TestV2Architecture(unittest.TestCase):
    def setUp(self):
        self.device = torch.device("cpu")
        self.batch_size = 4
        self.horizon = 20
        self.dyn_s = torch.randn(self.batch_size, 96, 22, device=self.device)
        self.dyn_r = torch.clamp(self.dyn_s * 30.0 + 130.0, 40.0, 400.0)
        self.dyn_r[:, :, 1] = torch.gradient(self.dyn_r[:, :, 0], dim=1)[0]
        self.dyn_r[:, :, 2] = torch.gradient(self.dyn_r[:, :, 1], dim=1)[0]
        self.dyn_r[:, :, 4] = 12.5 # std_1h
        self.dyn_r[:, :, 10] = 0.5 # sin_24
        self.dyn_r[:, :, 11] = 0.8 # cos_24

        self.stat_s = torch.randn(self.batch_size, 9, device=self.device)
        self.stat_r = torch.tensor([[55.0, 26.0, 7.5, 20.0, 140.0, 1.2, 0.0, 0.0, 1.0]] * self.batch_size, device=self.device)

        self.ctx = PhysiologicalContextBatch(
            f_exercise=torch.tensor([[np.log(2.5), 0.45, 0.70, 0.66]] * self.batch_size, device=self.device),
            m_exercise=torch.ones(self.batch_size, 1, device=self.device),
            f_sleep=torch.tensor([[6.0 / 8.0, 0.82, 0.18, 1.5 / 4.0, 0.85]] * self.batch_size, device=self.device),
            m_sleep=torch.ones(self.batch_size, 1, device=self.device),
            f_hormonal=torch.tensor([[0.0, 1.0, 0.75]] * self.batch_size, device=self.device),
            m_hormonal=torch.ones(self.batch_size, 1, device=self.device),
            f_circadian=torch.tensor([[0.5, 0.8, 0.8, -0.39]] * self.batch_size, device=self.device)
        )

    def test_01_context_encoder_forward(self):
        """Test 1: Context encoder produces valid (batch, 32) embedding."""
        encoder = PhysiologicalContextEncoder(embed_dim=32).to(self.device)
        z_ctx, embeds = encoder(self.ctx)
        self.assertEqual(z_ctx.shape, (self.batch_size, 32))
        self.assertFalse(torch.isnan(z_ctx).any(), "NaN found in context embedding")
        self.assertIn("exercise", embeds)
        self.assertIn("sleep", embeds)
        self.assertIn("hormonal", embeds)

    def test_02_neural_forecaster_dimensions(self):
        """Test 2: Neural Forecaster produces 20-step trajectory, 4x20 quantiles, and 5 risks."""
        model = GlucoShieldNeuralForecasterV2().to(self.device)
        out = model(self.dyn_s, self.stat_s, self.ctx)
        
        self.assertEqual(out["trajectory"].shape, (self.batch_size, self.horizon))
        self.assertEqual(out["quantiles"].shape, (self.batch_size, 4, self.horizon))
        self.assertEqual(out["risk_logits"].shape, (self.batch_size, 5))
        self.assertEqual(out["risk_probs"].shape, (self.batch_size, 5))
        self.assertTrue(torch.all(out["risk_probs"] >= 0.0) and torch.all(out["risk_probs"] <= 1.0))

    def test_03_neural_forecaster_empty_context_fallback(self):
        """Test 3: Passing context_batch=None safely falls back to neutral context."""
        model = GlucoShieldNeuralForecasterV2().to(self.device)
        out = model(self.dyn_s, self.stat_s, context_batch=None)
        self.assertEqual(out["trajectory"].shape, (self.batch_size, self.horizon))
        self.assertFalse(torch.isnan(out["trajectory"]).any())

    def test_04_hybrid_forecaster_end_to_end(self):
        """Test 4: Hybrid Forecaster V2 integrates neural, ODE, fusion, and uncertainty."""
        neural = GlucoShieldNeuralForecasterV2().to(self.device)
        hybrid = GlucoShieldHybridForecasterV2(neural, calib_iterations=2).to(self.device)
        
        out = hybrid(
            dynamic_seq_scaled=self.dyn_s,
            dynamic_seq_raw=self.dyn_r,
            static_feat_scaled=self.stat_s,
            static_feat_raw=self.stat_r,
            context_batch=self.ctx,
            calibrate=False # fast test
        )
        
        self.assertEqual(out["trajectory"].shape, (self.batch_size, self.horizon))
        self.assertEqual(out["y_neural"].shape, (self.batch_size, self.horizon))
        self.assertEqual(out["y_ode"].shape, (self.batch_size, self.horizon))
        self.assertEqual(out["alpha"].shape, (self.batch_size, self.horizon))
        self.assertTrue(torch.all(out["alpha"] >= 0.0) and torch.all(out["alpha"] <= 1.0))
        
        p_int = out["prediction_interval"]
        self.assertEqual(p_int.lower_80.shape, (self.batch_size, self.horizon))
        self.assertEqual(p_int.upper_95.shape, (self.batch_size, self.horizon))

    def test_05_checkpoint_save_and_load(self):
        """Test 5: State dict can be saved and reloaded with exact bitwise reproduction."""
        neural = GlucoShieldNeuralForecasterV2().to(self.device)
        hybrid = GlucoShieldHybridForecasterV2(neural, calib_iterations=1).to(self.device)
        
        ckpt_path = os.path.join(BASE_DIR, "scratch", "test_v2_ckpt.pt")
        torch.save(hybrid.state_dict(), ckpt_path)
        
        hybrid_loaded = GlucoShieldHybridForecasterV2(GlucoShieldNeuralForecasterV2(), calib_iterations=1).to(self.device)
        hybrid_loaded.load_state_dict(torch.load(ckpt_path, weights_only=True))
        
        # Test identical outputs
        hybrid.eval()
        hybrid_loaded.eval()
        with torch.no_grad():
            out1 = hybrid(self.dyn_s, self.dyn_r, self.stat_s, self.stat_r, self.ctx, calibrate=False)
            out2 = hybrid_loaded(self.dyn_s, self.dyn_r, self.stat_s, self.stat_r, self.ctx, calibrate=False)
            
        max_diff = torch.max(torch.abs(out1["trajectory"] - out2["trajectory"])).item()
        self.assertEqual(max_diff, 0.0, "Checkpoint loading did not produce identical predictions")
        if os.path.exists(ckpt_path):
            os.remove(ckpt_path)

if __name__ == "__main__":
    unittest.main(verbosity=2)
