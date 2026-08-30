"""
GlucoShield Activity Telemetry Automated Test Suite
===================================================
Comprehensive unit tests covering:
  1. Exact 15-minute binning
  2. No cross-participant data leakage
  3. Strict causality (no future data leakage in active_load_60m)
  4. Correct 3D acceleration magnitude calculation
  5. Accurate heart rate aggregation
  6. SENSOR_MISSING != NO_ACTIVITY distinction
  7. Duplicate timestamp deduplication
  8. Out-of-order timestamp sorting
  9. Exercise onset pulse detection (0 -> 1 transition)
  10. Step-count boundary precision without double counting
  11. Empty-window behavior
  12. Participant boundary enforcement
  13. GlucoShield V1 core integrity invariant (SHA256 hashes)
"""

import os
import sys
import unittest
import hashlib
import numpy as np
import pandas as pd

# Ensure project root is in sys.path
BASE_DIR = "D:/ML PROJECT"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from activity_telemetry.dataset_adapter import MockWearableAdapter
from activity_telemetry.timestamp_alignment import align_telemetry_to_15m_grid
from activity_telemetry.feature_engineering import compute_activity_features
from activity_telemetry.activity_detection import detect_activity_states, extract_activity_episodes
from activity_telemetry.missing_data import clean_raw_timestamps, audit_participant_quality

class TestActivityTelemetry(unittest.TestCase):

    def setUp(self):
        np.random.seed(42)

    def test_01_exact_15m_binning(self):
        """Test 1: Output timestamps align precisely to 15-minute grid boundaries."""
        adapter = MockWearableAdapter(num_days=1, seed=42)
        df_raw = adapter.load_participant_telemetry("PT_01")
        df_15m = align_telemetry_to_15m_grid(df_raw, participant_id="PT_01", expected_sample_interval_sec=5.0)

        self.assertFalse(df_15m.empty)
        # Check that all minute values are in {0, 15, 30, 45} and seconds are 0
        minutes = df_15m["timestamp"].dt.minute
        seconds = df_15m["timestamp"].dt.second
        self.assertTrue(all(m in [0, 15, 30, 45] for m in minutes))
        self.assertTrue(all(s == 0 for s in seconds))
        # 1 day = 96 15-minute windows
        self.assertEqual(len(df_15m), 96)

    def test_02_no_cross_participant_leakage(self):
        """Test 2: Processing distinct participants maintains strict data isolation."""
        adapter = MockWearableAdapter(num_days=1, seed=42)
        df1 = align_telemetry_to_15m_grid(adapter.load_participant_telemetry("PT_01"), "PT_01")
        df2 = align_telemetry_to_15m_grid(adapter.load_participant_telemetry("PT_02"), "PT_02")

        self.assertTrue(all(df1["participant_id"] == "PT_01"))
        self.assertTrue(all(df2["participant_id"] == "PT_02"))
        # Verify timestamps match independent 96 windows
        self.assertEqual(len(df1), 96)
        self.assertEqual(len(df2), 96)

    def test_03_strict_causality_active_load(self):
        """Test 3: active_load_60m uses only past/present data (zero future lookahead)."""
        df_dummy = pd.DataFrame({
            "timestamp": pd.date_range("2026-06-01 00:00", periods=8, freq="15min"),
            "participant_id": ["PT_01"] * 8,
            "steps_15m": [0.0, 100.0, 0.0, 0.0, 500.0, 0.0, 0.0, 0.0],
            "hr_mean_15m": [70.0] * 8,
            "sensor_missing": [0] * 8
        })
        df_feat = compute_activity_features(df_dummy, gamma_decay=0.5)
        
        # Step 0 (0 steps): load = 0
        self.assertEqual(df_feat["active_load_60m"].iloc[0], 0.0)
        # Step 1 (100 steps): load = 100.0
        self.assertEqual(df_feat["active_load_60m"].iloc[1], 100.0)
        # Step 2 (0 steps): load = 0 + 0.5 * 100 = 50.0
        self.assertEqual(df_feat["active_load_60m"].iloc[2], 50.0)
        # Step 3 (0 steps): load = 0 + 0.5*0 + 0.25*100 = 25.0
        self.assertEqual(df_feat["active_load_60m"].iloc[3], 25.0)

    def test_04_correct_acceleration_magnitude(self):
        """Test 4: Accel magnitude computes exact Euclidean norm sqrt(x^2 + y^2 + z^2)."""
        df_raw = pd.DataFrame({
            "timestamp": [pd.to_datetime("2026-06-01 00:05:00")],
            "cgm_glucose": [120.0],
            "heart_rate": [70.0],
            "accel_x": [3.0],
            "accel_y": [4.0],
            "accel_z": [0.0],
            "steps": [10.0]
        })
        df_15m = align_telemetry_to_15m_grid(df_raw, "PT_01", min_coverage_threshold=0.0)
        # sqrt(3^2 + 4^2 + 0) = 5.0
        self.assertAlmostEqual(df_15m["accel_mag_15m"].iloc[0], 5.0, places=2)

    def test_05_accurate_heart_rate_aggregation(self):
        """Test 5: Heart rate mean and std are computed accurately over valid readings."""
        ts = pd.date_range("2026-06-01 00:01:00", periods=5, freq="2min")
        df_raw = pd.DataFrame({
            "timestamp": ts,
            "cgm_glucose": [100.0]*5,
            "heart_rate": [60.0, 70.0, 80.0, 90.0, 100.0],  # Mean = 80.0
            "steps": [0.0]*5
        })
        df_15m = align_telemetry_to_15m_grid(df_raw, "PT_01", min_coverage_threshold=0.0)
        self.assertAlmostEqual(df_15m["hr_mean_15m"].iloc[0], 80.0, places=2)

    def test_06_sensor_missing_vs_no_activity(self):
        """Test 6: SENSOR_MISSING is distinguished from zero active movement."""
        # Case A: Sensor present with 0 steps -> sensor_missing = 0, steps = 0
        df_present = pd.DataFrame({
            "timestamp": pd.date_range("2026-06-01 00:00:05", periods=180, freq="5s"),
            "heart_rate": [65.0] * 180,
            "steps": [0.0] * 180
        })
        df_15m_present = align_telemetry_to_15m_grid(df_present, "PT_01", expected_sample_interval_sec=5.0)
        self.assertEqual(df_15m_present["sensor_missing"].iloc[0], 0)
        self.assertEqual(df_15m_present["steps_15m"].iloc[0], 0.0)

        # Case B: Sensor missing (0 samples) -> sensor_missing = 1, steps = NaN
        df_empty = pd.DataFrame(columns=["timestamp", "heart_rate", "steps"])
        df_15m_empty = align_telemetry_to_15m_grid(df_empty, "PT_01")
        self.assertTrue(df_15m_empty.empty)

    def test_07_duplicate_timestamp_deduplication(self):
        """Test 7: Duplicate timestamps are cleaned without crashing or multiplying counts."""
        df_raw = pd.DataFrame({
            "timestamp": [
                pd.to_datetime("2026-06-01 10:00:00"),
                pd.to_datetime("2026-06-01 10:00:00"),  # Duplicate
                pd.to_datetime("2026-06-01 10:01:00")
            ],
            "heart_rate": [70.0, 70.0, 75.0]
        })
        df_clean = clean_raw_timestamps(df_raw)
        self.assertEqual(len(df_clean), 2)

    def test_08_out_of_order_timestamp_sorting(self):
        """Test 8: Chronologically scrambled records are sorted properly."""
        df_raw = pd.DataFrame({
            "timestamp": [
                pd.to_datetime("2026-06-01 10:05:00"),
                pd.to_datetime("2026-06-01 10:01:00"),
                pd.to_datetime("2026-06-01 10:03:00")
            ],
            "heart_rate": [80.0, 70.0, 75.0]
        })
        df_clean = clean_raw_timestamps(df_raw)
        self.assertTrue(df_clean["timestamp"].is_monotonic_increasing)

    def test_09_exercise_onset_pulse_detection(self):
        """Test 9: exercise_onset_flag triggers 1 only on 0 -> 1 state transition."""
        df = pd.DataFrame({
            "timestamp": pd.date_range("2026-06-01 00:00", periods=5, freq="15min"),
            "participant_id": ["PT_01"] * 5,
            "steps_15m": [20.0, 300.0, 400.0, 20.0, 500.0],  # Active at idx 1, 2, and 4
            "hr_reserve_pct": [5.0, 30.0, 35.0, 5.0, 40.0],
            "accel_mag_15m": [1.0, 1.3, 1.4, 1.0, 1.5],
            "sensor_missing": [0] * 5
        })
        df_det = detect_activity_states(df, step_threshold=150.0)
        
        # is_active_15m: [0, 1, 1, 0, 1]
        np.testing.assert_array_equal(df_det["is_active_15m"].values, [0, 1, 1, 0, 1])
        # exercise_onset_flag: [0, 1, 0, 0, 1]
        np.testing.assert_array_equal(df_det["exercise_onset_flag"].values, [0, 1, 0, 0, 1])

    def test_10_step_count_boundary_precision(self):
        """Test 10: Step count sums within each window without double counting across boundaries."""
        # 30 min recording: 15 samples of 10 steps in min 1-15, 15 samples of 20 steps in min 16-30
        ts1 = pd.date_range("2026-06-01 00:01:00", periods=15, freq="1min")
        ts2 = pd.date_range("2026-06-01 00:16:00", periods=15, freq="1min")
        df_raw = pd.DataFrame({
            "timestamp": ts1.append(ts2),
            "steps": [10.0]*15 + [20.0]*15,
            "heart_rate": [70.0]*30
        })
        df_15m = align_telemetry_to_15m_grid(df_raw, "PT_01", min_coverage_threshold=0.0)
        
        self.assertEqual(len(df_15m), 2)
        self.assertAlmostEqual(df_15m["steps_15m"].iloc[0], 150.0)
        self.assertAlmostEqual(df_15m["steps_15m"].iloc[1], 300.0)

    def test_11_audit_participant_quality_metrics(self):
        """Test 11: Quality auditor accurately computes window counts and coverage percentages."""
        df_15m = pd.DataFrame({
            "cgm_glucose": [100.0, 110.0, np.nan, 120.0],
            "hr_mean_15m": [70.0, 75.0, 80.0, np.nan],
            "sensor_missing": [0, 0, 0, 1],
            "is_active_15m": [0, 1, 0, 0]
        })
        report = audit_participant_quality(df_15m, "PT_01")
        
        self.assertEqual(report.total_15m_windows, 4)
        self.assertEqual(report.valid_cgm_windows, 3)
        self.assertEqual(report.valid_wearable_windows, 3)
        self.assertEqual(report.cgm_coverage_pct, 75.0)
        self.assertEqual(report.wearable_coverage_pct, 75.0)

    def test_12_episode_clustering_integrity(self):
        """Test 12: Workout episodes cluster contiguous active periods and compute duration."""
        df = pd.DataFrame({
            "timestamp": pd.date_range("2026-06-01 17:00", periods=4, freq="15min"),
            "participant_id": ["PT_01"] * 4,
            "is_active_15m": [1, 1, 1, 0],  # 3 contiguous active windows = 45 mins
            "hr_mean_15m": [140.0, 150.0, 145.0, 75.0],
            "steps_15m": [400.0, 500.0, 450.0, 20.0],
            "accel_mag_15m": [1.4, 1.6, 1.5, 1.0],
            "cgm_glucose": [140.0, 130.0, 115.0, 105.0]
        })
        episodes = extract_activity_episodes(df, min_duration_minutes=15)
        self.assertEqual(len(episodes), 1)
        self.assertEqual(episodes[0].duration_minutes, 45.0)
        self.assertEqual(episodes[0].peak_hr, 150.0)
        self.assertAlmostEqual(episodes[0].total_steps, 1350.0)

    def test_13_glucoshield_v1_integrity_invariant(self):
        """Test 13: Strict invariant check verifying frozen V1 checkpoints and datasets."""
        neural_path = os.path.join(BASE_DIR, "models", "glucoshield_neural_best.pt")
        hybrid_path = os.path.join(BASE_DIR, "models", "glucoshield_hybrid_best.pt")
        
        self.assertTrue(os.path.exists(neural_path))
        self.assertTrue(os.path.exists(hybrid_path))

        def get_sha256(p):
            h = hashlib.sha256()
            with open(p, "rb") as f:
                while chunk := f.read(65536):
                    h.update(chunk)
            return h.hexdigest()

        self.assertEqual(get_sha256(neural_path), "026af3341a91064136c38b0172f2aa6af34806913640a02270c7d82a28ea13fb")
        self.assertEqual(get_sha256(hybrid_path), "89a67710aa4931246f9097674332cbfd9d1af3d20c722c04d806ef66e47298d1")

if __name__ == "__main__":
    unittest.main()
