"""
GlucoShield Patient Profile & Longitudinal Persistence Router
=============================================================
Endpoints for managing patient profiles, CGM history, meal logs, insulin events,
forecast records, what-if simulations, decision history, and wearable telemetry.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from db.session import get_db
from db.models import (
    User,
    PatientProfile,
    CGMReading,
    MealRecord,
    InsulinRecord,
    ForecastRecord,
    WhatIfRecord,
    DecisionRecord,
    WearableObservation
)
from api.schemas import (
    PatientCreate,
    PatientUpdate,
    PatientResponse,
    CGMPointCreate,
    CGMBatchCreate,
    CGMPointResponse,
    MealCreate,
    MealResponse,
    InsulinCreate,
    InsulinResponse,
    WearableCreate,
    WearableResponse,
    ForecastRecordResponse,
    WhatIfRecordResponse,
    DecisionRecordResponse
)
from api.deps import get_current_user, verify_patient_ownership

router = APIRouter(prefix="/api/v1/patients", tags=["Patient Profiles & Longitudinal Data"])

# ==============================================================================
# Patient Profile Management
# ==============================================================================

@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def create_patient_profile(
    payload: PatientCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Creates a new patient profile associated with the authenticated user."""
    patient = PatientProfile(
        user_id=current_user.id,
        patient_display_id=payload.patient_display_id or f"PATIENT-{current_user.id[:8].upper()}",
        age=payload.age,
        bmi=payload.bmi,
        diabetes_duration_years=payload.diabetes_duration_years,
        hba1c=payload.hba1c,
        glycated_albumin=payload.glycated_albumin,
        fasting_glucose=payload.fasting_glucose,
        fasting_c_peptide=payload.fasting_c_peptide,
        macrovascular_comp_count=payload.macrovascular_comp_count,
        microvascular_comp_count=payload.microvascular_comp_count,
        is_t1dm=payload.is_t1dm
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return PatientResponse.model_validate(patient)

@router.get("", response_model=List[PatientResponse])
def list_user_patient_profiles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists all patient profiles owned by the current authenticated user."""
    patients = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).all()
    if not patients:
        default_patient = PatientProfile(
            user_id=current_user.id,
            patient_display_id=f"PATIENT-{current_user.id[:8].upper()}"
        )
        db.add(default_patient)
        db.commit()
        db.refresh(default_patient)
        patients = [default_patient]
    return [PatientResponse.model_validate(p) for p in patients]

@router.get("/me", response_model=PatientResponse)
def get_my_patient_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves the default patient profile associated with the current user."""
    patient = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
    if not patient:
        # Create default profile if not present
        patient = PatientProfile(
            user_id=current_user.id,
            patient_display_id=f"PATIENT-{current_user.id[:8].upper()}"
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
    return PatientResponse.model_validate(patient)

@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient_profile(
    patient: PatientProfile = Depends(verify_patient_ownership)
):
    """Retrieves a specific patient profile (protected by ownership authorization)."""
    return PatientResponse.model_validate(patient)

@router.put("/{patient_id}", response_model=PatientResponse)
def update_patient_profile(
    payload: PatientUpdate,
    patient: PatientProfile = Depends(verify_patient_ownership),
    db: Session = Depends(get_db)
):
    """Updates clinical static parameters for a patient profile."""
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(patient, field, value)
    
    db.commit()
    db.refresh(patient)
    return PatientResponse.model_validate(patient)

# ==============================================================================
# CGM Time Series Persistence
# ==============================================================================

@router.post("/{patient_id}/cgm", response_model=List[CGMPointResponse], status_code=status.HTTP_201_CREATED)
def ingest_cgm_batch(
    payload: CGMBatchCreate,
    patient: PatientProfile = Depends(verify_patient_ownership),
    db: Session = Depends(get_db)
):
    """Ingests a batch of continuous glucose monitoring readings."""
    created_readings = []
    for r in payload.readings:
        reading = CGMReading(
            patient_id=patient.id,
            timestamp=r.timestamp,
            cgm_glucose=r.cgm_glucose,
            insulin_bolus=r.insulin_bolus,
            insulin_basal=r.insulin_basal,
            meal_carbs=r.meal_carbs
        )
        db.add(reading)
        created_readings.append(reading)
    
    db.commit()
    for cr in created_readings:
        db.refresh(cr)
    return [CGMPointResponse.model_validate(r) for r in created_readings]

@router.get("/{patient_id}/cgm", response_model=List[CGMPointResponse])
def get_cgm_history(
    patient: PatientProfile = Depends(verify_patient_ownership),
    limit: int = Query(96, ge=1, le=1000),
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """Retrieves historical CGM readings for the patient."""
    q = db.query(CGMReading).filter(CGMReading.patient_id == patient.id)
    if start_time:
        q = q.filter(CGMReading.timestamp >= start_time)
    if end_time:
        q = q.filter(CGMReading.timestamp <= end_time)
    
    readings = q.order_by(desc(CGMReading.timestamp)).limit(limit).all()
    readings.reverse() # Return chronological order
    return [CGMPointResponse.model_validate(r) for r in readings]

# ==============================================================================
# Meal Records Persistence
# ==============================================================================

@router.post("/{patient_id}/meals", response_model=MealResponse, status_code=status.HTTP_201_CREATED)
def log_meal(
    payload: MealCreate,
    patient: PatientProfile = Depends(verify_patient_ownership),
    db: Session = Depends(get_db)
):
    """Logs a meal with validated or estimated macronutrients."""
    meal = MealRecord(
        patient_id=patient.id,
        timestamp=payload.timestamp or datetime.utcnow(),
        meal_name=payload.meal_name,
        portion_g=payload.portion_g,
        carbs_g=payload.carbs_g,
        calories_kcal=payload.calories_kcal,
        protein_g=payload.protein_g,
        fat_g=payload.fat_g,
        user_confirmed=payload.user_confirmed,
        source=payload.source
    )
    db.add(meal)
    db.commit()
    db.refresh(meal)
    return MealResponse.model_validate(meal)

@router.get("/{patient_id}/meals", response_model=List[MealResponse])
def get_meal_history(
    patient: PatientProfile = Depends(verify_patient_ownership),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Retrieves meal history for the patient."""
    meals = db.query(MealRecord).filter(
        MealRecord.patient_id == patient.id
    ).order_by(desc(MealRecord.timestamp)).limit(limit).all()
    return [MealResponse.model_validate(m) for m in meals]

# ==============================================================================
# Insulin Records Persistence
# ==============================================================================

@router.post("/{patient_id}/insulin", response_model=InsulinResponse, status_code=status.HTTP_201_CREATED)
def log_insulin(
    payload: InsulinCreate,
    patient: PatientProfile = Depends(verify_patient_ownership),
    db: Session = Depends(get_db)
):
    """Logs an exogenous insulin administration event."""
    insulin = InsulinRecord(
        patient_id=patient.id,
        timestamp=payload.timestamp or datetime.utcnow(),
        dose_type=payload.dose_type,
        units=payload.units,
        insulin_type=payload.insulin_type,
        notes=payload.notes
    )
    db.add(insulin)
    db.commit()
    db.refresh(insulin)
    return InsulinResponse.model_validate(insulin)

@router.get("/{patient_id}/insulin", response_model=List[InsulinResponse])
def get_insulin_history(
    patient: PatientProfile = Depends(verify_patient_ownership),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Retrieves insulin dosing history for the patient."""
    records = db.query(InsulinRecord).filter(
        InsulinRecord.patient_id == patient.id
    ).order_by(desc(InsulinRecord.timestamp)).limit(limit).all()
    return [InsulinResponse.model_validate(r) for r in records]

# ==============================================================================
# Forecast, What-If, Decision & Wearable History Queries
# ==============================================================================

@router.get("/{patient_id}/forecasts", response_model=List[ForecastRecordResponse])
def get_forecast_history(
    patient: PatientProfile = Depends(verify_patient_ownership),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Retrieves historical 5-hour forecasts for the patient."""
    records = db.query(ForecastRecord).filter(
        ForecastRecord.patient_id == patient.id
    ).order_by(desc(ForecastRecord.timestamp)).limit(limit).all()
    return [ForecastRecordResponse.model_validate(r) for r in records]

@router.get("/{patient_id}/what-if", response_model=List[WhatIfRecordResponse])
def get_what_if_history(
    patient: PatientProfile = Depends(verify_patient_ownership),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Retrieves historical What-If ODE simulation records."""
    records = db.query(WhatIfRecord).filter(
        WhatIfRecord.patient_id == patient.id
    ).order_by(desc(WhatIfRecord.timestamp)).limit(limit).all()
    return [WhatIfRecordResponse.model_validate(r) for r in records]

@router.get("/{patient_id}/decisions", response_model=List[DecisionRecordResponse])
def get_decision_history(
    patient: PatientProfile = Depends(verify_patient_ownership),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Retrieves historical synthesized multimodal decision reports."""
    records = db.query(DecisionRecord).filter(
        DecisionRecord.patient_id == patient.id
    ).order_by(desc(DecisionRecord.timestamp)).limit(limit).all()
    return [DecisionRecordResponse.model_validate(r) for r in records]

@router.post("/{patient_id}/wearables", response_model=WearableResponse, status_code=status.HTTP_201_CREATED)
def log_wearable_telemetry(
    payload: WearableCreate,
    patient: PatientProfile = Depends(verify_patient_ownership),
    db: Session = Depends(get_db)
):
    """Logs observational smartwatch telemetry (strictly isolated from V1 forecaster)."""
    obs = WearableObservation(
        patient_id=patient.id,
        timestamp=payload.timestamp or datetime.utcnow(),
        step_count=payload.step_count,
        heart_rate_bpm=payload.heart_rate_bpm,
        accel_magnitude_g=payload.accel_magnitude_g,
        device_source=payload.device_source
    )
    db.add(obs)
    db.commit()
    db.refresh(obs)
    return WearableResponse.model_validate(obs)

@router.get("/{patient_id}/wearables", response_model=List[WearableResponse])
def get_wearable_history(
    patient: PatientProfile = Depends(verify_patient_ownership),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Retrieves observational smartwatch telemetry history."""
    obs = db.query(WearableObservation).filter(
        WearableObservation.patient_id == patient.id
    ).order_by(desc(WearableObservation.timestamp)).limit(limit).all()
    return [WearableResponse.model_validate(o) for o in obs]
