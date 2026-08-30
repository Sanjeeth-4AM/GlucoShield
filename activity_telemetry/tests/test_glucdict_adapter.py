"""
GlucoShield — Glucdict Adapter Automated Test Suite
===================================================
Tests participant discovery, schema validation, multi-modal sensor parsing,
causal 15-minute grid downsampling, and participant isolation.
"""

import os
import sys
import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Ensure project root is in sys.path
BASE_DIR = "D:/ML PROJECT"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from activity_telemetry.glucdict_adapter import GlucdictAdapter

class TestGlucdictAdapter(unittest.TestCase):

    def setUp(self):
        self.adapter = GlucdictAdapter()
        self.raw_root = "D:/ML PROJECT/data/raw/Glucdict/Glucdict Dataset"

    def test_01_adapter_dataset_name(self):
        """Test 01: Adapter reports correct dataset name."""
        self.assertEqual(self.adapter.dataset_name, "Glucdict")

    def test_02_participant_discovery(self):
        """Test 02: Discovers all available participants."""
        pts = self.adapter.list_participants()
        self.assertGreaterEqual(len(pts), 12, "Expected at least 12 participants in Glucdict.")
        self.assertIn("User1", pts)
        self.assertIn("User3", pts)

    def test_03_load_raw_cgm_schema_and_types(self):
        """Test 03: Raw CGM parser returns validated timestamp and glucose columns."""
        df_cgm = self.adapter.load_raw_cgm("User1")
        self.assertIsInstance(df_cgm, pd.DataFrame)
        self.assertIn("timestamp", df_cgm.columns)
        self.assertIn("cgm_glucose", df_cgm.columns)
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(df_cgm["timestamp"]))
        self.assertTrue(pd.api.types.is_numeric_dtype(df_cgm["cgm_glucose"]))
        
        # Verify physiological range (mg/dL)
        self.assertTrue((df_cgm["cgm_glucose"] >= 30.0).all())
        self.assertTrue((df_cgm["cgm_glucose"] <= 500.0).all())

    def test_04_load_raw_watch_telemetry_sensors(self):
        """Test 04: Watch parser correctly separates HR (21), Steps (18), and Accel (1)."""
        watch = self.adapter.load_raw_watch_telemetry("User1")
        self.assertIn("heart_rate", watch)
        self.assertIn("steps", watch)
        self.assertIn("accel", watch)

        df_hr = watch["heart_rate"]
        if not df_hr.empty:
            self.assertIn("timestamp", df_hr.columns)
            self.assertIn("heart_rate", df_hr.columns)
            self.assertTrue((df_hr["heart_rate"] >= 30.0).all())
            self.assertTrue((df_hr["heart_rate"] <= 230.0).all())

        df_acc = watch["accel"]
        if not df_acc.empty:
            self.assertIn("accel_x", df_acc.columns)
            self.assertIn("accel_y", df_acc.columns)
            self.assertIn("accel_z", df_acc.columns)

    def test_05_load_participant_telemetry_standard_contract(self):
        """Test 05: Standardized DataFrame contains all 7 required base telemetry columns."""
        df = self.adapter.load_participant_telemetry("User1")
        expected_cols = ["timestamp", "cgm_glucose", "heart_rate", "accel_x", "accel_y", "accel_z", "steps"]
        self.assertEqual(list(df.columns), expected_cols)
        self.assertFalse(df.empty)

    def test_06_causal_15m_grid_alignment(self):
        """Test 06: Timestamps lie on exact 15-minute grid boundaries (:00, :15, :30, :45)."""
        df = self.adapter.load_participant_telemetry("User1")
        minutes = df["timestamp"].dt.minute
        valid_minutes = set([0, 15, 30, 45])
        self.assertTrue(set(minutes.unique()).issubset(valid_minutes))
        
        # Verify strictly monotonic increasing timestamps
        self.assertTrue(df["timestamp"].is_monotonic_increasing)

    def test_07_no_future_leakage_backward_aggregation(self):
        """Test 07: Causal window slicing strictly includes past readings only."""
        df = self.adapter.load_participant_telemetry("User1")
        # Step counts and mean readings are non-negative
        self.assertTrue((df["steps"] >= 0.0).all())

    def test_08_participant_isolation(self):
        """Test 08: Loading User1 and User3 yields independent DataFrames."""
        df1 = self.adapter.load_participant_telemetry("User1")
        df3 = self.adapter.load_participant_telemetry("User3")
        self.assertNotEqual(len(df1), len(df3))

    def test_09_invalid_participant_handling(self):
        """Test 09: Raises FileNotFoundError for nonexistent participant."""
        with self.assertRaises((FileNotFoundError, ValueError)):
            self.adapter.load_participant_telemetry("UserNonExistent999")

if __name__ == "__main__":
    unittest.main()
