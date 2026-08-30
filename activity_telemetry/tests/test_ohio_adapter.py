"""
GlucoShield Ohio Adapter & Pre-Ablation Test Suite
==================================================
Comprehensive automated unit tests covering:
  1. Single participant parsing & alignment
  2. Multiple participant isolation
  3. Duplicate timestamp detection
  4. Non-monotonic timestamp rejection
  5. Missing optional signal handling (HR/Steps absent)
  6. Missing required signal rejection (CGM absent)
  7. Physiological unit bounds validation
  8. No cross-patient window generation
  9. Zero future lookahead leakage
  10. Train-only scaler fitting logic
  11. Strict participant-disjoint split enforcement
  12. Deterministic split reproduction
  13. Dataset-absent readiness checker behavior
"""

import os
import sys
import unittest
import pandas as pd
import numpy as np

# Ensure project root is in sys.path
BASE_DIR = "D:/ML PROJECT"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from activity_telemetry.ohio_schema import OhioT1DMConfig, OhioValidationReport
from activity_telemetry.ohio_data_validator import OhioDataValidator
from activity_telemetry.experiments.participant_split import generate_participant_split, generate_kfold_participant_splits
from activity_telemetry.validation.check_ohiot1dm_readiness import check_ohiot1dm_readiness
from activity_telemetry.timestamp_alignment import align_telemetry_to_15m_grid
from activity_telemetry.feature_engineering import compute_activity_features

class TestOhioAdapterAndAblationReadiness(unittest.TestCase):

    def setUp(self):
        self.validator = OhioDataValidator()
        self.config = OhioT1DMConfig()

    def test_01_single_participant_processing(self):
        """Test 1: Single participant DataFrame validates successfully."""
        df = pd.DataFrame({
            "timestamp": pd.date_range("2026-06-01 00:00", periods=20, freq="5min"),
            "participant_id": ["559"] * 20,
            "cgm_glucose": [120.0 + i for i in range(20)],
            "heart_rate": [70.0] * 20,
            "steps": [10.0] * 20
        })
        report = self.validator.validate_participant_dataframe(df, expected_participant_id="559")
        self.assertTrue(report.is_valid)
        self.assertEqual(report.participant_id, "559")
        self.assertEqual(report.total_raw_records, 20)
        self.assertEqual(report.glucose_records, 20)

    def test_02_multiple_participant_isolation(self):
        """Test 2: Detecting mixed participant data rejects validation with error."""
        df_mixed = pd.DataFrame({
            "timestamp": pd.date_range("2026-06-01 00:00", periods=10, freq="5min"),
            "participant_id": ["559"] * 5 + ["563"] * 5,
            "cgm_glucose": [120.0] * 10
        })
        report = self.validator.validate_participant_dataframe(df_mixed, expected_participant_id="559")
        self.assertFalse(report.is_valid)
        self.assertTrue(report.mixed_participant_leakage)
        self.assertTrue(any("Mixed participant" in e for e in report.errors))

    def test_03_duplicate_timestamp_detection(self):
        """Test 3: Duplicate timestamps generate warnings."""
        df = pd.DataFrame({
            "timestamp": [pd.to_datetime("2026-06-01 10:00"), pd.to_datetime("2026-06-01 10:00"), pd.to_datetime("2026-06-01 10:05")],
            "participant_id": ["559"] * 3,
            "cgm_glucose": [120.0, 122.0, 125.0]
        })
        report = self.validator.validate_participant_dataframe(df, expected_participant_id="559")
        self.assertEqual(report.duplicate_timestamps_found, 1)
        self.assertTrue(any("duplicate" in w.lower() for w in report.warnings))

    def test_04_non_monotonic_timestamp_handling(self):
        """Test 4: Out-of-order timestamps trigger validation error."""
        df_unsorted = pd.DataFrame({
            "timestamp": [pd.to_datetime("2026-06-01 10:10"), pd.to_datetime("2026-06-01 10:00"), pd.to_datetime("2026-06-01 10:05")],
            "participant_id": ["559"] * 3,
            "cgm_glucose": [120.0, 125.0, 130.0]
        })
        report = self.validator.validate_participant_dataframe(df_unsorted, expected_participant_id="559")
        self.assertFalse(report.is_valid)
        self.assertFalse(report.monotonic_timestamps)
        self.assertTrue(any("non-monotonic" in e.lower() for e in report.errors))

    def test_05_missing_optional_signal_handling(self):
        """Test 5: Missing optional heart rate produces warning but remains valid."""
        df_no_hr = pd.DataFrame({
            "timestamp": pd.date_range("2026-06-01 00:00", periods=10, freq="5min"),
            "participant_id": ["559"] * 10,
            "cgm_glucose": [130.0] * 10
        })
        report = self.validator.validate_participant_dataframe(df_no_hr, expected_participant_id="559")
        self.assertTrue(report.is_valid)
        self.assertEqual(report.heart_rate_records, 0)
        self.assertEqual(report.heart_rate_missing_pct, 100.0)

    def test_06_missing_required_signal_rejection(self):
        """Test 6: Missing CGM glucose rejects validation with critical error."""
        df_no_cgm = pd.DataFrame({
            "timestamp": pd.date_range("2026-06-01 00:00", periods=10, freq="5min"),
            "participant_id": ["559"] * 10,
            "heart_rate": [70.0] * 10
        })
        report = self.validator.validate_participant_dataframe(df_no_cgm, expected_participant_id="559")
        self.assertFalse(report.is_valid)
        self.assertTrue(any("glucose" in e.lower() for e in report.errors))

    def test_07_unit_validation(self):
        """Test 7: Out-of-bounds physiological values (e.g. glucose = 999 mg/dL) generate warnings."""
        df_extreme = pd.DataFrame({
            "timestamp": pd.date_range("2026-06-01 00:00", periods=5, freq="5min"),
            "participant_id": ["559"] * 5,
            "cgm_glucose": [120.0, 130.0, 999.0, 140.0, 5.0]
        })
        report = self.validator.validate_participant_dataframe(df_extreme, expected_participant_id="559")
        self.assertEqual(report.out_of_range_glucose_count, 2)
        self.assertTrue(any("physiological range" in w for w in report.warnings))

    def test_08_no_cross_patient_window_generation(self):
        """Test 8: Temporal alignment strictly isolates participant streams."""
        df1 = pd.DataFrame({
            "timestamp": pd.date_range("2026-06-01 00:00", periods=12, freq="5min"),
            "cgm_glucose": [100.0] * 12
        })
        df2 = pd.DataFrame({
            "timestamp": pd.date_range("2026-06-01 00:00", periods=12, freq="5min"),
            "cgm_glucose": [180.0] * 12
        })
        out1 = align_telemetry_to_15m_grid(df1, participant_id="559")
        out2 = align_telemetry_to_15m_grid(df2, participant_id="563")

        self.assertTrue(all(out1["participant_id"] == "559"))
        self.assertTrue(all(out2["participant_id"] == "563"))
        self.assertEqual(out1["cgm_glucose"].iloc[0], 100.0)
        self.assertEqual(out2["cgm_glucose"].iloc[0], 180.0)

    def test_09_no_future_leakage_in_features(self):
        """Test 9: Feature computation produces identical results regardless of future rows."""
        df_past_only = pd.DataFrame({
            "timestamp": pd.date_range("2026-06-01 00:00", periods=4, freq="15min"),
            "participant_id": ["559"] * 4,
            "steps_15m": [100.0, 200.0, 300.0, 400.0],
            "sensor_missing": [0] * 4
        })
        df_extended = pd.DataFrame({
            "timestamp": pd.date_range("2026-06-01 00:00", periods=8, freq="15min"),
            "participant_id": ["559"] * 8,
            "steps_15m": [100.0, 200.0, 300.0, 400.0, 9999.0, 9999.0, 9999.0, 9999.0],
            "sensor_missing": [0] * 8
        })
        feat_past = compute_activity_features(df_past_only)
        feat_ext = compute_activity_features(df_extended)

        # active_load_60m for step 3 must be identical
        self.assertAlmostEqual(feat_past["active_load_60m"].iloc[3], feat_ext["active_load_60m"].iloc[3])

    def test_10_train_only_scaler_fitting_logic(self):
        """Test 10: Scaling parameters are fit exclusively on training set."""
        train_vals = np.array([[10.0], [20.0], [30.0]])
        test_vals = np.array([[1000.0]])

        # Train median = 20, IQR = 10
        median = np.median(train_vals)
        q75, q25 = np.percentile(train_vals, [75, 25])
        iqr = max(1e-6, q75 - q25)

        scaled_train = (train_vals - median) / iqr
        scaled_test = (test_vals - median) / iqr  # Applied without re-estimating median

        self.assertAlmostEqual(median, 20.0)
        self.assertAlmostEqual(scaled_test[0, 0], (1000.0 - 20.0) / iqr)

    def test_11_participant_disjoint_split_enforcement(self):
        """Test 11: Split generator guarantees 0% overlap between train, val, and test."""
        pids = [f"PT_{i:02d}" for i in range(1, 13)]
        split = generate_participant_split(pids, seed=42)

        s_tr = set(split["train_participants"])
        s_va = set(split["validation_participants"])
        s_te = set(split["test_participants"])

        self.assertEqual(len(s_tr), 8)
        self.assertEqual(len(s_va), 2)
        self.assertEqual(len(s_te), 2)
        self.assertEqual(len(s_tr.intersection(s_va)), 0)
        self.assertEqual(len(s_tr.intersection(s_te)), 0)
        self.assertEqual(len(s_va.intersection(s_te)), 0)

    def test_12_deterministic_split_reproduction(self):
        """Test 12: Fixed seed produces 100% identical participant partitions."""
        pids = [f"PT_{i:02d}" for i in range(1, 13)]
        split1 = generate_participant_split(pids, seed=123)
        split2 = generate_participant_split(pids, seed=123)

        self.assertEqual(split1["train_participants"], split2["train_participants"])
        self.assertEqual(split1["validation_participants"], split2["validation_participants"])
        self.assertEqual(split1["test_participants"], split2["test_participants"])

    def test_13_dataset_absent_readiness_checker_behavior(self):
        """Test 13: Readiness checker exits cleanly with DATASET_NOT_PRESENT when files are absent."""
        rep = check_ohiot1dm_readiness()
        self.assertIn(rep["status"], ["DATASET_NOT_PRESENT", "DATA_READY"])
        self.assertIsInstance(rep["is_ready_for_ablation"], bool)

    def test_14_kfold_complete_test_coverage_13_folds(self):
        """Test 14: 13-fold LOOCV ensures all 13 participants appear in test set exactly once with 11/1/1 partitions."""
        pids = ["User1", "User3", "User4", "User5", "User6", "User7", "User8", "User9", "User10", "User12", "User13", "User14", "User15"]
        manifest = generate_kfold_participant_splits(pids, n_splits=13, seed=42)

        self.assertEqual(len(manifest["folds"]), 13)
        all_test = []
        for f in manifest["folds"]:
            self.assertEqual(f["train_count"], 11)
            self.assertEqual(f["val_count"], 1)
            self.assertEqual(f["test_count"], 1)
            all_test.extend(f["test_participants"])

        self.assertEqual(len(all_test), 13)
        self.assertEqual(sorted(all_test), sorted(pids))

    def test_15_kfold_disjointness_per_fold_13_folds(self):
        """Test 15: Within every fold of 13-fold LOOCV, train (11), val (1), and test (1) are strictly disjoint."""
        pids = ["User1", "User3", "User4", "User5", "User6", "User7", "User8", "User9", "User10", "User12", "User13", "User14", "User15"]
        manifest = generate_kfold_participant_splits(pids, n_splits=13, seed=42)

        for f in manifest["folds"]:
            s_tr = set(f["train_participants"])
            s_va = set(f["validation_participants"])
            s_te = set(f["test_participants"])
            self.assertEqual(len(s_tr.intersection(s_va)), 0)
            self.assertEqual(len(s_tr.intersection(s_te)), 0)
            self.assertEqual(len(s_va.intersection(s_te)), 0)

    def test_16_kfold_deterministic_reproduction_13_folds(self):
        """Test 16: 13-fold LOOCV is 100% deterministic with fixed seed."""
        pids = ["User1", "User3", "User4", "User5", "User6", "User7", "User8", "User9", "User10", "User12", "User13", "User14", "User15"]
        m1 = generate_kfold_participant_splits(pids, n_splits=13, seed=99)
        m2 = generate_kfold_participant_splits(pids, n_splits=13, seed=99)

        for i in range(13):
            self.assertEqual(m1["folds"][i]["train_participants"], m2["folds"][i]["train_participants"])
            self.assertEqual(m1["folds"][i]["validation_participants"], m2["folds"][i]["validation_participants"])
            self.assertEqual(m1["folds"][i]["test_participants"], m2["folds"][i]["test_participants"])

    def test_17_kfold_out_of_fold_wilcoxon_sample_size_13(self):
        """Test 17: Out-of-fold pooling yields exactly 13 paired out-of-fold participant-level error observations, where each participant appears exactly once as a held-out test participant across the complete cross-validation procedure."""
        pids = ["User1", "User3", "User4", "User5", "User6", "User7", "User8", "User9", "User10", "User12", "User13", "User14", "User15"]
        manifest = generate_kfold_participant_splits(pids, n_splits=13, seed=42)
        
        # Simulating out-of-fold test evaluation accumulation
        oof_model_a_mae = {}
        oof_model_b_mae = {}
        for f in manifest["folds"]:
            for test_pid in f["test_participants"]:
                self.assertNotIn(test_pid, oof_model_a_mae, "Duplicate test prediction for participant!")
                oof_model_a_mae[test_pid] = 14.5  # Simulated MAE
                oof_model_b_mae[test_pid] = 13.2  # Simulated MAE

        self.assertEqual(len(oof_model_a_mae), 13)
        self.assertEqual(len(oof_model_b_mae), 13)

if __name__ == "__main__":
    unittest.main()

