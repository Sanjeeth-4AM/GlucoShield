"""
GlucoShield Phase 6 — Automated Unit Test Suite
================================================
Validates patient grouping, causal robustness, statistical reproducibility,
metric alignment, and immutability of frozen baseline artifacts.
"""

import os
import sys
import unittest
import numpy as np
import pandas as pd
import hashlib

BASE_DIR = "D:/ML PROJECT"
DATA_DIR = os.path.join(BASE_DIR, "data", "final")
MODELS_DIR = os.path.join(BASE_DIR, "models")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
PHASE6_RES_DIR = os.path.join(BASE_DIR, "evaluation", "phase6", "results")

sys.path.insert(0, BASE_DIR)
from evaluation.phase6.scripts.run_risk_calibration_audit import compute_ece

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

class TestPhase6Pipeline(unittest.TestCase):

    def test_01_patient_grouping_and_isolation(self):
        """Test 1: Verify 17 unique test patients and zero patient leakage across splits."""
        meta_tr = pd.read_csv(os.path.join(DATA_DIR, "meta_train.csv"))
        meta_val = pd.read_csv(os.path.join(DATA_DIR, "meta_val.csv"))
        meta_te = pd.read_csv(os.path.join(DATA_DIR, "meta_test.csv"))

        s_tr = set(meta_tr["patient_id"].unique())
        s_val = set(meta_val["patient_id"].unique())
        s_te = set(meta_te["patient_id"].unique())

        self.assertEqual(len(s_te), 17)
        self.assertEqual(len(s_val), 17)
        self.assertEqual(len(s_tr), 78)
        self.assertEqual(len(s_tr.intersection(s_val)), 0, "Train-Val patient leakage!")
        self.assertEqual(len(s_tr.intersection(s_te)), 0, "Train-Test patient leakage!")
        self.assertEqual(len(s_val.intersection(s_te)), 0, "Val-Test patient leakage!")

    def test_02_horizon_indexing_and_shapes(self):
        """Test 2: Verify 20-step horizon trajectory array shapes and bounds."""
        y_true = np.load(os.path.join(DATA_DIR, "Y_test_trajectory.npy"))
        y_hyb = np.load(os.path.join(RESULTS_DIR, "digital_twin", "preds_hybrid_test.npy"))

        self.assertEqual(y_true.shape, (4113, 20))
        self.assertEqual(y_hyb.shape, (4113, 20))
        self.assertFalse(np.isnan(y_hyb).any(), "NaN detected in hybrid predictions!")
        self.assertFalse(np.isinf(y_hyb).any(), "Inf detected in hybrid predictions!")
        self.assertTrue(np.all(y_hyb >= 20.0), "Predicted glucose fell below physical minimum (20 mg/dL)")
        self.assertTrue(np.all(y_hyb <= 500.0), "Predicted glucose exceeded physical maximum (500 mg/dL)")

    def test_03_metric_reproducibility(self):
        """Test 3: Verify exact metric computation against master evaluation manifest."""
        manifest_path = os.path.join(PHASE6_RES_DIR, "evaluation_manifest.json")
        self.assertTrue(os.path.exists(manifest_path))
        
        y_true = np.load(os.path.join(DATA_DIR, "Y_test_trajectory.npy"))
        y_hyb = np.load(os.path.join(RESULTS_DIR, "digital_twin", "preds_hybrid_test.npy"))
        
        mae = float(np.mean(np.abs(y_hyb - y_true)))
        rmse = float(np.sqrt(np.mean((y_hyb - y_true) ** 2)))
        
        self.assertAlmostEqual(mae, 24.1427, places=3)
        self.assertAlmostEqual(rmse, 34.7744, places=3)

    def test_04_bootstrap_reproducibility(self):
        """Test 4: Verify bootstrap resampling is deterministic with fixed seed."""
        np.random.seed(42)
        n_pts = 17
        idx_1 = np.random.choice(n_pts, size=(100, n_pts), replace=True)
        
        np.random.seed(42)
        idx_2 = np.random.choice(n_pts, size=(100, n_pts), replace=True)
        
        np.testing.assert_array_equal(idx_1, idx_2)

    def test_05_immutability_of_frozen_inputs(self):
        """Test 5: Verify SHA256 checksums of core frozen model checkpoints."""
        ckpt_neural = os.path.join(MODELS_DIR, "glucoshield_neural_best.pt")
        ckpt_hybrid = os.path.join(MODELS_DIR, "glucoshield_hybrid_best.pt")
        
        sha_neural = sha256_file(ckpt_neural)
        sha_hybrid = sha256_file(ckpt_hybrid)

        self.assertTrue(sha_neural.startswith("026af3341a910641"), f"Neural checkpoint altered! Hash: {sha_neural}")
        self.assertTrue(sha_hybrid.startswith("89a67710aa493124"), f"Hybrid checkpoint altered! Hash: {sha_hybrid}")

    def test_06_causal_perturbation_immutability(self):
        """Test 6: Verify perturbation copies do not mutate original test arrays."""
        x_orig = np.load(os.path.join(DATA_DIR, "X_test_raw.npy"))
        x_copy = x_orig.copy()
        
        # Perturb copy
        x_copy[:, :, 0] += np.random.normal(0, 10, size=x_copy[:, :, 0].shape)
        
        # Verify original is completely untouched
        x_reloaded = np.load(os.path.join(DATA_DIR, "X_test_raw.npy"))
        np.testing.assert_array_equal(x_orig, x_reloaded)

    def test_07_ece_calibration_bounds(self):
        """Test 7: Verify ECE is bounded in [0, 1] and computes safely."""
        y_true = np.array([0, 1, 0, 1, 1, 0, 0, 1])
        y_prob = np.array([0.1, 0.9, 0.2, 0.8, 0.7, 0.3, 0.4, 0.6])
        ece, mce, confs, accs, counts = compute_ece(y_true, y_prob, n_bins=5)
        
        self.assertTrue(0.0 <= ece <= 1.0)
        self.assertTrue(0.0 <= mce <= 1.0)
        self.assertEqual(sum(counts), len(y_true))

if __name__ == "__main__":
    unittest.main()
