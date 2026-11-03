"""
GlucoShield Mobile & Device Integration Router (Phase 17)
=========================================================
Secure REST endpoints for device batch synchronization, manual mobile events,
device connection lifecycle, and causal context diagnostics.
"""

from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from db.session import get_db
from db.models import (
    User,
    PatientProfile,
    DeviceConnection,
    DeviceRecord
)
from api.deps import get_current_user, verify_patient_ownership
from api.devices.schemas import (
    DeviceSyncRequest,
    DeviceSyncResponse,
    ManualEventCreate,
    DeviceRegisterRequest,
    DeviceConnectionResponse,
    CausalContextResponse,
    MeasurementType,
    DeviceProvider,
    DeviceObservationIn,
    QualityStatus
)
from api.devices.ingestion import DeviceIngestionService
from api.devices.causality import CausalDeviceContextBuilder

router = APIRouter(prefix="/api/v1/devices", tags=["Mobile & Device Integration"])
ingestion_service = DeviceIngestionService()
context_builder = CausalDeviceContextBuilder()


def _get_user_patient(current_user: User, db: Session) -> PatientProfile:
    """Helper to retrieve the primary patient profile of the authenticated user."""
    patient = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
    if not patient:
        # Create default patient profile for user if none exists
        patient = PatientProfile(
            user_id=current_user.id,
            patient_display_id=f"PATIENT-{current_user.id[:8].upper()}"
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
    return patient


# ==============================================================================
# 1. Device Synchronization & Ingestion
# ==============================================================================

@router.post("/sync", response_model=DeviceSyncResponse, status_code=status.HTTP_200_OK)
def sync_device_data(
    payload: DeviceSyncRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ingests batch of device observations (CGM, heart rate, steps, sleep, meal, insulin).
    Applies timezone normalization, physiological range validation, and
    deterministic deduplication.
    """
    patient = _get_user_patient(current_user, db)
    return ingestion_service.sync_device_observations(db, patient, payload)


@router.post("/events/manual", response_model=DeviceSyncResponse, status_code=status.HTTP_201_CREATED)
def log_manual_mobile_event(
    payload: ManualEventCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Logs a human-entered mobile event (meal, insulin, symptom, exercise)
    with explicit confirmation status and provenance.
    """
    patient = _get_user_patient(current_user, db)

    m_type_map = {
        "meal": MeasurementType.MEAL_CARBS,
        "carbs": MeasurementType.MEAL_CARBS,
        "insulin": MeasurementType.INSULIN_DOSE,
        "exercise": MeasurementType.ACTIVE_MINUTES,
        "stress": MeasurementType.CONTEXT_EVENT,
        "symptom": MeasurementType.CONTEXT_EVENT
    }

    m_type = m_type_map.get(payload.event_type.lower(), MeasurementType.CONTEXT_EVENT)

    observation = DeviceObservationIn(
        measurement_type=m_type,
        value=payload.value,
        unit=payload.unit,
        observation_timestamp=payload.timestamp,
        source_timezone=payload.source_timezone or "UTC",
        quality_status=QualityStatus.VALID,
        metadata={"user_confirmed": payload.user_confirmed, "notes": payload.notes}
    )

    sync_req = DeviceSyncRequest(
        device_id="mobile_app_manual",
        provider=DeviceProvider.MANUAL_MOBILE,
        device_name="GlucoShield Mobile App",
        observations=[observation]
    )

    return ingestion_service.sync_device_observations(db, patient, sync_req)


# ==============================================================================
# 2. Device Connection Management & Health Observability
# ==============================================================================

@router.get("", response_model=List[DeviceConnectionResponse])
def list_connected_devices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists all paired hardware devices and mobile integrations for the authenticated user."""
    patient = _get_user_patient(current_user, db)
    connections = db.query(DeviceConnection).filter(
        DeviceConnection.patient_id == patient.id
    ).order_by(desc(DeviceConnection.last_sync_at)).all()

    now_utc = datetime.utcnow()
    results = []
    for c in connections:
        freshness = None
        if c.last_observation_at:
            freshness = max(0.0, (now_utc - c.last_observation_at).total_seconds())

        resp = DeviceConnectionResponse.model_validate(c)
        resp.data_freshness_seconds = freshness
        results.append(resp)
    return results


@router.post("/register", response_model=DeviceConnectionResponse, status_code=status.HTTP_201_CREATED)
def register_device(
    payload: DeviceRegisterRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Pairs a new mobile or wearable device for the authenticated patient."""
    patient = _get_user_patient(current_user, db)

    conn = db.query(DeviceConnection).filter(
        DeviceConnection.patient_id == patient.id,
        DeviceConnection.device_id == payload.device_id
    ).first()

    now_utc = datetime.utcnow()
    if conn:
        conn.connection_status = "connected"
        conn.provider = payload.provider.value
        conn.device_name = payload.device_name
    else:
        conn = DeviceConnection(
            patient_id=patient.id,
            device_id=payload.device_id,
            provider=payload.provider.value,
            device_name=payload.device_name,
            connection_status="connected",
            created_at=now_utc
        )
        db.add(conn)

    db.commit()
    db.refresh(conn)
    return DeviceConnectionResponse.model_validate(conn)


@router.post("/{device_id}/disconnect", response_model=DeviceConnectionResponse)
def disconnect_device(
    device_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disconnects an existing device connection."""
    patient = _get_user_patient(current_user, db)
    conn = db.query(DeviceConnection).filter(
        DeviceConnection.patient_id == patient.id,
        DeviceConnection.device_id == device_id
    ).first()

    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device '{device_id}' not found for this patient."
        )

    conn.connection_status = "disconnected"
    db.commit()
    db.refresh(conn)
    return DeviceConnectionResponse.model_validate(conn)


@router.get("/{device_id}/status", response_model=DeviceConnectionResponse)
def get_device_status(
    device_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves operational telemetry, duplicate count, and data freshness for a device."""
    patient = _get_user_patient(current_user, db)
    conn = db.query(DeviceConnection).filter(
        DeviceConnection.patient_id == patient.id,
        DeviceConnection.device_id == device_id
    ).first()

    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device '{device_id}' not found for this patient."
        )

    freshness = None
    if conn.last_observation_at:
        freshness = max(0.0, (datetime.utcnow() - conn.last_observation_at).total_seconds())

    resp = DeviceConnectionResponse.model_validate(conn)
    resp.data_freshness_seconds = freshness
    return resp


# ==============================================================================
# 3. Causal Context Verification Endpoint
# ==============================================================================

@router.get("/causal-context", response_model=CausalContextResponse)
def get_causal_context(
    forecast_origin: Optional[str] = Query(None, description="ISO timestamp of forecast origin. Defaults to current time."),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Demonstrates temporal causality: returns only patient observations
    occurring on or before the specified forecast_origin.
    Guarantees future observations are strictly excluded.
    """
    patient = _get_user_patient(current_user, db)

    if forecast_origin:
        try:
            origin_dt = datetime.fromisoformat(forecast_origin.replace("Z", "+00:00"))
            origin_utc, _ = DeviceIngestionService.normalize_timestamp(origin_dt)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid ISO timestamp: '{forecast_origin}'"
            )
    else:
        origin_utc = datetime.utcnow()

    return context_builder.build_causal_context(db, patient.id, origin_utc)
