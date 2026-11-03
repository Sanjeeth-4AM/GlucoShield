"""
GlucoShield API Pydantic Data Schemas
=====================================
Strict Pydantic request and response contracts for all Phase 8, Phase 9, and Phase 10 REST endpoints.
"""

from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime

# ==============================================================================
# 1. System Health & Core Dynamic Preprocessor Schemas
# ==============================================================================

class HealthResponse(BaseModel):
    status: str = Field(..., example="healthy")
    version: str = Field(..., example="1.0.0")
    neural_forecaster_loaded: bool = True
    hybrid_forecaster_loaded: bool = True
    ode_digital_twin_ready: bool = True
    food_vision_ready: bool = True
    active_channels_contract: int = 22
    database_connected: bool = True
    research_disclaimer: str
    timestamp: str
    active_model_version: Optional[str] = "COMBINATION_C"
    available_models: Optional[List[str]] = Field(default_factory=lambda: ["COMBINATION_C", "V1_FROZEN", "V2_FROZEN", "PHASE13_VALIDATED"])
    artifact_integrity: Optional[str] = "VERIFIED"

class TimeStepReading(BaseModel):
    timestamp: Optional[str] = Field(None, example="2026-08-28T12:00:00")
    cgm_glucose: float = Field(..., ge=20.0, le=600.0, example=125.0, description="CGM glucose in mg/dL")
    insulin_bolus: float = Field(0.0, ge=0.0, le=50.0, example=0.0, description="Bolus insulin units")
    insulin_basal: float = Field(0.0, ge=0.0, le=20.0, example=0.5, description="Basal insulin units")
    meal_carbs: float = Field(0.0, ge=0.0, le=300.0, example=0.0, description="Carbohydrate intake grams")

class PatientStaticProfile(BaseModel):
    age: float = Field(45.0, ge=1.0, le=120.0, example=45.0)
    bmi: float = Field(26.5, ge=10.0, le=70.0, example=26.5)
    diabetes_duration_years: float = Field(
        10.0, ge=0.0, le=80.0, example=10.0,
        description="Patient clinical profile metadata. Note: Retained for longitudinal records but excluded from the 9-channel acute forecasting vector (age, bmi, hba1c, glycated_albumin, fasting_glucose, fasting_c_peptide, macrovascular_comp_count, microvascular_comp_count, is_t1dm) per Phase 1-17 frozen contract."
    )
    hba1c: float = Field(58.0, ge=20.0, le=150.0, example=58.0)
    glycated_albumin: float = Field(18.0, ge=5.0, le=50.0, example=18.0)
    fasting_glucose: float = Field(130.0, ge=40.0, le=400.0, example=130.0)
    fasting_c_peptide: float = Field(0.8, ge=0.0, le=10.0, example=0.8)
    macrovascular_comp_count: float = Field(0.0, ge=0.0, le=10.0, example=0.0)
    microvascular_comp_count: float = Field(0.0, ge=0.0, le=10.0, example=0.0)
    is_t1dm: float = Field(1.0, ge=0.0, le=1.0, example=1.0)

class OptionalWearableContext(BaseModel):
    steps_15m: Optional[List[float]] = Field(None, description="Optional steps in past 15-min intervals")
    heart_rate_bpm: Optional[List[float]] = Field(None, description="Optional heart rate readings")
    accel_magnitude_g: Optional[List[float]] = Field(None, description="Optional acceleration magnitude")
    device_source: Optional[str] = Field("smartwatch", example="TicWatch Pro / Apple Watch")
    disclaimer: str = "Wearable activity telemetry is stored for observational context and is not merged into the frozen V1 22-channel dynamic forecaster tensor per Phase 7C empirical findings."

# ==============================================================================
# 2. Existing Scientific Inference Endpoints
# ==============================================================================

class ForecastRequest(BaseModel):
    patient_id: str = Field("demo_patient_001", example="patient_101")
    history_readings: List[TimeStepReading] = Field(..., min_length=96, max_length=96, description="Exactly 96 readings (24 hours at 15m intervals)")
    static_profile: Optional[PatientStaticProfile] = Field(default_factory=PatientStaticProfile)
    wearable_context: Optional[OptionalWearableContext] = None
    requested_model_version: Optional[str] = Field(None, example="COMBINATION_C", description="Optional explicit model version: COMBINATION_C (production default), V1_FROZEN (legacy baseline), V2_FROZEN, or PHASE13_VALIDATED.")

class ForecastResponse(BaseModel):
    disclaimer: str
    patient_id: str
    current_state: Dict[str, Any]
    forecast: Dict[str, Any]
    hybrid_components: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    explanation: Dict[str, Any]
    wearable_context_logged: bool = False
    record_id: Optional[str] = None
    model_version: Optional[str] = "COMBINATION_C"
    traceability: Optional[Dict[str, Any]] = None
    telemetry: Optional[Dict[str, Any]] = None

class WhatIfRequest(BaseModel):
    patient_id: str = Field("demo_patient_001", example="patient_101")
    history_readings: List[TimeStepReading] = Field(..., min_length=96, max_length=96)
    static_profile: Optional[PatientStaticProfile] = Field(default_factory=PatientStaticProfile)
    scenario_meal_carbs_g: float = Field(0.0, ge=0.0, le=300.0, example=50.0)
    scenario_insulin_bolus_u: float = Field(0.0, ge=0.0, le=50.0, example=4.0)

class WhatIfResponse(BaseModel):
    disclaimer: str
    scenario_name: str
    simulated_trajectory: List[float]
    nadir_glucose: float
    time_to_nadir_min: int
    peak_glucose: float
    time_to_peak_min: int
    time_in_range_pct: float
    warnings: List[str]
    record_id: Optional[str] = None

class FoodAnalyzeRequest(BaseModel):
    image_base64: Optional[str] = Field(None, description="Base64 encoded JPEG/PNG photograph of meal")
    food_name_query: Optional[str] = Field(None, example="spaghetti bolognese", description="Optional text query if no image provided")
    portion_g: float = Field(100.0, ge=1.0, le=2000.0, example=250.0)
    selected_candidate_index: int = Field(0, ge=0, le=10)

class FoodAnalyzeResponse(BaseModel):
    image_food_candidates: List[Dict[str, Any]]
    selected_food: Optional[str]
    portion_g: float
    nutrition_density: Optional[Dict[str, Any]]
    final_macros: Dict[str, Any]
    requires_user_confirmation: bool
    warnings: List[str]
    record_id: Optional[str] = None

class FullFlowDecisionRequest(BaseModel):
    patient_id: str = Field("demo_patient_001", example="patient_101")
    history_readings: List[TimeStepReading] = Field(..., min_length=96, max_length=96)
    static_profile: Optional[PatientStaticProfile] = Field(default_factory=PatientStaticProfile)
    meal_image_base64: Optional[str] = Field(None, description="Optional meal photograph")
    meal_food_query: Optional[str] = Field(None, description="Optional text meal name")
    meal_portion_g: float = Field(100.0, ge=1.0, le=2000.0)
    proposed_insulin_bolus_u: Optional[float] = Field(None, ge=0.0, le=50.0)
    wearable_context: Optional[OptionalWearableContext] = None

class FullFlowDecisionResponse(BaseModel):
    disclaimer: str
    patient_id: str
    food_analysis: Optional[FoodAnalyzeResponse] = None
    baseline_forecast: ForecastResponse
    what_if_simulation: Optional[WhatIfResponse] = None
    decision_summary: Dict[str, Any]
    decision_record_id: Optional[str] = None

# ==============================================================================
# 3. Phase 10 Authentication & User Account Schemas
# ==============================================================================

class UserRegister(BaseModel):
    email: EmailStr = Field(..., example="clinician@hospital.org")
    password: str = Field(..., min_length=8, example="SecurePassword123!")
    full_name: Optional[str] = Field(None, example="Dr. Jane Doe")

class UserLogin(BaseModel):
    email: EmailStr = Field(..., example="clinician@hospital.org")
    password: str = Field(..., example="SecurePassword123!")

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    is_active: bool
    is_superuser: bool
    created_at: datetime

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    user: UserResponse

# ==============================================================================
# 4. Phase 10 Patient Profile & Longitudinal Persistence Schemas
# ==============================================================================

class PatientCreate(BaseModel):
    patient_display_id: Optional[str] = Field("patient_001", example="PATIENT-4092")
    age: float = Field(45.0, ge=1.0, le=120.0)
    bmi: float = Field(26.5, ge=10.0, le=70.0)
    diabetes_duration_years: float = Field(10.0, ge=0.0, le=80.0)
    hba1c: float = Field(58.0, ge=20.0, le=150.0)
    glycated_albumin: float = Field(18.0, ge=5.0, le=50.0)
    fasting_glucose: float = Field(130.0, ge=40.0, le=400.0)
    fasting_c_peptide: float = Field(0.8, ge=0.0, le=10.0)
    macrovascular_comp_count: float = Field(0.0, ge=0.0, le=10.0)
    microvascular_comp_count: float = Field(0.0, ge=0.0, le=10.0)
    is_t1dm: float = Field(1.0, ge=0.0, le=1.0)

class PatientUpdate(BaseModel):
    patient_display_id: Optional[str] = None
    age: Optional[float] = Field(None, ge=1.0, le=120.0)
    bmi: Optional[float] = Field(None, ge=10.0, le=70.0)
    diabetes_duration_years: Optional[float] = Field(None, ge=0.0, le=80.0)
    hba1c: Optional[float] = Field(None, ge=20.0, le=150.0)
    glycated_albumin: Optional[float] = Field(None, ge=5.0, le=50.0)
    fasting_glucose: Optional[float] = Field(None, ge=40.0, le=400.0)
    fasting_c_peptide: Optional[float] = Field(None, ge=0.0, le=10.0)
    macrovascular_comp_count: Optional[float] = Field(None, ge=0.0, le=10.0)
    microvascular_comp_count: Optional[float] = Field(None, ge=0.0, le=10.0)
    is_t1dm: Optional[float] = Field(None, ge=0.0, le=1.0)

class PatientResponse(BaseModel):
    id: str
    user_id: Optional[str]
    patient_display_id: str
    age: float
    bmi: float
    diabetes_duration_years: float
    hba1c: float
    glycated_albumin: float
    fasting_glucose: float
    fasting_c_peptide: float
    macrovascular_comp_count: float
    microvascular_comp_count: float
    is_t1dm: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# CGM Ingestion & Querying
class CGMPointCreate(BaseModel):
    timestamp: datetime
    cgm_glucose: float = Field(..., ge=20.0, le=600.0)
    insulin_bolus: float = Field(0.0, ge=0.0, le=50.0)
    insulin_basal: float = Field(0.0, ge=0.0, le=20.0)
    meal_carbs: float = Field(0.0, ge=0.0, le=300.0)

class CGMBatchCreate(BaseModel):
    readings: List[CGMPointCreate]

class CGMPointResponse(BaseModel):
    id: str
    patient_id: str
    timestamp: datetime
    cgm_glucose: float
    insulin_bolus: float
    insulin_basal: float
    meal_carbs: float
    created_at: datetime

    class Config:
        from_attributes = True

# Meal Logging
class MealCreate(BaseModel):
    timestamp: Optional[datetime] = None
    meal_name: str = Field(..., example="Mediterranean Chicken Salad")
    portion_g: float = Field(100.0, ge=1.0, le=2000.0)
    carbs_g: float = Field(..., ge=0.0, le=400.0)
    calories_kcal: Optional[float] = Field(None, ge=0.0)
    protein_g: Optional[float] = Field(None, ge=0.0)
    fat_g: Optional[float] = Field(None, ge=0.0)
    user_confirmed: bool = True
    source: str = "manual"

class MealResponse(BaseModel):
    id: str
    patient_id: str
    timestamp: datetime
    meal_name: str
    portion_g: float
    carbs_g: float
    calories_kcal: Optional[float]
    protein_g: Optional[float]
    fat_g: Optional[float]
    user_confirmed: bool
    source: str
    created_at: datetime

    class Config:
        from_attributes = True

# Insulin Logging
class InsulinCreate(BaseModel):
    timestamp: Optional[datetime] = None
    dose_type: str = Field("bolus", example="bolus") # 'bolus' or 'basal'
    units: float = Field(..., ge=0.1, le=100.0, example=4.5)
    insulin_type: Optional[str] = Field("Aspart (Novolog)", example="Aspart (Novolog)")
    notes: Optional[str] = None

class InsulinResponse(BaseModel):
    id: str
    patient_id: str
    timestamp: datetime
    dose_type: str
    units: float
    insulin_type: Optional[str]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

# Wearables Logging
class WearableCreate(BaseModel):
    timestamp: Optional[datetime] = None
    step_count: Optional[float] = Field(None, ge=0.0)
    heart_rate_bpm: Optional[float] = Field(None, ge=30.0, le=250.0)
    accel_magnitude_g: Optional[float] = None
    device_source: Optional[str] = "smartwatch"

class WearableResponse(BaseModel):
    id: str
    patient_id: str
    timestamp: datetime
    step_count: Optional[float]
    heart_rate_bpm: Optional[float]
    accel_magnitude_g: Optional[float]
    device_source: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

# History Record Responses
class ForecastRecordResponse(BaseModel):
    id: str
    patient_id: str
    timestamp: datetime
    current_glucose: float
    current_iob: float
    current_cob: float
    point_forecast: List[float]
    lower_80: List[float]
    upper_80: List[float]
    lower_95: List[float]
    upper_95: List[float]
    risk_assessment: Dict[str, Any]
    explanation: Dict[str, Any]
    disclaimer: str
    created_at: datetime

    class Config:
        from_attributes = True

class WhatIfRecordResponse(BaseModel):
    id: str
    patient_id: str
    timestamp: datetime
    scenario_name: str
    scenario_meal_carbs_g: float
    scenario_insulin_bolus_u: float
    simulated_trajectory: List[float]
    nadir_glucose: float
    time_to_nadir_min: int
    peak_glucose: float
    time_to_peak_min: int
    time_in_range_pct: float
    warnings: Optional[List[str]]
    created_at: datetime

    class Config:
        from_attributes = True

class DecisionRecordResponse(BaseModel):
    id: str
    patient_id: str
    timestamp: datetime
    food_analysis_id: Optional[str]
    forecast_id: Optional[str]
    what_if_id: Optional[str]
    alert_status: str
    recommended_action: str
    decision_summary: Dict[str, Any]
    disclaimer: str
    created_at: datetime

    class Config:
        from_attributes = True

# ==============================================================================
# 5. Phase 14 Longitudinal Analytics Schemas
# ==============================================================================
from api.schemas_analytics import (
    GlycemicBands,
    GlycemicVariability,
    HypoHyperEpisodes,
    GlucoseTimeSeriesPoint,
    GlucoseAnalyticsResponse,
    HourlyDiurnalPoint,
    QuadrantProfile,
    DiurnalAnalyticsResponse,
    HorizonErrorMetric,
    ForecastPerformanceResponse,
    RiskFactorsResponse,
    TimelineItem,
    TimelineResponse,
    AnalyticsSummaryResponse
)
