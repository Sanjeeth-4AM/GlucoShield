"""
GlucoShield Unit & Integration Tests — Cohort & Comparative Intelligence
========================================================================
Validates real cohort endpoints, Patient A vs Patient B data structures,
Combination C forecast integrity, and comparative intelligence metrics.
"""

import unittest
from fastapi.testclient import TestClient
from api.service import app

class TestCohortComparison(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)

    def test_get_demo_patients(self):
        res = self.client.get("/api/v1/cohort/demo-patients")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("patientA", data)
        self.assertIn("patientB", data)

        patA = data["patientA"]
        patB = data["patientB"]

        # Validate Patient A structure and real metrics
        self.assertEqual(patA["id"], "PATIENT_A")
        self.assertEqual(len(patA["history_readings"]), 96)
        self.assertEqual(patA["observation_count"], 96)
        self.assertEqual(patA["sampling_interval_min"], 15)
        self.assertEqual(patA["diabetes_type"], "Type 2 Diabetes (T2D)")
        self.assertEqual(patA["data_status"], "HISTORICAL_DATASET")
        self.assertEqual(patA["cgm_stats"]["time_in_range_pct"], 100.0)
        self.assertAlmostEqual(patA["cgm_stats"]["average_glucose"], 103.6, delta=1.0)
        self.assertIn("point_forecast_mg_dl", patA["forecast"])
        self.assertEqual(len(patA["forecast"]["point_forecast_mg_dl"]), 20)

        # Validate Patient B structure and real metrics
        self.assertEqual(patB["id"], "PATIENT_B")
        self.assertEqual(len(patB["history_readings"]), 96)
        self.assertEqual(patB["observation_count"], 96)
        self.assertEqual(patB["sampling_interval_min"], 15)
        self.assertEqual(patB["diabetes_type"], "Type 2 Diabetes (T2D)")
        self.assertEqual(patB["data_status"], "HISTORICAL_DATASET")
        self.assertEqual(patB["clinical_type"], "Type 2 Diabetes (Hyperglycemic 24-Hour Profile)")
        self.assertEqual(patB["cgm_stats"]["time_above_range_pct"], 100.0)
        self.assertAlmostEqual(patB["cgm_stats"]["average_glucose"], 261.7, delta=1.0)
        self.assertIn("point_forecast_mg_dl", patB["forecast"])
        self.assertEqual(len(patB["forecast"]["point_forecast_mg_dl"]), 20)

    def test_get_individual_cohort_patient(self):
        resA = self.client.get("/api/v1/cohort/patients/PATIENT_A")
        self.assertEqual(resA.status_code, 200)
        self.assertEqual(resA.json()["id"], "PATIENT_A")

        resB = self.client.get("/api/v1/cohort/patients/PATIENT_B")
        self.assertEqual(resB.status_code, 200)
        self.assertEqual(resB.json()["id"], "PATIENT_B")

        res_invalid = self.client.get("/api/v1/cohort/patients/PATIENT_UNKNOWN")
        self.assertEqual(res_invalid.status_code, 404)

    def test_get_cohort_comparison(self):
        res = self.client.get("/api/v1/cohort/comparison")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertIn("comparison_table", data)
        self.assertIn("risk_visualization", data)
        self.assertIn("comparative_interpretation", data)

        table = data["comparison_table"]
        # Find 5-hour risk row and ensure it is NOT evaluated
        five_h_row = next((r for r in table if "risk at 5h" in r["parameter"].lower()), None)
        self.assertIsNotNone(five_h_row)
        self.assertEqual(five_h_row["patient_a"], "N/A (Not Evaluated)")
        self.assertEqual(five_h_row["patient_b"], "N/A (Not Evaluated)")

        # Verify Hyperglycemia at 2h & 4h is much higher in Patient B
        hyper_2h_row = next((r for r in table if "Hyperglycemia risk at 2h" in r["parameter"]), None)
        self.assertIsNotNone(hyper_2h_row)
        self.assertGreater(float(hyper_2h_row["patient_b"]), 90.0)
        self.assertLess(float(hyper_2h_row["patient_a"]), 10.0)

        # Verify visualizations
        vis = data["risk_visualization"]
        self.assertIn("hypoglycemia", vis)
        self.assertIn("hyperglycemia", vis)
        self.assertEqual(len(vis["hypoglycemia"]), 3) # 1h, 2h, 4h
        self.assertEqual(len(vis["hyperglycemia"]), 2) # 2h, 4h

        # Verify metadata and scientific interpretation phrasing
        self.assertEqual(data["patientA"]["data_status"], "HISTORICAL_DATASET")
        self.assertEqual(data["patientA"]["sampling_interval_min"], 15)
        self.assertIn("marked 24-hour glycemic instability", data["comparative_interpretation"]["stability_analysis"])
        self.assertNotIn("chronic", data["comparative_interpretation"]["stability_analysis"].lower())

if __name__ == "__main__":
    unittest.main()
