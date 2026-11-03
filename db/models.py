"""
GlucoShield Normalized Relational Data Models
=============================================
SQLAlchemy 2.0 ORM models for Users, Patients, Longitudinal CGM, Insulin, Meals,
Food Vision, Forecasts, What-If simulations, Decisions, and Wearable observations.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    String,
    Float,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Index,
    Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.base import Base, TimestampMixin, generate_uuid

class User(Base, TimestampMixin):
    """
    Authenticated User Account (Clinician, Patient, or Researcher).
    """
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    patients: Mapped[List["PatientProfile"]] = relationship(
        "PatientProfile",
        back_populates="user",
        cascade="all, delete-orphan"
    )

class PatientProfile(Base, TimestampMixin):
    """
    Patient Phenotypic Profile (9 static clinical features).
    """
    __tablename__ = "patient_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=True
    )
    patient_display_id: Mapped[str] = mapped_column(String(64), index=True, default="patient_001")
    
    # 9 Static clinical features for GlucoShield V1
    age: Mapped[float] = mapped_column(Float, default=45.0, nullable=False)
    bmi: Mapped[float] = mapped_column(Float, default=26.5, nullable=False)
    diabetes_duration_years: Mapped[float] = mapped_column(Float, default=10.0, nullable=False)
    hba1c: Mapped[float] = mapped_column(Float, default=58.0, nullable=False)
    glycated_albumin: Mapped[float] = mapped_column(Float, default=18.0, nullable=False)
    fasting_glucose: Mapped[float] = mapped_column(Float, default=130.0, nullable=False)
    fasting_c_peptide: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    macrovascular_comp_count: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    microvascular_comp_count: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_t1dm: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="patients")
    cgm_readings: Mapped[List["CGMReading"]] = relationship(
        "CGMReading",
        back_populates="patient",
        cascade="all, delete-orphan",
        order_by="CGMReading.timestamp"
    )
    insulin_records: Mapped[List["InsulinRecord"]] = relationship(
        "InsulinRecord",
        back_populates="patient",
        cascade="all, delete-orphan",
        order_by="InsulinRecord.timestamp"
    )
    meal_records: Mapped[List["MealRecord"]] = relationship(
        "MealRecord",
        back_populates="patient",
        cascade="all, delete-orphan",
        order_by="MealRecord.timestamp"
    )
    food_analyses: Mapped[List["FoodAnalysisRecord"]] = relationship(
        "FoodAnalysisRecord",
        back_populates="patient",
        cascade="all, delete-orphan",
        order_by="FoodAnalysisRecord.created_at"
    )
    forecasts: Mapped[List["ForecastRecord"]] = relationship(
        "ForecastRecord",
        back_populates="patient",
        cascade="all, delete-orphan",
        order_by="ForecastRecord.timestamp"
    )
    what_if_simulations: Mapped[List["WhatIfRecord"]] = relationship(
        "WhatIfRecord",
        back_populates="patient",
        cascade="all, delete-orphan",
        order_by="WhatIfRecord.timestamp"
    )
    decisions: Mapped[List["DecisionRecord"]] = relationship(
        "DecisionRecord",
        back_populates="patient",
        cascade="all, delete-orphan",
        order_by="DecisionRecord.timestamp"
    )
    wearable_observations: Mapped[List["WearableObservation"]] = relationship(
        "WearableObservation",
        back_populates="patient",
        cascade="all, delete-orphan",
        order_by="WearableObservation.timestamp"
    )
    device_connections: Mapped[List["DeviceConnection"]] = relationship(
        "DeviceConnection",
        back_populates="patient",
        cascade="all, delete-orphan",
        order_by="DeviceConnection.created_at"
    )
    device_records: Mapped[List["DeviceRecord"]] = relationship(
        "DeviceRecord",
        back_populates="patient",
        cascade="all, delete-orphan",
        order_by="DeviceRecord.observation_timestamp"
    )

class CGMReading(Base):
    """
    Continuous Glucose Monitoring 15-minute time series datapoint.
    """
    __tablename__ = "cgm_readings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    patient_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("patient_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)
    cgm_glucose: Mapped[float] = mapped_column(Float, nullable=False)  # mg/dL
    insulin_bolus: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    insulin_basal: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    meal_carbs: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    patient: Mapped["PatientProfile"] = relationship("PatientProfile", back_populates="cgm_readings")

    __table_args__ = (
        Index("idx_cgm_patient_time", "patient_id", "timestamp"),
    )

class InsulinRecord(Base):
    """
    Detailed exogenous insulin administration event.
    """
    __tablename__ = "insulin_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    patient_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("patient_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)
    dose_type: Mapped[str] = mapped_column(String(32), default="bolus", nullable=False) # 'bolus' or 'basal'
    units: Mapped[float] = mapped_column(Float, nullable=False)
    insulin_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True) # e.g. 'Aspart', 'Lispro', 'Glargine'
    notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    patient: Mapped["PatientProfile"] = relationship("PatientProfile", back_populates="insulin_records")

class MealRecord(Base):
    """
    Logged Meal with validated or manual macronutrients.
    """
    __tablename__ = "meal_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    patient_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("patient_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)
    meal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    portion_g: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    carbs_g: Mapped[float] = mapped_column(Float, nullable=False)
    calories_kcal: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    protein_g: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fat_g: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    user_confirmed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source: Mapped[str] = mapped_column(String(64), default="manual", nullable=False) # 'manual', 'food_vision', 'usda'
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    patient: Mapped["PatientProfile"] = relationship("PatientProfile", back_populates="meal_records")

class FoodAnalysisRecord(Base):
    """
    Food Vision photograph / query analysis record.
    """
    __tablename__ = "food_analysis_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    patient_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("patient_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    food_name_query: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    selected_food: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    portion_g: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    candidates: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    nutrition_density: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    final_macros: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    requires_user_confirmation: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    warnings: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    image_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True) # file hash/path, not blob
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    patient: Mapped["PatientProfile"] = relationship("PatientProfile", back_populates="food_analyses")

class ForecastRecord(Base):
    """
    5-Hour Hybrid Multi-Horizon Glucose Forecast Result.
    """
    __tablename__ = "forecast_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    patient_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("patient_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=datetime.utcnow, nullable=False)
    current_glucose: Mapped[float] = mapped_column(Float, nullable=False)
    current_iob: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    current_cob: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    point_forecast: Mapped[List[float]] = mapped_column(JSON, nullable=False)
    lower_80: Mapped[List[float]] = mapped_column(JSON, nullable=False)
    upper_80: Mapped[List[float]] = mapped_column(JSON, nullable=False)
    lower_95: Mapped[List[float]] = mapped_column(JSON, nullable=False)
    upper_95: Mapped[List[float]] = mapped_column(JSON, nullable=False)
    hybrid_components: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    risk_assessment: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    explanation: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    patient: Mapped["PatientProfile"] = relationship("PatientProfile", back_populates="forecasts")

class WhatIfRecord(Base):
    """
    Counterfactual Postprandial ODE Simulation Result.
    """
    __tablename__ = "what_if_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    patient_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("patient_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=datetime.utcnow, nullable=False)
    scenario_name: Mapped[str] = mapped_column(String(128), default="Custom Scenario", nullable=False)
    scenario_meal_carbs_g: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    scenario_insulin_bolus_u: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    simulated_trajectory: Mapped[List[float]] = mapped_column(JSON, nullable=False)
    nadir_glucose: Mapped[float] = mapped_column(Float, nullable=False)
    time_to_nadir_min: Mapped[int] = mapped_column(Integer, nullable=False)
    peak_glucose: Mapped[float] = mapped_column(Float, nullable=False)
    time_to_peak_min: Mapped[int] = mapped_column(Integer, nullable=False)
    time_in_range_pct: Mapped[float] = mapped_column(Float, nullable=False)
    warnings: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    patient: Mapped["PatientProfile"] = relationship("PatientProfile", back_populates="what_if_simulations")

class DecisionRecord(Base):
    """
    Synthesized Multimodal Decision Report.
    """
    __tablename__ = "decision_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    patient_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("patient_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=datetime.utcnow, nullable=False)
    food_analysis_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("food_analysis_records.id", ondelete="SET NULL"), nullable=True)
    forecast_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("forecast_records.id", ondelete="SET NULL"), nullable=True)
    what_if_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("what_if_records.id", ondelete="SET NULL"), nullable=True)
    alert_status: Mapped[str] = mapped_column(String(32), default="NORMAL", nullable=False)
    recommended_action: Mapped[str] = mapped_column(String(255), nullable=False)
    decision_summary: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    patient: Mapped["PatientProfile"] = relationship("PatientProfile", back_populates="decisions")

class WearableObservation(Base):
    """
    Smartwatch activity/heart rate telemetry (strictly isolated from 22-channel forecaster).
    """
    __tablename__ = "wearable_observations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    patient_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("patient_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=datetime.utcnow, nullable=False)
    step_count: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    heart_rate_bpm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    accel_magnitude_g: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    device_source: Mapped[Optional[str]] = mapped_column(String(128), default="smartwatch", nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    patient: Mapped["PatientProfile"] = relationship("PatientProfile", back_populates="wearable_observations")


class DeviceConnection(Base):
    """
    Connected mobile or wearable hardware device instance.
    Tracks sync state, consent, freshness, and error diagnostics.
    """
    __tablename__ = "device_connections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    patient_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("patient_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    device_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)  # 'dexcom', 'freestyle_libre', 'apple_health', etc.
    device_name: Mapped[str] = mapped_column(String(128), nullable=False)
    connection_status: Mapped[str] = mapped_column(String(32), default="connected", nullable=False)  # connected, disconnected, revoked, error, synchronizing
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_observation_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    records_synced_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    patient: Mapped["PatientProfile"] = relationship("PatientProfile", back_populates="device_connections")

    __table_args__ = (
        Index("idx_device_patient_id", "patient_id", "device_id", unique=True),
    )


class DeviceRecord(Base):
    """
    Normalized, provider-independent mobile & wearable observation record.
    Preserves raw source provenance, source timezone, measurement quality,
    and deterministic deduplication hash.
    """
    __tablename__ = "device_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    patient_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("patient_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    device_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(64), index=True, nullable=False)  # SHA-256
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    measurement_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)  # glucose, heart_rate, steps, active_minutes, sleep_session, meal_carbs, insulin_dose
    value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    observation_timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)  # normalized UTC
    source_timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    ingestion_timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)  # arrival time
    quality_flag: Mapped[str] = mapped_column(String(32), default="VALID", nullable=False)  # VALID, MISSING, DUPLICATE, DELAYED, INVALID, LOW_QUALITY
    raw_source_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    patient: Mapped["PatientProfile"] = relationship("PatientProfile", back_populates="device_records")

    __table_args__ = (
        Index("idx_device_rec_patient_time", "patient_id", "observation_timestamp"),
        Index("idx_device_rec_idempotency", "patient_id", "idempotency_key", unique=True),
    )
