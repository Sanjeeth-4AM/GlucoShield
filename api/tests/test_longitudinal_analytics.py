"""
GlucoShield Phase 14 — Longitudinal Analytics Test Suite
=========================================================
Tests for glycemic summaries, time-in-range metrics, diurnal AGP profiles,
causal forecast accuracy evaluations, risk factor tracking, unified timelines,
time-window filtering, IDOR protection, and empty/sparse data safeguards.
"""

import unittest
from datetime import datetime, timedelta
import numpy as np
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.base import Base
from db.models import (
    User,
    PatientProfile,
    CGMReading,
    MealRecord,
    InsulinRecord,
    ForecastRecord,
    DecisionRecord,
    WearableObservation
)
from db.session import get_db
from api.service import app
from api.security import create_access_token, get_password_hash

class TestLongitudinalAnalytics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        Base.metadata.create_all(cls.test_engine)
        cls.TestSessionLocal = sessionmaker(
            bind=cls.test_engine,
            autocommit=False,
            autoflush=False
        )

        def override_get_db():
            db = cls.TestSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

        # Create two distinct users for IDOR testing
        db = cls.TestSessionLocal()

        # User A
        cls.user_a = User(
            email="user_alice@clinical.org",
            hashed_password=get_password_hash("AlicePass2026!"),
            is_active=True,
            is_superuser=False
        )
        db.add(cls.user_a)

        # User B
        cls.user_b = User(
            email="user_bob@clinical.org",
            hashed_password=get_password_hash("BobPass2026!"),
            is_active=True,
            is_superuser=False
        )
        db.add(cls.user_b)
        db.commit()

        # Patient for User A
        cls.patient_a = PatientProfile(
            user_id=cls.user_a.id,
            patient_display_id="PATIENT-ALICE-01",
            age=45.0,
            bmi=26.0,
            hba1c=58.0,
            is_t1dm=1.0
        )
        db.add(cls.patient_a)

        # Empty Patient for User A (to test empty history)
        cls.patient_a_empty = PatientProfile(
            user_id=cls.user_a.id,
            patient_display_id="PATIENT-ALICE-EMPTY",
            age=35.0,
            bmi=24.0,
            hba1c=50.0,
            is_t1dm=1.0
        )
        db.add(cls.patient_a_empty)

        # Patient for User B
        cls.patient_b = PatientProfile(
            user_id=cls.user_b.id,
            patient_display_id="PATIENT-BOB-01",
            age=52.0,
            bmi=28.5,
            hba1c=64.0,
            is_t1dm=0.0
        )
        db.add(cls.patient_b)
        db.commit()

        # Capture IDs as plain strings to avoid SQLAlchemy session detachment
        cls.patient_a_id = str(cls.patient_a.id)
        cls.patient_a_empty_id = str(cls.patient_a_empty.id)
        cls.patient_b_id = str(cls.patient_b.id)

        cls.token_a = create_access_token({"sub": cls.user_a.id, "email": cls.user_a.email})
        cls.token_b = create_access_token({"sub": cls.user_b.id, "email": cls.user_b.email})
        cls.headers_a = {"Authorization": f"Bearer {cls.token_a}"}
        cls.headers_b = {"Authorization": f"Bearer {cls.token_b}"}

        db.close()

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()

    def test_01_empty_patient_history(self):
        """Empty patient records must return HTTP 200 with has_data=False and no NaNs or 500 errors."""
        p_id = self.patient_a_empty_id

        # 1. Summary
        res = self.client.get(f"/api/v1/patients/{p_id}/analytics/summary", headers=self.headers_a)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["has_data"])
        self.assertEqual(data["total_readings"], 0)
        self.assertEqual(data["days_of_data"], 0.0)
        self.assertIsNone(data["glycemic_variability"]["mean_glucose"])
        self.assertIsNone(data["glycemic_variability"]["cv_pct"])
        self.assertIsNone(data["glycemic_bands"]["tir_pct"])

        # 2. Glucose
        res = self.client.get(f"/api/v1/patients/{p_id}/analytics/glucose", headers=self.headers_a)
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.json()["has_data"])
        self.assertEqual(res.json()["glucose_readings"], [])

        # 3. Diurnal
        res = self.client.get(f"/api/v1/patients/{p_id}/analytics/diurnal", headers=self.headers_a)
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.json()["has_data"])
        self.assertEqual(len(res.json()["hourly_agp"]), 24)
        for h_pt in res.json()["hourly_agp"]:
            self.assertEqual(h_pt["reading_count"], 0)
            self.assertIsNone(h_pt["mean_glucose"])

        # 4. Forecast performance
        res = self.client.get(f"/api/v1/patients/{p_id}/analytics/forecast-performance", headers=self.headers_a)
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.json()["has_data"])
        self.assertEqual(res.json()["total_forecasts_logged"], 0)
        self.assertIsNone(res.json()["overall_mae_mg_dl"])

        # 5. Risk Factors
        res = self.client.get(f"/api/v1/patients/{p_id}/analytics/risk-factors", headers=self.headers_a)
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.json()["has_data"])
        self.assertEqual(res.json()["total_alerts"], 0)

        # 6. Timeline
        res = self.client.get(f"/api/v1/patients/{p_id}/analytics/timeline", headers=self.headers_a)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["total_events"], 0)
        self.assertEqual(res.json()["events"], [])

    def test_02_single_reading_history(self):
        """Single reading should avoid division by zero and produce 0.0 std and 0.0 CV."""
        db = self.TestSessionLocal()
        t_single = datetime(2026, 9, 1, 12, 0, 0)
        r = CGMReading(
            patient_id=self.patient_a_id,
            timestamp=t_single,
            cgm_glucose=125.0,
            insulin_bolus=0.0,
            insulin_basal=0.5,
            meal_carbs=0.0
        )
        db.add(r)
        db.commit()
        db.close()

        res = self.client.get(
            f"/api/v1/patients/{self.patient_a_id}/analytics/glucose?period=24h",
            headers=self.headers_a
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["has_data"])
        self.assertEqual(data["total_readings"], 1)
        self.assertEqual(data["glycemic_variability"]["mean_glucose"], 125.0)
        self.assertEqual(data["glycemic_variability"]["std_glucose"], 0.0)
        self.assertEqual(data["glycemic_variability"]["cv_pct"], 0.0)
        self.assertEqual(data["glycemic_bands"]["tir_pct"], 100.0)
        self.assertEqual(data["glycemic_bands"]["tir_minutes"], 15)

    def test_03_glycemic_variability_and_bands_calculation(self):
        """Validates exact consensus TIR bands, CV, GMI, and LBGI/HBGI indices."""
        db = self.TestSessionLocal()
        base_t = datetime(2026, 9, 5, 0, 0, 0)

        # Construct synthetic sequence of 60 points (15 hours):
        # 4 points at 50 mg/dL (TBR L2: <54)
        # 6 points at 60 mg/dL (TBR L1: 54-69)
        # 30 points at 110 mg/dL (TIR: 70-180 & TITR: 70-140)
        # 10 points at 160 mg/dL (TIR: 70-180, outside TITR)
        # 6 points at 200 mg/dL (TAR L1: 181-250)
        # 4 points at 280 mg/dL (TAR L2: >250)
        # Total = 60 readings
        values = [50.0]*4 + [60.0]*6 + [110.0]*30 + [160.0]*10 + [200.0]*6 + [280.0]*4
        readings = []
        for i, val in enumerate(values):
            readings.append(CGMReading(
                patient_id=self.patient_a_id,
                timestamp=base_t + timedelta(minutes=i * 15),
                cgm_glucose=val,
                insulin_bolus=0.0,
                insulin_basal=0.5,
                meal_carbs=0.0
            ))
        db.add_all(readings)
        db.commit()
        db.close()

        start_str = base_t.isoformat()
        end_str = (base_t + timedelta(minutes=65 * 15)).isoformat()

        res = self.client.get(
            f"/api/v1/patients/{self.patient_a_id}/analytics/summary?start_time={start_str}&end_time={end_str}",
            headers=self.headers_a
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["has_data"])
        self.assertEqual(data["total_readings"], 60)

        bands = data["glycemic_bands"]
        # TIR: 40/60 = 66.67%
        self.assertAlmostEqual(bands["tir_pct"], 66.67, places=1)
        self.assertEqual(bands["tir_minutes"], 40 * 15)
        # TITR: 30/60 = 50.0%
        self.assertAlmostEqual(bands["titr_pct"], 50.0, places=1)
        self.assertEqual(bands["titr_minutes"], 30 * 15)
        # TBR L1: 6/60 = 10.0%
        self.assertAlmostEqual(bands["tbr_l1_pct"], 10.0, places=1)
        self.assertEqual(bands["tbr_l1_minutes"], 6 * 15)
        # TBR L2: 4/60 = 6.67%
        self.assertAlmostEqual(bands["tbr_l2_pct"], 6.67, places=1)
        self.assertEqual(bands["tbr_l2_minutes"], 4 * 15)
        # TAR L1: 6/60 = 10.0%
        self.assertAlmostEqual(bands["tar_l1_pct"], 10.0, places=1)
        # TAR L2: 4/60 = 6.67%
        self.assertAlmostEqual(bands["tar_l2_pct"], 6.67, places=1)

        # Variability
        var = data["glycemic_variability"]
        expected_mean = float(np.mean(values))
        expected_gmi = round(3.31 + 0.02392 * expected_mean, 2)
        self.assertAlmostEqual(var["mean_glucose"], expected_mean, places=1)
        self.assertAlmostEqual(var["gmi_pct"], expected_gmi, places=1)
        self.assertGreater(var["lbgi"], 0.0)
        self.assertGreater(var["hbgi"], 0.0)

    def test_04_hypo_and_hyper_episodes(self):
        """Verifies contiguous hypo and hyper episodes count and mean durations."""
        db = self.TestSessionLocal()
        base_t = datetime(2026, 9, 7, 0, 0, 0)

        # Sequence:
        # 2 readings normal (120)
        # 3 readings hypo (60, 50, 65) -> Hypo Episode 1 (duration: 45 min, severe: True)
        # 2 readings normal (130, 140)
        # 2 readings hypo (65, 68) -> Hypo Episode 2 (duration: 30 min, severe: False)
        # 2 readings normal (150, 160)
        # 4 readings hyper (190, 210, 220, 200) -> Hyper Episode 1 (duration: 60 min)
        # 2 readings normal (140, 130)
        vals = [120, 120, 60, 50, 65, 130, 140, 65, 68, 150, 160, 190, 210, 220, 200, 140, 130]
        readings = [
            CGMReading(
                patient_id=self.patient_a_id,
                timestamp=base_t + timedelta(minutes=i * 15),
                cgm_glucose=float(v)
            )
            for i, v in enumerate(vals)
        ]
        db.add_all(readings)
        db.commit()
        db.close()

        start_str = base_t.isoformat()
        end_str = (base_t + timedelta(minutes=len(vals) * 15)).isoformat()

        res = self.client.get(
            f"/api/v1/patients/{self.patient_a_id}/analytics/glucose?start_time={start_str}&end_time={end_str}",
            headers=self.headers_a
        )
        self.assertEqual(res.status_code, 200)
        ep = res.json()["episodes"]
        self.assertEqual(ep["hypo_episode_count"], 2)
        self.assertEqual(ep["severe_hypo_episode_count"], 1)
        self.assertEqual(ep["hyper_episode_count"], 1)
        self.assertAlmostEqual(ep["mean_hypo_duration_minutes"], 37.5, places=1) # (45 + 30)/2
        self.assertEqual(ep["mean_hyper_duration_minutes"], 60.0)

    def test_05_diurnal_profile_quadrants(self):
        """Verifies diurnal 4-quadrant and 24-hour AGP aggregation."""
        db = self.TestSessionLocal()
        day_t = datetime(2026, 9, 10, 0, 0, 0)

        # Add readings at specific hours
        readings = [
            CGMReading(patient_id=self.patient_a_id, timestamp=day_t + timedelta(hours=3), cgm_glucose=95.0),   # Night
            CGMReading(patient_id=self.patient_a_id, timestamp=day_t + timedelta(hours=8), cgm_glucose=140.0),  # Morning
            CGMReading(patient_id=self.patient_a_id, timestamp=day_t + timedelta(hours=14), cgm_glucose=160.0), # Afternoon
            CGMReading(patient_id=self.patient_a_id, timestamp=day_t + timedelta(hours=21), cgm_glucose=110.0), # Evening
        ]
        db.add_all(readings)
        db.commit()
        db.close()

        start_str = day_t.isoformat()
        end_str = (day_t + timedelta(days=1)).isoformat()

        res = self.client.get(
            f"/api/v1/patients/{self.patient_a_id}/analytics/diurnal?start_time={start_str}&end_time={end_str}",
            headers=self.headers_a
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["has_data"])
        quads = {q["quadrant"]: q for q in data["quadrants"]}

        self.assertEqual(quads["Night"]["reading_count"], 1)
        self.assertEqual(quads["Night"]["mean_glucose"], 95.0)

        self.assertEqual(quads["Morning"]["reading_count"], 1)
        self.assertEqual(quads["Morning"]["mean_glucose"], 140.0)

        self.assertEqual(quads["Afternoon"]["reading_count"], 1)
        self.assertEqual(quads["Afternoon"]["mean_glucose"], 160.0)

        self.assertEqual(quads["Evening"]["reading_count"], 1)
        self.assertEqual(quads["Evening"]["mean_glucose"], 110.0)

        # Check hourly AGP
        agp_map = {pt["hour"]: pt for pt in data["hourly_agp"]}
        self.assertEqual(agp_map[3]["reading_count"], 1)
        self.assertEqual(agp_map[3]["mean_glucose"], 95.0)
        self.assertEqual(agp_map[8]["mean_glucose"], 140.0)
        self.assertEqual(agp_map[0]["reading_count"], 0)

    def test_06_causal_forecast_accuracy_evaluation(self):
        """Verifies causal retrospective evaluation of ForecastRecords against subsequent CGMReadings."""
        db = self.TestSessionLocal()
        fc_t = datetime(2026, 9, 12, 10, 0, 0)

        # Forecast predictions for next 4 steps:
        # Step 1 (10:15): pred=130, l80=120, u80=140, l95=110, u95=150
        # Step 2 (10:30): pred=135, l80=125, u80=145, l95=115, u95=155
        # Step 3 (10:45): pred=140, l80=130, u80=150, l95=120, u95=160
        # Step 4 (11:00): pred=145, l80=135, u80=155, l95=125, u95=165
        point_fc = [130.0, 135.0, 140.0, 145.0] + [150.0] * 16
        lower_80 = [120.0, 125.0, 130.0, 135.0] + [140.0] * 16
        upper_80 = [140.0, 145.0, 150.0, 155.0] + [160.0] * 16
        lower_95 = [110.0, 115.0, 120.0, 125.0] + [130.0] * 16
        upper_95 = [150.0, 155.0, 160.0, 165.0] + [170.0] * 16

        fc_rec = ForecastRecord(
            patient_id=self.patient_a_id,
            timestamp=fc_t,
            current_glucose=125.0,
            current_iob=1.2,
            current_cob=20.0,
            point_forecast=point_fc,
            lower_80=lower_80,
            upper_80=upper_80,
            lower_95=lower_95,
            upper_95=upper_95,
            risk_assessment={"alert_level": "NORMAL"},
            explanation={"summary": "Stable trajectory"},
            disclaimer="Research only"
        )
        db.add(fc_rec)

        # Actual subsequent readings:
        # Step 1: actual=128 (error = 130 - 128 = +2, inside 80% & 95%)
        # Step 2: actual=140 (error = 135 - 140 = -5, inside 80% & 95%)
        # Step 3: actual=155 (error = 140 - 155 = -15, outside 80%, inside 95%)
        # Step 4: actual=175 (error = 145 - 175 = -30, outside 80% & 95%)
        actuals = [
            CGMReading(patient_id=self.patient_a_id, timestamp=fc_t + timedelta(minutes=15), cgm_glucose=128.0),
            CGMReading(patient_id=self.patient_a_id, timestamp=fc_t + timedelta(minutes=30), cgm_glucose=140.0),
            CGMReading(patient_id=self.patient_a_id, timestamp=fc_t + timedelta(minutes=45), cgm_glucose=155.0),
            CGMReading(patient_id=self.patient_a_id, timestamp=fc_t + timedelta(minutes=60), cgm_glucose=175.0),
        ]
        db.add_all(actuals)
        db.commit()
        db.close()

        start_str = (fc_t - timedelta(hours=1)).isoformat()
        end_str = (fc_t + timedelta(hours=6)).isoformat()

        res = self.client.get(
            f"/api/v1/patients/{self.patient_a_id}/analytics/forecast-performance?start_time={start_str}&end_time={end_str}",
            headers=self.headers_a
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["has_data"])
        self.assertEqual(data["evaluated_pairs_count"], 4)
        self.assertEqual(data["pending_evaluation_count"], 16) # 20 - 4 = 16 pending future horizons

        # Check errors: errors = [+2, -5, -15, -30]
        # abs errors = [2, 5, 15, 30] -> mean = 52 / 4 = 13.0
        # squared errors = [4, 25, 225, 900] = 1154 -> sqrt(1154/4) = sqrt(288.5) = 16.985
        # bias = (2 - 5 - 15 - 30) / 4 = -48 / 4 = -12.0
        self.assertAlmostEqual(data["overall_mae_mg_dl"], 13.0, places=1)
        self.assertAlmostEqual(data["overall_rmse_mg_dl"], 16.99, places=1)
        self.assertAlmostEqual(data["overall_bias_mg_dl"], -12.0, places=1)

        # Coverage:
        # Step 1: in 80, in 95
        # Step 2: in 80, in 95
        # Step 3: not in 80, in 95
        # Step 4: not in 80, not in 95
        # 80% coverage: 2/4 = 50.0%
        # 95% coverage: 3/4 = 75.0%
        self.assertEqual(data["overall_coverage_80_pct"], 50.0)
        self.assertEqual(data["overall_coverage_95_pct"], 75.0)

    def test_07_risk_factors_and_nutrition_tracking(self):
        """Verifies alert counts, IOB/COB at alerts, and nutrition/insulin totals."""
        db = self.TestSessionLocal()
        base_t = datetime(2026, 9, 14, 12, 0, 0)

        # Decisions
        db.add(DecisionRecord(patient_id=self.patient_a_id, timestamp=base_t, alert_status="NORMAL", recommended_action="Monitor", decision_summary={"alert_status": "NORMAL"}, disclaimer="Research only"))
        db.add(DecisionRecord(patient_id=self.patient_a_id, timestamp=base_t + timedelta(hours=2), alert_status="WARNING_HYPO", recommended_action="Snack", decision_summary={"alert_status": "WARNING_HYPO"}, disclaimer="Research only"))
        db.add(DecisionRecord(patient_id=self.patient_a_id, timestamp=base_t + timedelta(hours=4), alert_status="CRITICAL_HYPO", recommended_action="Glucose tabs", decision_summary={"alert_status": "CRITICAL_HYPO"}, disclaimer="Research only"))

        # Meals
        db.add(MealRecord(patient_id=self.patient_a_id, timestamp=base_t + timedelta(hours=1), meal_name="Oatmeal", carbs_g=45.0, calories_kcal=300.0, source="manual"))
        db.add(MealRecord(patient_id=self.patient_a_id, timestamp=base_t + timedelta(hours=6), meal_name="Pasta", carbs_g=75.0, calories_kcal=600.0, source="vision"))

        # Insulin
        db.add(InsulinRecord(patient_id=self.patient_a_id, timestamp=base_t + timedelta(hours=1), dose_type="bolus", units=4.0, insulin_type="Aspart"))
        db.add(InsulinRecord(patient_id=self.patient_a_id, timestamp=base_t + timedelta(hours=6), dose_type="bolus", units=6.0, insulin_type="Aspart"))
        db.add(InsulinRecord(patient_id=self.patient_a_id, timestamp=base_t + timedelta(hours=8), dose_type="basal", units=15.0, insulin_type="Degludec"))

        # Wearable
        db.add(WearableObservation(patient_id=self.patient_a_id, timestamp=base_t + timedelta(hours=3), step_count=4500.0, heart_rate_bpm=78.0))

        db.commit()
        db.close()

        start_str = (base_t - timedelta(hours=1)).isoformat()
        end_str = (base_t + timedelta(hours=12)).isoformat()

        res = self.client.get(
            f"/api/v1/patients/{self.patient_a_id}/analytics/risk-factors?start_time={start_str}&end_time={end_str}",
            headers=self.headers_a
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["has_data"])
        self.assertEqual(data["alert_counts"]["NORMAL"], 1)
        self.assertEqual(data["alert_counts"]["WARNING_HYPO"], 1)
        self.assertEqual(data["alert_counts"]["CRITICAL_HYPO"], 1)

        nut = data["nutrition_totals"]
        self.assertEqual(nut["meal_count"], 2)
        self.assertEqual(nut["total_carbs_g"], 120.0)
        self.assertEqual(nut["total_calories_kcal"], 900.0)

        # Bolus: 10.0 U, Basal: 15.0 U, TDD: 25.0 U
        # Ratio = 10 / 15 = 0.67
        self.assertAlmostEqual(nut["bolus_basal_ratio"], 0.67, places=2)

    def test_08_timeline_pagination_and_type_filtering(self):
        """Verifies unified chronological event timeline pagination and type filtering."""
        p_id = self.patient_a_id

        # Query all events
        res = self.client.get(f"/api/v1/patients/{p_id}/analytics/timeline?limit=10&offset=0&period=all", headers=self.headers_a)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreater(data["total_events"], 10)
        self.assertEqual(len(data["events"]), 10)

        # Filter by meal
        res_meals = self.client.get(f"/api/v1/patients/{p_id}/analytics/timeline?event_type=meal&period=all", headers=self.headers_a)
        self.assertEqual(res_meals.status_code, 200)
        meal_events = res_meals.json()["events"]
        self.assertGreater(len(meal_events), 0)
        for ev in meal_events:
            self.assertEqual(ev["event_type"], "meal")

        # Filter by insulin
        res_ins = self.client.get(f"/api/v1/patients/{p_id}/analytics/timeline?event_type=insulin&period=all", headers=self.headers_a)
        self.assertEqual(res_ins.status_code, 200)
        ins_events = res_ins.json()["events"]
        self.assertGreater(len(ins_events), 0)
        for ev in ins_events:
            self.assertEqual(ev["event_type"], "insulin")

    def test_09_idor_protection(self):
        """User A must NOT be able to access Patient B's analytics (returns HTTP 403)."""
        patient_b_id = self.patient_b_id

        # User A attempting to access Patient B's analytics
        endpoints = [
            f"/api/v1/patients/{patient_b_id}/analytics/summary",
            f"/api/v1/patients/{patient_b_id}/analytics/glucose",
            f"/api/v1/patients/{patient_b_id}/analytics/diurnal",
            f"/api/v1/patients/{patient_b_id}/analytics/forecast-performance",
            f"/api/v1/patients/{patient_b_id}/analytics/risk-factors",
            f"/api/v1/patients/{patient_b_id}/analytics/timeline"
        ]

        for ep in endpoints:
            res = self.client.get(ep, headers=self.headers_a)
            self.assertEqual(res.status_code, 403, f"Failed IDOR test for {ep}: expected 403 got {res.status_code}")

    def test_10_unauthenticated_access(self):
        """Unauthenticated requests must be rejected with HTTP 401."""
        res = self.client.get(f"/api/v1/patients/{self.patient_a_id}/analytics/summary")
        self.assertEqual(res.status_code, 401)

    def test_11_distinction_no_data_vs_zero_value(self):
        """Clearly distinguishes between None/null (NO DATA) and 0.0 (ZERO VALUE)."""
        p_id = self.patient_a_empty_id
        res = self.client.get(f"/api/v1/patients/{p_id}/analytics/summary", headers=self.headers_a)
        data = res.json()
        self.assertFalse(data["has_data"])
        # Mean glucose must be None when no data
        self.assertIsNone(data["glycemic_variability"]["mean_glucose"])
        self.assertIsNone(data["glycemic_variability"]["median_glucose"])
        self.assertIsNone(data["glycemic_bands"]["tir_pct"])
        # Episode counts must be explicitly 0
        self.assertEqual(data["episodes"]["hypo_episode_count"], 0)
        self.assertEqual(data["episodes"]["hyper_episode_count"], 0)

    def test_12_period_filtering_windows(self):
        """Verifies 24h, 7d, 14d, 30d, all window filtering behavior."""
        p_id = self.patient_a_id

        res_24h = self.client.get(f"/api/v1/patients/{p_id}/analytics/summary?period=24h", headers=self.headers_a)
        self.assertEqual(res_24h.status_code, 200)

        res_7d = self.client.get(f"/api/v1/patients/{p_id}/analytics/summary?period=7d", headers=self.headers_a)
        self.assertEqual(res_7d.status_code, 200)

        res_14d = self.client.get(f"/api/v1/patients/{p_id}/analytics/summary?period=14d", headers=self.headers_a)
        self.assertEqual(res_14d.status_code, 200)

        res_30d = self.client.get(f"/api/v1/patients/{p_id}/analytics/summary?period=30d", headers=self.headers_a)
        self.assertEqual(res_30d.status_code, 200)

        res_all = self.client.get(f"/api/v1/patients/{p_id}/analytics/summary?period=all", headers=self.headers_a)
        self.assertEqual(res_all.status_code, 200)

        # Longer windows must capture at least as many readings as shorter windows
        cnt_24h = res_24h.json()["total_readings"]
        cnt_7d = res_7d.json()["total_readings"]
        cnt_all = res_all.json()["total_readings"]
        self.assertGreaterEqual(cnt_7d, cnt_24h)
        self.assertGreaterEqual(cnt_all, cnt_7d)

    def test_13_timeline_ordering_and_metadata(self):
        """Verifies that timeline returns items ordered strictly descending by timestamp."""
        p_id = self.patient_a_id
        res = self.client.get(f"/api/v1/patients/{p_id}/analytics/timeline?limit=25&offset=0&period=all", headers=self.headers_a)
        self.assertEqual(res.status_code, 200)
        events = res.json()["events"]
        self.assertGreater(len(events), 1)
        for i in range(len(events) - 1):
            t_curr = datetime.fromisoformat(events[i]["timestamp"].replace("Z", "+00:00"))
            t_next = datetime.fromisoformat(events[i+1]["timestamp"].replace("Z", "+00:00"))
            self.assertGreaterEqual(t_curr, t_next, "Timeline events must be descending in time")

if __name__ == "__main__":
    unittest.main()
