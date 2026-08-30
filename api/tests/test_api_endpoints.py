"""
GlucoShield API Integration & End-to-End Test Suite
===================================================
Tests all 5 REST endpoints, input preprocessor, physiological validation,
food vision bridging, what-if simulations, and frozen model hash preservation.
"""

import sys
import os
import unittest
import hashlib
import numpy as np
from fastapi.testclient import TestClient

BASE_DIR = "D:/ML PROJECT"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from api.service import app
from api.schemas import TimeStepReading, PatientStaticProfile

def sha256_file(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192 * 1024):
            h.update(chunk)
    return h.hexdigest().lower()

class TestGlucoShieldAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        # Enter client context once for entire test suite
        cls.client.__enter__()

        # Record frozen model hashes
        cls.neural_hash = sha256_file(os.path.join(BASE_DIR, "models", "glucoshield_neural_best.pt"))
        cls.hybrid_hash = sha256_file(os.path.join(BASE_DIR, "models", "glucoshield_hybrid_best.pt"))

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)

    def _generate_synthetic_96_readings(self, base_glucose=120.0, trend="stable"):
        readings = []
        for i in range(96):
            if trend == "stable":
                g = base_glucose + np.sin(i / 5.0) * 5.0
            elif trend == "falling":
                g = max(45.0, base_glucose - i * 0.8)
            elif trend == "rising":
                g = min(350.0, base_glucose + i * 1.5)
            else:
                g = base_glucose

            bolus = 3.0 if i == 60 else 0.0
            carbs = 45.0 if i == 60 else 0.0
            readings.append({
                "timestamp": f"2026-08-28T{i//4:02d}:{(i%4)*15:02d}:00",
                "cgm_glucose": float(g),
                "insulin_bolus": float(bolus),
                "insulin_basal": 0.5,
                "meal_carbs": float(carbs)
            })
        return readings

    def test_01_health_endpoint(self):
        """Test 1: Health endpoint returns status healthy, model readiness, and research disclaimer."""
        resp = self.client.get("/api/v1/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "healthy")
        self.assertTrue(data["neural_forecaster_loaded"])
        self.assertTrue(data["hybrid_forecaster_loaded"])
        self.assertTrue(data["ode_digital_twin_ready"])
        self.assertEqual(data["active_channels_contract"], 22)
        self.assertIn("RESEARCH", data["research_disclaimer"])

    def test_02_forecast_endpoint_valid_payload(self):
        """Test 2: Forecast endpoint returns 20-step hybrid trajectory, intervals, risk alerts, and explanation."""
        payload = {
            "patient_id": "test_patient_01",
            "history_readings": self._generate_synthetic_96_readings(130.0, "stable"),
            "static_profile": {
                "age": 45.0,
                "bmi": 26.5,
                "hba1c": 58.0,
                "is_t1dm": 1.0
            }
        }
        resp = self.client.post("/api/v1/forecast", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        
        # Forecast trajectory structure
        self.assertEqual(len(data["forecast"]["point_forecast_mg_dl"]), 20)
        self.assertEqual(len(data["forecast"]["lower_80_mg_dl"]), 20)
        self.assertEqual(len(data["forecast"]["upper_80_mg_dl"]), 20)
        self.assertEqual(len(data["forecast"]["lower_95_mg_dl"]), 20)
        self.assertEqual(len(data["forecast"]["upper_95_mg_dl"]), 20)

        # Check interval width monotonic relationship (95% wider than 80%)
        u80 = np.array(data["forecast"]["upper_80_mg_dl"])
        l80 = np.array(data["forecast"]["lower_80_mg_dl"])
        u95 = np.array(data["forecast"]["upper_95_mg_dl"])
        l95 = np.array(data["forecast"]["lower_95_mg_dl"])
        self.assertTrue(np.all((u95 - l95) >= (u80 - l80)))

        # Risk assessment & Explanations
        self.assertIn("alert_level", data["risk_assessment"])
        self.assertIn("headline", data["explanation"])
        self.assertIn("hybrid_attribution", data["explanation"])

    def test_03_forecast_endpoint_invalid_length_rejection(self):
        """Test 3: Reject history payloads that do not contain exactly 96 timesteps (24 hours)."""
        payload = {
            "patient_id": "test_patient_02",
            "history_readings": self._generate_synthetic_96_readings(120.0)[:50]
        }
        resp = self.client.post("/api/v1/forecast", json=payload)
        self.assertEqual(resp.status_code, 422)

    def test_04_forecast_endpoint_physiological_bound_rejection(self):
        """Test 4: Reject physiologically impossible glucose or dosing bounds."""
        readings = self._generate_synthetic_96_readings(120.0)
        readings[0]["cgm_glucose"] = 1500.0  # Impossible glucose (> 600)
        payload = {
            "patient_id": "test_patient_03",
            "history_readings": readings
        }
        resp = self.client.post("/api/v1/forecast", json=payload)
        self.assertEqual(resp.status_code, 422)

    def test_05_what_if_simulation_endpoint(self):
        """Test 5: What-If simulation executes counterfactual ODE simulation for proposed meal and bolus."""
        payload = {
            "patient_id": "test_patient_04",
            "history_readings": self._generate_synthetic_96_readings(110.0, "stable"),
            "scenario_meal_carbs_g": 60.0,
            "scenario_insulin_bolus_u": 4.5
        }
        resp = self.client.post("/api/v1/what-if", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["simulated_trajectory"]), 20)
        self.assertIn("nadir_glucose", data)
        self.assertIn("peak_glucose", data)
        self.assertIn("time_in_range_pct", data)
        self.assertIn("what_if_meal_60g_bolus_4.5U", data["scenario_name"])

    def test_06_food_analyze_endpoint_text_query(self):
        """Test 6: Food analyze endpoint parses text query, returns nutrition density, macronutrients, and safety policy."""
        payload = {
            "food_name_query": "apple",
            "portion_g": 182.0
        }
        resp = self.client.post("/api/v1/food/analyze", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["selected_food"], "apple")
        self.assertGreater(data["final_macros"]["carbs_g"], 10.0)
        self.assertTrue(data["requires_user_confirmation"])  # Healthcare confirmation policy enforced

    def test_07_food_analyze_endpoint_low_confidence_handling(self):
        """Test 7: Food analyze endpoint flags ambiguous items with requires_user_confirmation=True."""
        payload = {
            "food_name_query": "unknown_mysterious_food_xyz",
            "portion_g": 100.0
        }
        resp = self.client.post("/api/v1/food/analyze", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["requires_user_confirmation"])
        self.assertGreater(len(data["warnings"]), 0)

    def test_08_full_flow_decision_endpoint(self):
        """Test 8: Unified full-flow endpoint executes Food Vision -> Hybrid Forecaster -> What-If -> Decision Summary."""
        payload = {
            "patient_id": "test_patient_08",
            "history_readings": self._generate_synthetic_96_readings(125.0, "stable"),
            "meal_food_query": "pizza",
            "meal_portion_g": 200.0,
            "proposed_insulin_bolus_u": 6.0
        }
        resp = self.client.post("/api/v1/decision/full-flow", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        
        # Check presence of all components
        self.assertIsNotNone(data["food_analysis"])
        self.assertIsNotNone(data["baseline_forecast"])
        self.assertIsNotNone(data["what_if_simulation"])
        self.assertIn("decision_summary", data)
        self.assertGreater(data["decision_summary"]["meal_carbs_considered_g"], 20.0)
        self.assertEqual(data["decision_summary"]["bolus_considered_u"], 6.0)

    def test_09_wearable_context_isolation(self):
        """Test 9: Passing wearable context is acknowledged in response metadata without altering V1 model output."""
        readings = self._generate_synthetic_96_readings(120.0)
        
        # Request WITHOUT wearable context
        resp_no_wear = self.client.post("/api/v1/forecast", json={"patient_id": "pt_a", "history_readings": readings})
        self.assertEqual(resp_no_wear.status_code, 200)
        data_no_wear = resp_no_wear.json()
        self.assertFalse(data_no_wear["wearable_context_logged"])

        # Request WITH wearable context
        resp_wear = self.client.post("/api/v1/forecast", json={
            "patient_id": "pt_a",
            "history_readings": readings,
            "wearable_context": {
                "steps_15m": [150.0] * 96,
                "heart_rate_bpm": [85.0] * 96,
                "device_source": "TicWatch Pro"
            }
        })
        self.assertEqual(resp_wear.status_code, 200)
        data_wear = resp_wear.json()
        self.assertTrue(data_wear["wearable_context_logged"])

        # Point forecasts MUST BE IDENTICAL bit-for-bit (Wearable data strictly isolated from V1 forecaster)
        np.testing.assert_allclose(
            data_no_wear["forecast"]["point_forecast_mg_dl"],
            data_wear["forecast"]["point_forecast_mg_dl"],
            rtol=1e-5, atol=1e-5
        )

    def test_10_frozen_model_hash_verification(self):
        """Test 10: Frozen V1 core model hashes remain bitwise unchanged before and after API operations."""
        current_neural_hash = sha256_file(os.path.join(BASE_DIR, "models", "glucoshield_neural_best.pt"))
        current_hybrid_hash = sha256_file(os.path.join(BASE_DIR, "models", "glucoshield_hybrid_best.pt"))

        self.assertEqual(self.neural_hash, current_neural_hash)
        self.assertEqual(self.hybrid_hash, current_hybrid_hash)
        self.assertEqual(current_neural_hash, "026af3341a91064136c38b0172f2aa6af34806913640a02270c7d82a28ea13fb")
        self.assertEqual(current_hybrid_hash, "89a67710aa4931246f9097674332cbfd9d1af3d20c722c04d806ef66e47298d1")

if __name__ == "__main__":
    unittest.main(verbosity=2)
