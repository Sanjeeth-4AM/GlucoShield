"""
GlucoShield Unit Tests — Persistence Endpoints & Longitudinal Tracking
======================================================================
Tests for patient CRUD, CGM ingestion, meal logging, insulin dosing,
wearables, and history retrieval.
"""

import unittest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.base import Base
from db.models import User, PatientProfile
from db.session import get_db
from api.service import app
from api.security import create_access_token, get_password_hash

class TestPersistenceEndpoints(unittest.TestCase):
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

        db = cls.TestSessionLocal()
        cls.user = User(
            email="researcher_alice@university.edu",
            hashed_password=get_password_hash("ResearchPass2026!"),
            is_active=True,
            is_superuser=False
        )
        db.add(cls.user)
        db.commit()

        cls.token = create_access_token({"sub": cls.user.id, "email": cls.user.email})
        cls.auth_headers = {"Authorization": f"Bearer {cls.token}"}
        db.close()

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()

    def test_patient_crud_flow(self):
        # 1. Create Patient
        create_res = self.client.post("/api/v1/patients", headers=self.auth_headers, json={
            "patient_display_id": "PATIENT-DEMO-99",
            "age": 50.0,
            "bmi": 27.2,
            "hba1c": 60.0,
            "fasting_glucose": 135.0,
            "is_t1dm": 1.0
        })
        self.assertEqual(create_res.status_code, 201)
        patient_data = create_res.json()
        patient_id = patient_data["id"]
        self.assertEqual(patient_data["age"], 50.0)

        # 2. Get Patient
        get_res = self.client.get(f"/api/v1/patients/{patient_id}", headers=self.auth_headers)
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.json()["patient_display_id"], "PATIENT-DEMO-99")

        # 3. Update Patient
        update_res = self.client.put(f"/api/v1/patients/{patient_id}", headers=self.auth_headers, json={
            "hba1c": 57.5,
            "bmi": 26.8
        })
        self.assertEqual(update_res.status_code, 200)
        self.assertEqual(update_res.json()["hba1c"], 57.5)
        self.assertEqual(update_res.json()["bmi"], 26.8)

    def test_cgm_ingestion_and_querying(self):
        # Get user's primary patient
        p_res = self.client.get("/api/v1/patients/me", headers=self.auth_headers)
        patient_id = p_res.json()["id"]

        # Ingest batch of 4 CGM readings (1 hour)
        base_time = datetime(2026, 8, 30, 10, 0, 0)
        readings = [
            {
                "timestamp": (base_time + timedelta(minutes=15 * i)).isoformat(),
                "cgm_glucose": 120.0 + i * 5.0,
                "insulin_bolus": 1.0 if i == 0 else 0.0,
                "insulin_basal": 0.5,
                "meal_carbs": 25.0 if i == 0 else 0.0
            }
            for i in range(4)
        ]

        post_res = self.client.post(
            f"/api/v1/patients/{patient_id}/cgm",
            headers=self.auth_headers,
            json={"readings": readings}
        )
        self.assertEqual(post_res.status_code, 201)
        self.assertEqual(len(post_res.json()), 4)

        # Query CGM history
        get_res = self.client.get(
            f"/api/v1/patients/{patient_id}/cgm?limit=10",
            headers=self.auth_headers
        )
        self.assertEqual(get_res.status_code, 200)
        cgm_history = get_res.json()
        self.assertGreaterEqual(len(cgm_history), 4)
        self.assertEqual(cgm_history[0]["cgm_glucose"], 120.0)

    def test_meal_and_insulin_logging(self):
        p_res = self.client.get("/api/v1/patients/me", headers=self.auth_headers)
        patient_id = p_res.json()["id"]

        # 1. Log Meal
        meal_res = self.client.post(
            f"/api/v1/patients/{patient_id}/meals",
            headers=self.auth_headers,
            json={
                "meal_name": "Oatmeal with Blueberries",
                "portion_g": 200.0,
                "carbs_g": 42.0,
                "calories_kcal": 280.0,
                "protein_g": 9.0,
                "fat_g": 5.0,
                "user_confirmed": True
            }
        )
        self.assertEqual(meal_res.status_code, 201)
        self.assertEqual(meal_res.json()["carbs_g"], 42.0)

        # Query Meals
        get_meals_res = self.client.get(
            f"/api/v1/patients/{patient_id}/meals",
            headers=self.auth_headers
        )
        self.assertEqual(get_meals_res.status_code, 200)
        self.assertGreaterEqual(len(get_meals_res.json()), 1)

        # 2. Log Insulin
        ins_res = self.client.post(
            f"/api/v1/patients/{patient_id}/insulin",
            headers=self.auth_headers,
            json={
                "dose_type": "bolus",
                "units": 3.5,
                "insulin_type": "Humalog",
                "notes": "Pre-breakfast bolus"
            }
        )
        self.assertEqual(ins_res.status_code, 201)
        self.assertEqual(ins_res.json()["units"], 3.5)

        # Query Insulin
        get_ins_res = self.client.get(
            f"/api/v1/patients/{patient_id}/insulin",
            headers=self.auth_headers
        )
        self.assertEqual(get_ins_res.status_code, 200)
        self.assertGreaterEqual(len(get_ins_res.json()), 1)

    def test_wearable_telemetry_persistence(self):
        p_res = self.client.get("/api/v1/patients/me", headers=self.auth_headers)
        patient_id = p_res.json()["id"]

        wear_res = self.client.post(
            f"/api/v1/patients/{patient_id}/wearables",
            headers=self.auth_headers,
            json={
                "step_count": 480.0,
                "heart_rate_bpm": 84.0,
                "device_source": "Garmin Forerunner"
            }
        )
        self.assertEqual(wear_res.status_code, 201)
        self.assertEqual(wear_res.json()["step_count"], 480.0)

        get_wear_res = self.client.get(
            f"/api/v1/patients/{patient_id}/wearables",
            headers=self.auth_headers
        )
        self.assertEqual(get_wear_res.status_code, 200)
        self.assertGreaterEqual(len(get_wear_res.json()), 1)

    def test_forecast_record_persistence_and_query(self):
        p_res = self.client.get("/api/v1/patients/me", headers=self.auth_headers)
        patient_id = p_res.json()["id"]

        db = self.TestSessionLocal()
        from db.models import ForecastRecord
        f_rec = ForecastRecord(
            patient_id=patient_id,
            timestamp=datetime.utcnow(),
            current_glucose=122.5,
            current_iob=1.2,
            current_cob=25.0,
            point_forecast=[123.0 + i for i in range(20)],
            lower_80=[115.0 + i for i in range(20)],
            upper_80=[131.0 + i for i in range(20)],
            lower_95=[110.0 + i for i in range(20)],
            upper_95=[136.0 + i for i in range(20)],
            hybrid_components={"effective_physics_weight": [0.4] * 20},
            risk_assessment={"alert_level": "NORMAL", "primary_status": "STABLE"},
            explanation={"headline": "Stable Glycemic Trajectory"},
            disclaimer="RESEARCH PROTOTYPE NOTICE: System validation only."
        )
        db.add(f_rec)
        db.commit()
        rec_id = f_rec.id
        db.close()

        # Query via REST endpoint
        get_fc_res = self.client.get(
            f"/api/v1/patients/{patient_id}/forecasts",
            headers=self.auth_headers
        )
        self.assertEqual(get_fc_res.status_code, 200)
        fc_list = get_fc_res.json()
        self.assertGreaterEqual(len(fc_list), 1)
        self.assertEqual(fc_list[0]["id"], rec_id)
        self.assertEqual(len(fc_list[0]["point_forecast"]), 20)
        self.assertEqual(len(fc_list[0]["lower_95"]), 20)
        self.assertEqual(len(fc_list[0]["upper_95"]), 20)
        self.assertIn("RESEARCH PROTOTYPE NOTICE", fc_list[0]["disclaimer"])

if __name__ == "__main__":
    unittest.main()
