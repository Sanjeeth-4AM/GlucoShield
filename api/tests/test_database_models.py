"""
GlucoShield Unit Tests — Database Models & Schema Relationships
==============================================================
"""

import unittest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.base import Base
from db.models import (
    User,
    PatientProfile,
    CGMReading,
    InsulinRecord,
    MealRecord,
    FoodAnalysisRecord,
    ForecastRecord,
    WhatIfRecord,
    DecisionRecord,
    WearableObservation
)

class TestDatabaseModels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine)

    def setUp(self):
        self.db = self.Session()

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def test_user_and_patient_profile_creation(self):
        user = User(
            email="test_doctor@hospital.org",
            hashed_password="fake_hashed_password_123",
            full_name="Dr. Sarah Connor"
        )
        self.db.add(user)
        self.db.flush()

        self.assertIsNotNone(user.id)
        self.assertEqual(len(user.id), 36) # UUID
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_superuser)

        patient = PatientProfile(
            user_id=user.id,
            patient_display_id="PATIENT-001",
            age=52.0,
            bmi=28.4,
            hba1c=62.0
        )
        self.db.add(patient)
        self.db.commit()

        # Query back
        fetched_patient = self.db.query(PatientProfile).filter(PatientProfile.id == patient.id).first()
        self.assertIsNotNone(fetched_patient)
        self.assertEqual(fetched_patient.user.email, "test_doctor@hospital.org")
        self.assertEqual(fetched_patient.hba1c, 62.0)

    def test_longitudinal_cgm_and_events_persistence(self):
        patient = PatientProfile(patient_display_id="PATIENT-002")
        self.db.add(patient)
        self.db.flush()

        # Ingest CGM
        cgm = CGMReading(
            patient_id=patient.id,
            timestamp=datetime(2026, 8, 30, 12, 0),
            cgm_glucose=145.0,
            insulin_bolus=2.5,
            meal_carbs=30.0
        )
        self.db.add(cgm)

        # Ingest Meal
        meal = MealRecord(
            patient_id=patient.id,
            timestamp=datetime(2026, 8, 30, 12, 0),
            meal_name="Grilled Salmon & Quinoa",
            carbs_g=30.0,
            user_confirmed=True
        )
        self.db.add(meal)

        # Ingest Insulin
        insulin = InsulinRecord(
            patient_id=patient.id,
            timestamp=datetime(2026, 8, 30, 12, 0),
            dose_type="bolus",
            units=2.5,
            insulin_type="Aspart"
        )
        self.db.add(insulin)

        # Ingest Wearable
        wearable = WearableObservation(
            patient_id=patient.id,
            timestamp=datetime(2026, 8, 30, 12, 0),
            step_count=350.0,
            heart_rate_bpm=78.0,
            device_source="Apple Watch Ultra"
        )
        self.db.add(wearable)
        self.db.commit()

        # Verify relationships
        refreshed = self.db.query(PatientProfile).filter(PatientProfile.id == patient.id).first()
        self.assertEqual(len(refreshed.cgm_readings), 1)
        self.assertEqual(len(refreshed.meal_records), 1)
        self.assertEqual(len(refreshed.insulin_records), 1)
        self.assertEqual(len(refreshed.wearable_observations), 1)
        self.assertEqual(refreshed.wearable_observations[0].step_count, 350.0)

    def test_forecast_and_decision_records(self):
        patient = PatientProfile(patient_display_id="PATIENT-003")
        self.db.add(patient)
        self.db.flush()

        forecast = ForecastRecord(
            patient_id=patient.id,
            timestamp=datetime.utcnow(),
            current_glucose=135.0,
            point_forecast=[135.0, 138.0, 142.0],
            lower_80=[125.0, 128.0, 130.0],
            upper_80=[145.0, 148.0, 154.0],
            lower_95=[115.0, 118.0, 120.0],
            upper_95=[155.0, 158.0, 164.0],
            risk_assessment={"alert_level": "NORMAL", "hypo_prob_1h": 0.02},
            explanation={"summary": "Stable trajectory"},
            disclaimer="Research use only"
        )
        self.db.add(forecast)

        what_if = WhatIfRecord(
            patient_id=patient.id,
            timestamp=datetime.utcnow(),
            scenario_name="Test Meal",
            scenario_meal_carbs_g=45.0,
            scenario_insulin_bolus_u=3.5,
            simulated_trajectory=[135.0, 150.0, 165.0, 140.0],
            nadir_glucose=120.0,
            time_to_nadir_min=180,
            peak_glucose=165.0,
            time_to_peak_min=45,
            time_in_range_pct=100.0
        )
        self.db.add(what_if)
        self.db.flush()

        decision = DecisionRecord(
            patient_id=patient.id,
            timestamp=datetime.utcnow(),
            forecast_id=forecast.id,
            what_if_id=what_if.id,
            alert_status="NORMAL",
            recommended_action="Maintain routine monitoring",
            decision_summary={"recommendation": "Optimal control"},
            disclaimer="Research use only"
        )
        self.db.add(decision)
        self.db.commit()

        fetched_dec = self.db.query(DecisionRecord).filter(DecisionRecord.id == decision.id).first()
        self.assertIsNotNone(fetched_dec)
        self.assertEqual(fetched_dec.alert_status, "NORMAL")
        self.assertEqual(fetched_dec.forecast_id, forecast.id)

if __name__ == "__main__":
    unittest.main()
