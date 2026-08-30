"""
GlucoShield API Pydantic Data Schemas
=====================================
Strict Pydantic request and response contracts for all Phase 8 REST endpoints.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any

class HealthResponse(BaseModel):
    status: str = Field(..., example="healthy")
    version: str = Field(..., example="1.0.0")
    neural_forecaster_loaded: bool = True
    hybrid_forecaster_loaded: bool = True
    ode_digital_twin_ready: bool = True
    food_vision_ready: bool = True
    active_channels_contract: int = 22
    research_disclaimer: str
    timestamp: str

class TimeStepReading(BaseModel):
    timestamp: Optional[str] = Field(None, example="2026-08-28T12:00:00")
    cgm_glucose: float = Field(..., ge=20.0, le=600.0, example=125.0, description="CGM glucose in mg/dL")
    insulin_bolus: float = Field(0.0, ge=0.0, le=50.0, example=0.0, description="Bolus insulin units")
    insulin_basal: float = Field(0.0, ge=0.0, le=20.0, example=0.5, description="Basal insulin units")
    meal_carbs: float = Field(0.0, ge=0.0, le=300.0, example=0.0, description="Carbohydrate intake grams")

class PatientStaticProfile(BaseModel):
    age: float = Field(45.0, ge=1.0, le=120.0, example=45.0)
    bmi: float = Field(26.5, ge=10.0, le=70.0, example=26.5)
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

class ForecastRequest(BaseModel):
    patient_id: str = Field("demo_patient_001", example="patient_101")
    history_readings: List[TimeStepReading] = Field(..., min_length=96, max_length=96, description="Exactly 96 readings (24 hours at 15m intervals)")
    static_profile: Optional[PatientStaticProfile] = Field(default_factory=PatientStaticProfile)
    wearable_context: Optional[OptionalWearableContext] = None

class ForecastResponse(BaseModel):
    disclaimer: str
    patient_id: str
    current_state: Dict[str, Any]
    forecast: Dict[str, Any]
    hybrid_components: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    explanation: Dict[str, Any]
    wearable_context_logged: bool = False

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
