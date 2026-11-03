"""
GlucoShield Device & Mobile Ingestion Schemas (Phase 17)
========================================================
Pydantic contracts for incoming device telemetry, mobile event logging,
deterministic sync responses, and device connection management.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class MeasurementType(str, Enum):
    GLUCOSE = "glucose"
    HEART_RATE = "heart_rate"
    STEPS = "steps"
    ACTIVE_MINUTES = "active_minutes"
    SLEEP_SESSION = "sleep_session"
    MEAL_CARBS = "meal_carbs"
    INSULIN_DOSE = "insulin_dose"
    CONTEXT_EVENT = "context_event"


class DeviceProvider(str, Enum):
    DEXCOM = "dexcom"
    FREESTYLE_LIBRE = "freestyle_libre"
    APPLE_HEALTH = "apple_health"
    GOOGLE_HEALTH_CONNECT = "google_health_connect"
    GARMIN = "garmin"
    FITBIT = "fitbit"
    MANUAL_MOBILE = "manual_mobile"
    CUSTOM = "custom"


class QualityStatus(str, Enum):
    VALID = "VALID"
    MISSING = "MISSING"
    DUPLICATE = "DUPLICATE"
    DELAYED = "DELAYED"
    INVALID = "INVALID"
    LOW_QUALITY = "LOW_QUALITY"


class ConnectionStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    REVOKED = "revoked"
    ERROR = "error"
    SYNCHRONIZING = "synchronizing"


class DeviceObservationIn(BaseModel):
    """A single raw measurement from a mobile or wearable device."""
    measurement_type: MeasurementType
    value: Optional[float] = Field(None, description="Numeric measurement value (None if sensor missing/error)")
    unit: str = Field(..., description="Measurement unit (e.g. mg/dL, mmol/L, bpm, count, minutes, grams, units)")
    observation_timestamp: datetime = Field(..., description="Timestamp when the event physically occurred")
    source_timezone: Optional[str] = Field("UTC", description="Source timezone identifier or offset e.g. '+05:30' or 'Asia/Kolkata'")
    quality_status: Optional[QualityStatus] = Field(QualityStatus.VALID, description="Device-reported quality flag")
    raw_source_id: Optional[str] = Field(None, description="Vendor record ID if available from the source SDK/API")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Auxiliary provenance metadata (e.g. sensor state, sleep stages)")


class DeviceSyncRequest(BaseModel):
    """Batch upload payload from mobile client or device companion app."""
    device_id: str = Field(..., description="Hardware or application instance identifier")
    provider: DeviceProvider = Field(..., description="Device provider or integration type")
    device_name: Optional[str] = Field("Generic Device", description="Human-readable device model")
    observations: List[DeviceObservationIn] = Field(..., max_length=1000, description="Batch of observations (max 1000)")
    sync_cursor: Optional[str] = Field(None, description="Optional continuation cursor from previous sync")


class DeviceSyncResponse(BaseModel):
    """Structured response detailing ingestion outcomes, deduplication, and errors."""
    sync_id: str
    device_id: str
    status: str = Field(..., description="'SUCCESS', 'PARTIAL_SUCCESS', or 'FAILED'")
    records_received: int
    records_accepted: int
    duplicates_ignored: int
    records_rejected: int
    errors: List[str] = Field(default_factory=list)
    data_freshness_seconds: Optional[float] = Field(None, description="Latency between latest observation and ingestion")
    new_cursor: Optional[str] = None


class ManualEventCreate(BaseModel):
    """Manual mobile event entry (meal, insulin, symptom, exercise)."""
    event_type: str = Field(..., description="'meal', 'insulin', 'exercise', 'stress', 'symptom'")
    timestamp: datetime = Field(..., description="Time of event occurrence")
    value: float = Field(..., description="Numeric value: grams for meal, units for insulin, minutes for exercise")
    unit: str = Field(..., description="'grams', 'units', 'minutes', 'rating'")
    source_timezone: Optional[str] = Field("UTC", description="Local timezone string")
    notes: Optional[str] = Field(None, max_length=255, description="Optional user note")
    user_confirmed: bool = Field(True, description="Human confirmation status")


class DeviceRegisterRequest(BaseModel):
    """Register or pair a new device for the authenticated patient."""
    device_id: str = Field(..., max_length=128)
    provider: DeviceProvider
    device_name: str = Field(..., max_length=128)


class DeviceConnectionResponse(BaseModel):
    """Observability status of a registered device."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    device_id: str
    provider: str
    device_name: str
    connection_status: str
    last_sync_at: Optional[datetime] = None
    last_observation_at: Optional[datetime] = None
    records_synced_total: int = 0
    duplicate_count: int = 0
    error_count: int = 0
    data_freshness_seconds: Optional[float] = None
    created_at: datetime


class CausalContextResponse(BaseModel):
    """Causal context summary generated at a specific forecast origin timestamp."""
    patient_id: str
    forecast_origin: datetime
    cgm_count_causal: int
    wearable_count_causal: int
    latest_cgm_glucose: Optional[float] = None
    mean_heart_rate_bpm: Optional[float] = None
    total_steps_window: Optional[float] = None
    active_minutes_window: Optional[float] = None
    sleep_efficiency_pct: Optional[float] = None
    future_observations_excluded_count: int = 0
    causal_boundary_verified: bool = True
