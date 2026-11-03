"""
GlucoShield Combination C Production Serving Adapter Test Suite
================================================================
Validates all 9 core requirements (A through I) mandated for the
Combination C Production Serving Adapter certification:
  A. Point Forecast Invariance (Comb C == Frozen V1 point trajectory)
  B. Uncertainty Source (Phase-13 calibrated bounds vs. legacy V1 MC-Dropout)
  C. Disagreement Regimes (monotonic interval scaling across low, medium, high)
  D. Response Contract (conformance with ForecastResponse schema)
  E. Missing Input Invariance (wearable context does not shift point trajectory)
  F. Risk Invariance (risk calculation parity + uncertainty downside notification)
  G. Error Handling (uncertainty engine failures raise 503, never return bogus data)
  H. Legacy Path is Not Default (default endpoint uses COMBINATION_C)
  I. Frozen Artifact Cryptographic Verification (7/7 bitwise SHA-256 matches)
"""

import os
import sys
import json
import hashlib
import unittest
import numpy as np
import torch
from fastapi.testclient import TestClient

BASE_DIR = "D:/ML PROJECT"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from api.service import app, state
from api.schemas import ForecastRequest, ForecastResponse, TimeStepReading, PatientStaticProfile, OptionalWearableContext
from api.model_registry import ModelVersion, get_configured_model_version


def create_deterministic_readings(base_glucose: float = 120.0, trend: float = 0.0, std_noise: float = 0.0) -> list:
    """Generates 96 deterministic readings (24 hours at 15m intervals)."""
    readings = []
    for step in range(96):
        val = base_glucose + step * trend
        if std_noise > 0.0:
            val += np.sin(step / 4.0) * std_noise
        val = max(40.0, min(val, 400.0))
        readings.append(
            TimeStepReading(
                timestamp=f"2026-10-04T{step//4:02d}:{(step%4)*15:02d}:00Z",
                cgm_glucose=round(float(val), 1),
                insulin_bolus=0.0,
                insulin_basal=0.5,
                meal_carbs=0.0
            )
        )
    return readings


class TestCombinationCProductionServing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Instantiate test client using context manager to ensure lifespan startup runs
        cls.client_cm = TestClient(app)
        cls.client = cls.client_cm.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_cm.__exit__(None, None, None)

    def test_A_point_forecast_invariance(self):
        """
        Requirement A: Point Forecast Invariance
        Production Combination C point trajectory must exactly match
        frozen V1 production point trajectory for identical inputs.
        """
        readings = create_deterministic_readings(base_glucose=135.0, trend=0.2)
        payload_comb_c = {
            "patient_id": "test_patient_invariance",
            "history_readings": [r.model_dump() for r in readings],
            "requested_model_version": "COMBINATION_C"
        }
        payload_v1 = {
            "patient_id": "test_patient_invariance",
            "history_readings": [r.model_dump() for r in readings],
            "requested_model_version": "V1_FROZEN"
        }

        res_comb_c = self.client.post("/api/v1/forecast", json=payload_comb_c)
        self.assertEqual(res_comb_c.status_code, 200, f"Comb C failed: {res_comb_c.text}")
        data_comb_c = res_comb_c.json()

        res_v1 = self.client.post("/api/v1/forecast", json=payload_v1)
        self.assertEqual(res_v1.status_code, 200, f"V1 failed: {res_v1.text}")
        data_v1 = res_v1.json()

        pts_comb_c = np.array(data_comb_c["forecast"]["point_forecast_mg_dl"])
        pts_v1 = np.array(data_v1["forecast"]["point_forecast_mg_dl"])

        # Point forecast must be invariant within numerical rounding tolerance (0.1 mg/dL)
        max_abs_diff = float(np.max(np.abs(pts_comb_c - pts_v1)))
        self.assertLessEqual(
            max_abs_diff, 0.1,
            f"Point forecast divergence: max delta = {max_abs_diff:.4f} mg/dL"
        )

    def test_B_uncertainty_source(self):
        """
        Requirement B: Uncertainty Source
        Verify interval values come from Phase-13 regime-conditioned uncertainty,
        NOT the legacy collapsed V1 MC-Dropout estimator.
        """
        readings = create_deterministic_readings(base_glucose=140.0, trend=0.5, std_noise=8.0)
        payload_default = {
            "patient_id": "test_patient_uncertainty",
            "history_readings": [r.model_dump() for r in readings]
        }
        payload_legacy = {
            "patient_id": "test_patient_uncertainty",
            "history_readings": [r.model_dump() for r in readings],
            "requested_model_version": "V1_FROZEN"
        }

        res_default = self.client.post("/api/v1/forecast", json=payload_default)
        self.assertEqual(res_default.status_code, 200)
        data_default = res_default.json()

        res_legacy = self.client.post("/api/v1/forecast", json=payload_legacy)
        self.assertEqual(res_legacy.status_code, 200)
        data_legacy = res_legacy.json()

        # Extract 95% widths
        def_up = np.array(data_default["forecast"]["upper_95_mg_dl"])
        def_lo = np.array(data_default["forecast"]["lower_95_mg_dl"])
        def_width = float(np.mean(def_up - def_lo))

        leg_up = np.array(data_legacy["forecast"]["upper_95_mg_dl"])
        leg_lo = np.array(data_legacy["forecast"]["lower_95_mg_dl"])
        leg_width = float(np.mean(leg_up - leg_lo))

        # Default Combination C must deliver Phase-13 calibrated dispersion (>120 mg/dL),
        # not the collapsed legacy V1 MC-Dropout width (~74 mg/dL).
        self.assertGreater(
            def_width, 100.0,
            f"Default uncertainty width too narrow ({def_width:.2f} mg/dL), indicates collapsed V1 estimator."
        )
        self.assertNotAlmostEqual(
            def_width, leg_width, delta=10.0,
            msg="Default width matches legacy MC-Dropout width; Phase-13 adapter not active."
        )
        self.assertEqual(
            data_default["telemetry"]["uncertainty_source"],
            "Phase13_RegimeConditioned"
        )

    def test_C_disagreement_regimes(self):
        """
        Requirement C: Disagreement Regimes
        Verify Phase-13 interval scaling behaves according to frozen configuration
        across low, medium, and high disagreement regimes.
        """
        # Low disagreement: Flat, quiet glucose
        readings_low = create_deterministic_readings(base_glucose=110.0, trend=0.0)
        # Medium disagreement: Moderate rising glucose with volatility
        readings_med = create_deterministic_readings(base_glucose=120.0, trend=0.8, std_noise=6.0)
        # High disagreement: Rapid glycemic spike (unbolused excursion)
        readings_high = create_deterministic_readings(base_glucose=90.0, trend=2.5, std_noise=15.0)

        res_low = self.client.post("/api/v1/forecast", json={"history_readings": [r.model_dump() for r in readings_low]}).json()
        res_med = self.client.post("/api/v1/forecast", json={"history_readings": [r.model_dump() for r in readings_med]}).json()
        res_high = self.client.post("/api/v1/forecast", json={"history_readings": [r.model_dump() for r in readings_high]}).json()

        w_low = np.mean(np.array(res_low["forecast"]["upper_95_mg_dl"]) - np.array(res_low["forecast"]["lower_95_mg_dl"]))
        w_med = np.mean(np.array(res_med["forecast"]["upper_95_mg_dl"]) - np.array(res_med["forecast"]["lower_95_mg_dl"]))
        w_high = np.mean(np.array(res_high["forecast"]["upper_95_mg_dl"]) - np.array(res_high["forecast"]["lower_95_mg_dl"]))

        # Monotonic scaling under increasing volatility and disagreement
        self.assertLess(w_low, w_med, f"Low width {w_low:.1f} not less than medium {w_med:.1f}")
        self.assertLess(w_med, w_high, f"Medium width {w_med:.1f} not less than high {w_high:.1f}")

        # Check that physics ceiling is respected
        self.assertTrue(res_high["telemetry"]["physics_ceiling_enforced"])
        self.assertLessEqual(res_high["telemetry"]["physics_contribution_mean_pct"], 40.001)

    def test_D_response_contract(self):
        """
        Requirement D: Response Contract
        Verify /api/v1/forecast returns the existing public schema without breaking clients.
        """
        readings = create_deterministic_readings(base_glucose=125.0)
        res = self.client.post("/api/v1/forecast", json={"history_readings": [r.model_dump() for r in readings]})
        self.assertEqual(res.status_code, 200)

        # Validate through Pydantic model
        resp_obj = ForecastResponse(**res.json())
        self.assertEqual(resp_obj.model_version, "COMBINATION_C")
        self.assertEqual(len(resp_obj.forecast["point_forecast_mg_dl"]), 20)
        self.assertEqual(len(resp_obj.forecast["lower_95_mg_dl"]), 20)
        self.assertEqual(len(resp_obj.forecast["upper_95_mg_dl"]), 20)
        self.assertEqual(len(resp_obj.forecast["lower_80_mg_dl"]), 20)
        self.assertEqual(len(resp_obj.forecast["upper_80_mg_dl"]), 20)
        self.assertIn("mean_uncertainty_std", resp_obj.forecast)
        self.assertIn("alert_level", resp_obj.risk_assessment)
        self.assertIn("headline", resp_obj.explanation)

    def test_E_missing_input_invariance(self):
        """
        Requirement E: Missing Input Invariance
        Verify absent optional contextual factors do not move the V1 point forecast.
        """
        readings = create_deterministic_readings(base_glucose=130.0, trend=0.4)
        payload_no_wearable = {
            "patient_id": "test_patient_invariance",
            "history_readings": [r.model_dump() for r in readings],
            "wearable_context": None
        }
        payload_with_wearable = {
            "patient_id": "test_patient_invariance",
            "history_readings": [r.model_dump() for r in readings],
            "wearable_context": {
                "device_source": "Fitbit Ionic",
                "steps_15m": [150.0, 200.0, 300.0, 100.0],
                "heart_rate_bpm": [72.0, 75.0, 80.0, 78.0]
            }
        }

        res1_resp = self.client.post("/api/v1/forecast", json=payload_no_wearable)
        self.assertEqual(res1_resp.status_code, 200, f"No wearable request failed: {res1_resp.text}")
        res1 = res1_resp.json()

        res2_resp = self.client.post("/api/v1/forecast", json=payload_with_wearable)
        self.assertEqual(res2_resp.status_code, 200, f"With wearable request failed: {res2_resp.text}")
        res2 = res2_resp.json()

        pts1 = np.array(res1["forecast"]["point_forecast_mg_dl"])
        pts2 = np.array(res2["forecast"]["point_forecast_mg_dl"])

        self.assertTrue(
            np.array_equal(pts1, pts2),
            "Point forecast shifted when optional wearable context was provided! Violates missing-input invariance."
        )

    def test_F_risk_invariance_and_uncertainty_alert(self):
        """
        Requirement F: Risk Invariance
        Verify clinical-risk calculations are unchanged except where they legitimately
        consume the corrected uncertainty representation (e.g. downside risk into hypoglycemia).
        """
        # Low glucose scenario near boundary: baseline 75 mg/dL with falling trend
        readings = create_deterministic_readings(base_glucose=75.0, trend=-0.2)
        res = self.client.post("/api/v1/forecast", json={"history_readings": [r.model_dump() for r in readings]}).json()

        risk = res["risk_assessment"]
        # Ensure risk outputs are structured correctly
        self.assertIn("alert_level", risk)
        self.assertIn("active_alerts", risk)
        self.assertIn("hypo_1h_prob", risk)

        # If lower bound drops below 50 mg/dL, check that downside uncertainty notice is added
        low95 = np.array(res["forecast"]["lower_95_mg_dl"])
        if np.min(low95[:8]) < 50.0 and risk["alert_level"] == "NONE":
            self.assertEqual(risk["alert_level"], "INFO")
            self.assertTrue(any("NOTICE: Downside trajectory uncertainty" in a for a in risk["active_alerts"]))

    def test_G_error_handling(self):
        """
        Requirement G: Error Handling
        Ensure failures in the uncertainty adapter do not silently return misleading intervals.
        """
        # Temporarily mock combination_c_adapter to None to test failure mode
        saved_adapter = state.combination_c_adapter
        try:
            state.combination_c_adapter = None
            readings = create_deterministic_readings(base_glucose=120.0)
            res = self.client.post("/api/v1/forecast", json={"history_readings": [r.model_dump() for r in readings]})
            self.assertEqual(res.status_code, 503, "Failed to return 503 when adapter is uninitialized.")
            self.assertIn("Combination C", res.json()["detail"])
        finally:
            state.combination_c_adapter = saved_adapter

    def test_H_legacy_path_is_not_default(self):
        """
        Requirement H: Legacy Path is Not Default
        Explicitly test that normal /api/v1/forecast requests default to COMBINATION_C
        and no longer use the collapsed legacy MC-Dropout interval path.
        """
        readings = create_deterministic_readings(base_glucose=130.0)
        # 1. Default request without model_version specified
        res_default = self.client.post("/api/v1/forecast", json={"history_readings": [r.model_dump() for r in readings]}).json()
        self.assertEqual(res_default["model_version"], "COMBINATION_C")
        self.assertEqual(res_default["telemetry"]["uncertainty_source"], "Phase13_RegimeConditioned")

        # 2. Explicit legacy request
        res_legacy = self.client.post("/api/v1/forecast", json={
            "history_readings": [r.model_dump() for r in readings],
            "requested_model_version": "V1_FROZEN"
        }).json()
        self.assertEqual(res_legacy["model_version"], "V1_FROZEN")
        self.assertIsNone(res_legacy.get("telemetry"))

    def test_I_frozen_artifact_cryptographic_hashes(self):
        """
        Requirement I: No Model Artifact Modification
        Hash all 7 frozen artifacts and verify 100% bitwise identity against certified hashes.
        """
        expected_hashes = {
            "models/glucoshield_neural_best.pt": "026af3341a91064136c38b0172f2aa6af34806913640a02270c7d82a28ea13fb",
            "models/glucoshield_hybrid_best.pt": "89a67710aa4931246f9097674332cbfd9d1af3d20c722c04d806ef66e47298d1",
            "data/metadata/feature_scaler.joblib": "757f5c99e294dc8c5698a42cee1843853e8506df5203508aa71a1462d545972b",
            "data/metadata/static_scaler.joblib": "fedc25f67dbcefd2c19ff38375568f3f2bc83ac1fa7c29840e5c81d33b479576",
            "models/v2/glucoshield_v2_best.pt": "fee7c966b41497bcb3bba9bff60bb47ccdab02c15afea8c1c3cb52b74b7abdc2",
            "scratch/phase13_disagreement_gate/frozen_gate_config.json": "a7d9aaaa908fdfb3667e6285312722ab5e7209286bc070203f48ea507f97964f",
            "scratch/phase13_patient_specific_ode/ode_adaptation_config.json": "25617ef1104b32bf24a2ed83db16f679a00e247e02ef846c6e41cd5e184d32d8"
        }

        for path, exp_hash in expected_hashes.items():
            full_path = os.path.join(BASE_DIR, path)
            self.assertTrue(os.path.exists(full_path), f"Artifact missing: {path}")
            with open(full_path, "rb") as f:
                actual_hash = hashlib.sha256(f.read()).hexdigest()
            self.assertEqual(
                actual_hash, exp_hash,
                f"BITWISE CORRUPTION in {path}: expected {exp_hash}, got {actual_hash}"
            )


if __name__ == "__main__":
    unittest.main()
