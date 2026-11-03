"""
GlucoShield — Reproducible Synthetic Demo Patient Seeding Script
================================================================
Sets up a dedicated synthetic demo patient (isolated from real patient data)
with 96 consecutive 15-minute CGM observations ingested through the
supported API endpoint: POST /api/v1/patients/{patient_id}/cgm.

Then executes certified Combination C forecast inference and verifies
that the trajectory, uncertainty intervals, risk assessment, explanation,
and database forecast_records persistence are fully validated.
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

BASE_DIR = "D:/ML PROJECT"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from db.session import SessionLocal, engine
from db.models import (
    Base,
    User,
    PatientProfile,
    CGMReading,
    MealRecord,
    InsulinRecord,
    ForecastRecord,
    WhatIfRecord,
    DecisionRecord
)
from api.security import get_password_hash, create_access_token
from api.service import app

DEMO_USER_EMAIL = "demo_user@glucoshield.org"
DEMO_USER_PASSWORD = "DemoPass2026!"
DEMO_PATIENT_DISPLAY_ID = "DEMO-SYNTHETIC-PATIENT-001"

DEMO_PROFILE_FEATURES = {
    "age": 42.0,
    "bmi": 25.8,
    "diabetes_duration_years": 10.0,
    "hba1c": 56.0,
    "glycated_albumin": 17.2,
    "fasting_glucose": 124.0,
    "fasting_c_peptide": 0.85,
    "macrovascular_comp_count": 0.0,
    "microvascular_comp_count": 0.0,
    "is_t1dm": 1.0
}


def generate_96_synthetic_observations(end_time: datetime) -> List[Dict[str, Any]]:
    """
    Generates 96 consecutive 15-minute observations spanning 24 hours.
    Follows a physiologically plausible Type 1 Diabetes profile:
      - Overnight stable baseline (~115-125 mg/dL)
      - Breakfast excursion at step 32 (40g carbs, 3.0 U bolus)
      - Lunch excursion at step 52 (55g carbs, 4.2 U bolus)
      - Dinner excursion at step 76 (50g carbs, 3.8 U bolus)
      - Basal rate: 0.5 U / 15-min interval
    """
    start_time = end_time - timedelta(minutes=15 * 95)
    readings = []

    for step in range(96):
        ts = start_time + timedelta(minutes=15 * step)
        bolus = 0.0
        basal = 0.5
        carbs = 0.0

        # Baseline glucose with gentle circadian wave
        circadian = 4.0 * (1.0 if (24 <= step <= 64) else -1.0)
        glucose = 120.0 + circadian

        # Breakfast: step 32 (08:00)
        if step == 32:
            carbs = 40.0
            bolus = 3.0
        elif 33 <= step <= 48:
            delta = step - 32
            # Smooth bell-shaped excursion peaking at step 37 (+36 mg/dL)
            curve = 36.0 * (delta / 5.0) * (1.8 ** (1.0 - delta / 5.0)) if delta <= 5 else 36.0 * (0.82 ** (delta - 5))
            glucose += curve

        # Lunch: step 52 (13:00)
        if step == 52:
            carbs = 55.0
            bolus = 4.2
        elif 53 <= step <= 68:
            delta = step - 52
            curve = 46.0 * (delta / 6.0) * (1.7 ** (1.0 - delta / 6.0)) if delta <= 6 else 46.0 * (0.80 ** (delta - 6))
            glucose += curve

        # Dinner: step 76 (19:00)
        if step == 76:
            carbs = 50.0
            bolus = 3.8
        elif 77 <= step <= 92:
            delta = step - 76
            curve = 38.0 * (delta / 5.0) * (1.8 ** (1.0 - delta / 5.0)) if delta <= 5 else 38.0 * (0.81 ** (delta - 5))
            glucose += curve

        # Clamp within physiological bounds
        glucose = max(40.0, min(float(glucose), 400.0))

        readings.append({
            "timestamp": ts.isoformat(),
            "cgm_glucose": round(glucose, 1),
            "insulin_bolus": round(bolus, 2),
            "insulin_basal": round(basal, 2),
            "meal_carbs": round(carbs, 1)
        })

    return readings


def seed_demo_patient():
    print("=" * 70)
    print("GLUCOSHIELD: REPRODUCIBLE DEMO PATIENT SEEDING")
    print("=" * 70)

    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        # 1. User Setup
        demo_user = db.query(User).filter(User.email == DEMO_USER_EMAIL).first()
        if not demo_user:
            demo_user = User(
                email=DEMO_USER_EMAIL,
                hashed_password=get_password_hash(DEMO_USER_PASSWORD),
                full_name="Synthetic Demonstration Patient (Non-Clinical)",
                is_active=True,
                is_superuser=False
            )
            db.add(demo_user)
            db.commit()
            db.refresh(demo_user)
            print(f"[1/5] Created demo user account: {demo_user.email} (ID: {demo_user.id})")
        else:
            print(f"[1/5] Demo user account already exists: {demo_user.email} (ID: {demo_user.id})")

        # 2. Patient Profile Setup
        demo_patient = db.query(PatientProfile).filter(
            PatientProfile.patient_display_id == DEMO_PATIENT_DISPLAY_ID
        ).first()

        if not demo_patient:
            demo_patient = PatientProfile(
                user_id=demo_user.id,
                patient_display_id=DEMO_PATIENT_DISPLAY_ID,
                **DEMO_PROFILE_FEATURES
            )
            db.add(demo_patient)
            db.commit()
            db.refresh(demo_patient)
            print(f"[2/5] Created demo patient profile: {demo_patient.patient_display_id} (UUID: {demo_patient.id})")
        else:
            # Ensure static covariates match specification
            for k, v in DEMO_PROFILE_FEATURES.items():
                setattr(demo_patient, k, v)
            demo_patient.user_id = demo_user.id
            db.commit()
            db.refresh(demo_patient)
            print(f"[2/5] Updated existing demo patient profile: {demo_patient.patient_display_id} (UUID: {demo_patient.id})")

        # 3. Purge existing records for demo patient to ensure idempotency
        deleted_cgm = db.query(CGMReading).filter(CGMReading.patient_id == demo_patient.id).delete()
        deleted_meals = db.query(MealRecord).filter(MealRecord.patient_id == demo_patient.id).delete()
        deleted_insulin = db.query(InsulinRecord).filter(InsulinRecord.patient_id == demo_patient.id).delete()
        deleted_forecasts = db.query(ForecastRecord).filter(ForecastRecord.patient_id == demo_patient.id).delete()
        deleted_whatifs = db.query(WhatIfRecord).filter(WhatIfRecord.patient_id == demo_patient.id).delete()
        deleted_decisions = db.query(DecisionRecord).filter(DecisionRecord.patient_id == demo_patient.id).delete()
        db.commit()
        print(f"[3/5] Idempotency reset: Cleared {deleted_cgm} CGM, {deleted_forecasts} forecast records.")

        # 4. Generate 96 consecutive observations
        # End time rounded to last 15-minute boundary in UTC
        now_utc = datetime.now(timezone.utc)
        minute_floor = (now_utc.minute // 15) * 15
        end_time = now_utc.replace(minute=minute_floor, second=0, microsecond=0)

        readings = generate_96_synthetic_observations(end_time)
        print(f"[4/5] Generated {len(readings)} observations spanning {readings[0]['timestamp']} to {readings[-1]['timestamp']}")

        # Ingest via supported API endpoint: POST /api/v1/patients/{patient_id}/cgm
        token = create_access_token({"sub": demo_user.id, "email": demo_user.email})
        auth_headers = {"Authorization": f"Bearer {token}"}

        with TestClient(app) as client:
            ingest_res = client.post(
                f"/api/v1/patients/{demo_patient.id}/cgm",
                headers=auth_headers,
                json={"readings": readings}
            )
            if ingest_res.status_code != 201:
                raise RuntimeError(f"CGM ingestion failed: {ingest_res.status_code} - {ingest_res.text}")
            print(f"[4/5] Successfully ingested {len(ingest_res.json())} CGM readings via POST /api/v1/patients/{demo_patient.id}/cgm")

            # Ingest corresponding meals
            meals = [
                {"timestamp": readings[32]["timestamp"], "meal_name": "Breakfast Oatmeal & Berries", "portion_g": 250.0, "carbs_g": 40.0, "calories_kcal": 320.0, "source": "synthetic_demo"},
                {"timestamp": readings[52]["timestamp"], "meal_name": "Lunch Turkey Wrap & Salad", "portion_g": 300.0, "carbs_g": 55.0, "calories_kcal": 480.0, "source": "synthetic_demo"},
                {"timestamp": readings[76]["timestamp"], "meal_name": "Dinner Grilled Chicken Bowl", "portion_g": 350.0, "carbs_g": 50.0, "calories_kcal": 510.0, "source": "synthetic_demo"}
            ]
            for m in meals:
                client.post(f"/api/v1/patients/{demo_patient.id}/meals", headers=auth_headers, json=m)

            # Ingest corresponding insulin boluses
            boluses = [
                {"timestamp": readings[32]["timestamp"], "dose_type": "bolus", "units": 3.0, "insulin_type": "Rapid-Acting", "notes": "Breakfast bolus"},
                {"timestamp": readings[52]["timestamp"], "dose_type": "bolus", "units": 4.2, "insulin_type": "Rapid-Acting", "notes": "Lunch bolus"},
                {"timestamp": readings[76]["timestamp"], "dose_type": "bolus", "units": 3.8, "insulin_type": "Rapid-Acting", "notes": "Dinner bolus"}
            ]
            for b in boluses:
                client.post(f"/api/v1/patients/{demo_patient.id}/insulin", headers=auth_headers, json=b)

            # 5. Run Live Combination C Forecast on the seeded 96 readings
            print("[5/5] Running Combination C Production Forecaster on demo telemetry...")
            forecast_payload = {
                "patient_id": demo_patient.patient_display_id,
                "history_readings": readings,
                "static_profile": DEMO_PROFILE_FEATURES,
                "requested_model_version": "COMBINATION_C"
            }
            fc_res = client.post("/api/v1/forecast", headers=auth_headers, json=forecast_payload)
            if fc_res.status_code != 200:
                raise RuntimeError(f"Forecast generation failed: {fc_res.status_code} - {fc_res.text}")

            fc_data = fc_res.json()
            point_forecast = fc_data["forecast"]["point_forecast_mg_dl"]
            low80 = fc_data["forecast"]["lower_80_mg_dl"]
            upp80 = fc_data["forecast"]["upper_80_mg_dl"]
            low95 = fc_data["forecast"]["lower_95_mg_dl"]
            upp95 = fc_data["forecast"]["upper_95_mg_dl"]
            rec_id = fc_data.get("record_id")

            print(f"      Model Version: {fc_data.get('model_version')}")
            print(f"      Current Glucose: {fc_data['current_state']['glucose_mg_dl']} mg/dL (IOB: {fc_data['current_state']['iob_units']} U, COB: {fc_data['current_state']['cob_grams']} g)")
            print(f"      Point Forecast (20 steps): {point_forecast}")
            print(f"      Lower 95% Interval: {low95}")
            print(f"      Upper 95% Interval: {upp95}")
            print(f"      Risk Assessment: {fc_data['risk_assessment']['primary_status']} (Alert Level: {fc_data['risk_assessment']['alert_level']})")
            print(f"      Explanation Headline: {fc_data['explanation']['headline']}")
            print(f"      Stored Database Record ID: {rec_id}")

            assert len(point_forecast) == 20, "Point forecast must have 20 steps"
            assert len(low80) == 20 and len(upp80) == 20, "80% intervals must have 20 steps"
            assert len(low95) == 20 and len(upp95) == 20, "95% intervals must have 20 steps"
            assert rec_id is not None, "ForecastRecord must be saved to database"

            # Check database row directly
            stored = db.query(ForecastRecord).filter(ForecastRecord.id == rec_id).first()
            assert stored is not None, "Persisted ForecastRecord row must exist in database"
            assert stored.patient_id == demo_patient.id, "ForecastRecord must link to demo_patient"
            print(f"      Database Verification: Confirmed ForecastRecord row {stored.id} exists for patient {stored.patient_id}")

        print("=" * 70)
        print("DEMO PATIENT SEEDING COMPLETE AND VERIFIED!")
        print("=" * 70)

    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_patient()
