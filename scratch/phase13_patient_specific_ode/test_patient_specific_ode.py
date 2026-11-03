"""
Unit & Invariant Tests for Patient-Specific Online ODE Adaptation
================================================================
Covers Section 14 requirements:
  - Causal updates only (no future data)
  - Parameter hard bounds enforcement (S_I in [1e-5, 5e-3], G_b in [70, 220])
  - NaN/Inf immunity and resilience
  - No exploding parameter trajectories
  - Deterministic inference
  - Adaptation disabled reproduces baseline prior
  - Zero adaptation rate reproduces baseline prior
"""

import unittest
import numpy as np
import torch
from scratch.phase13_patient_specific_ode.patient_ode_adapter import (
    PatientOdeAdapter,
    PatientOdeConfig,
    ParticipantState
)

class TestPatientSpecificOde(unittest.TestCase):
    def setUp(self):
        self.config = PatientOdeConfig()
        self.adapter = PatientOdeAdapter(self.config)

    def test_causal_updates_only(self):
        """Verify update_window uses ONLY the supplied 4-step history, zero future data."""
        cgm_hist = np.array([150.0, 155.0, 160.0, 165.0])
        prev_ode = np.array([140.0, 140.0, 140.0, 140.0])
        iob_hist = np.array([0.5, 0.5, 0.5, 0.5])
        ins_hist = np.array([0.1, 0.1, 0.1, 0.1])

        si, gb, diag = self.adapter.update_window(
            pid="P001",
            cgm_recent_4=cgm_hist,
            prev_ode_pred_4=prev_ode,
            iob_recent_4=iob_hist,
            ins_recent_4=ins_hist
        )
        self.assertTrue(diag["adapted"])
        self.assertAlmostEqual(diag["res_innov"], float(np.mean(cgm_hist - prev_ode)), places=4)

    def test_bounds_enforcement_si_and_gb(self):
        """Verify parameters NEVER breach [1e-5, 5e-3] and [70, 220] even under extreme residuals."""
        # Extreme positive residual (+500 mg/dL)
        cgm_extreme = np.array([600.0, 600.0, 600.0, 600.0])
        prev_ode = np.array([100.0, 100.0, 100.0, 100.0])
        iob = np.array([5.0, 5.0, 5.0, 5.0])
        ins = np.array([2.0, 2.0, 2.0, 2.0])

        cfg = PatientOdeConfig(adapt_si=True, adapt_gb=True, eta_si=0.5, eta_gb=0.5, beta=0.0)
        adapter = PatientOdeAdapter(cfg)

        for _ in range(50):
            si, gb, _ = adapter.update_window("P_EXTREME", cgm_extreme, prev_ode, iob, ins)
            self.assertGreaterEqual(si, 1.0e-5)
            self.assertLessEqual(si, 5.0e-3)
            self.assertGreaterEqual(gb, 70.0)
            self.assertLessEqual(gb, 220.0)

        # Extreme negative residual (-500 mg/dL)
        cgm_low = np.array([20.0, 20.0, 20.0, 20.0])
        prev_ode_high = np.array([500.0, 500.0, 500.0, 500.0])
        for _ in range(50):
            si, gb, _ = adapter.update_window("P_EXTREME_LOW", cgm_low, prev_ode_high, iob, ins)
            self.assertGreaterEqual(si, 1.0e-5)
            self.assertLessEqual(si, 5.0e-3)
            self.assertGreaterEqual(gb, 70.0)
            self.assertLessEqual(gb, 220.0)

    def test_nan_inf_immunity(self):
        """Verify that corrupted input (NaN / Inf) triggers graceful reset to baseline."""
        cgm_nan = np.array([np.nan, 150.0, 160.0, 170.0])
        prev_ode = np.array([140.0, 140.0, 140.0, 140.0])
        iob = np.array([0.5, 0.5, 0.5, 0.5])
        ins = np.array([0.1, 0.1, 0.1, 0.1])

        si, gb, diag = self.adapter.update_window("P_NAN", cgm_nan, prev_ode, iob, ins)
        self.assertFalse(np.isnan(si))
        self.assertFalse(np.isnan(gb))
        self.assertEqual(si, self.config.base_si)
        self.assertEqual(gb, self.config.base_gb)

        # Inf test
        cgm_inf = np.array([np.inf, 150.0, 160.0, 170.0])
        si, gb, diag = self.adapter.update_window("P_INF", cgm_inf, prev_ode, iob, ins)
        self.assertFalse(np.isinf(si))
        self.assertFalse(np.isinf(gb))
        self.assertEqual(si, self.config.base_si)

    def test_adaptation_disabled_reproduces_baseline(self):
        """Verify that adapt_si=False, adapt_gb=False returns exact baseline parameters."""
        cfg = PatientOdeConfig(adapt_si=False, adapt_gb=False)
        adapter = PatientOdeAdapter(cfg)

        cgm = np.array([200.0, 200.0, 200.0, 200.0])
        prev_ode = np.array([100.0, 100.0, 100.0, 100.0])
        iob = np.array([1.0, 1.0, 1.0, 1.0])
        ins = np.array([0.5, 0.5, 0.5, 0.5])

        for _ in range(10):
            si, gb, diag = adapter.update_window("P_DISABLED", cgm, prev_ode, iob, ins)
            self.assertEqual(si, cfg.base_si)
            self.assertEqual(gb, cfg.base_gb)
            self.assertFalse(diag["adapted"])

    def test_zero_adaptation_rate_reproduces_baseline(self):
        """Verify that eta_si=0.0, eta_gb=0.0 returns exact baseline parameters."""
        cfg = PatientOdeConfig(adapt_si=True, adapt_gb=True, eta_si=0.0, eta_gb=0.0)
        adapter = PatientOdeAdapter(cfg)

        cgm = np.array([250.0, 250.0, 250.0, 250.0])
        prev_ode = np.array([100.0, 100.0, 100.0, 100.0])
        iob = np.array([1.0, 1.0, 1.0, 1.0])
        ins = np.array([0.5, 0.5, 0.5, 0.5])

        for _ in range(10):
            si, gb, _ = adapter.update_window("P_ZERO_ETA", cgm, prev_ode, iob, ins)
            self.assertAlmostEqual(si, cfg.base_si, places=6)
            self.assertAlmostEqual(gb, cfg.base_gb, places=2)

    def test_deterministic_inference(self):
        """Verify identical inputs produce identical parameter sequences."""
        pids = np.array(["P1", "P1", "P1", "P2", "P2"])
        dyn = np.random.RandomState(42).randn(5, 96, 22).astype(np.float32)
        dyn[:, :, 0] = 150.0 + dyn[:, :, 0] * 20.0
        ode_proxy = np.full((5, 20), 140.0, dtype=np.float32)

        adapter1 = PatientOdeAdapter(self.config)
        si1, gb1, _ = adapter1.process_stream(pids, dyn, ode_proxy)

        adapter2 = PatientOdeAdapter(self.config)
        si2, gb2, _ = adapter2.process_stream(pids, dyn, ode_proxy)

        np.testing.assert_allclose(si1, si2, rtol=1e-6)
        np.testing.assert_allclose(gb1, gb2, rtol=1e-6)

    def test_participant_reset_isolation(self):
        """Verify state is reset between different participants."""
        adapter = PatientOdeAdapter(self.config)
        cgm = np.array([250.0, 250.0, 250.0, 250.0])
        prev_ode = np.array([100.0, 100.0, 100.0, 100.0])
        iob = np.array([1.0, 1.0, 1.0, 1.0])
        ins = np.array([0.5, 0.5, 0.5, 0.5])

        # Adapt P1
        for _ in range(5):
            si_p1, _, _ = adapter.update_window("P1", cgm, prev_ode, iob, ins)
        self.assertNotEqual(si_p1, self.config.base_si)

        # First window of P2 must start at base_si
        si_p2, _, _ = adapter.update_window("P2", cgm, None, iob, ins)
        self.assertEqual(si_p2, self.config.base_si)

if __name__ == "__main__":
    unittest.main()
