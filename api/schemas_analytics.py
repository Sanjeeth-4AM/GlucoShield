"""
GlucoShield Longitudinal Analytics Schemas
==========================================
Pydantic contracts for Phase 14 longitudinal summaries, glycemic distributions,
time-in-range metrics, diurnal AGP profiles, forecast accuracy tracking,
risk factor correlations, and unified chronological timeline streams.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class GlycemicBands(BaseModel):
    tir_pct: Optional[float] = Field(None, description="Time in Target Range (70-180 mg/dL) percentage")
    tir_minutes: int = Field(0, description="Minutes spent in target range")
    titr_pct: Optional[float] = Field(None, description="Time in Tight Range (70-140 mg/dL) percentage")
    titr_minutes: int = Field(0, description="Minutes spent in tight range")
    tbr_l1_pct: Optional[float] = Field(None, description="Time Below Range Level 1 (54-69 mg/dL) percentage")
    tbr_l1_minutes: int = Field(0, description="Minutes spent in TBR Level 1")
    tbr_l2_pct: Optional[float] = Field(None, description="Time Below Range Level 2 (<54 mg/dL) percentage")
    tbr_l2_minutes: int = Field(0, description="Minutes spent in TBR Level 2")
    tar_l1_pct: Optional[float] = Field(None, description="Time Above Range Level 1 (181-250 mg/dL) percentage")
    tar_l1_minutes: int = Field(0, description="Minutes spent in TAR Level 1")
    tar_l2_pct: Optional[float] = Field(None, description="Time Above Range Level 2 (>250 mg/dL) percentage")
    tar_l2_minutes: int = Field(0, description="Minutes spent in TAR Level 2")

class GlycemicVariability(BaseModel):
    mean_glucose: Optional[float] = Field(None, description="Mean CGM glucose in mg/dL")
    median_glucose: Optional[float] = Field(None, description="Median CGM glucose in mg/dL")
    std_glucose: Optional[float] = Field(None, description="Standard deviation of glucose in mg/dL")
    cv_pct: Optional[float] = Field(None, description="Coefficient of Variation (CV = std / mean * 100)")
    min_glucose: Optional[float] = Field(None, description="Minimum observed glucose in mg/dL")
    max_glucose: Optional[float] = Field(None, description="Maximum observed glucose in mg/dL")
    gmi_pct: Optional[float] = Field(None, description="Glucose Management Indicator / estimated HbA1c (Bergenstal 2018)")
    lbgi: Optional[float] = Field(None, description="Low Blood Glucose Index (Kovatchev et al.)")
    hbgi: Optional[float] = Field(None, description="High Blood Glucose Index (Kovatchev et al.)")

class HypoHyperEpisodes(BaseModel):
    hypo_episode_count: int = Field(0, description="Number of contiguous hypoglycemic events (<70 mg/dL)")
    severe_hypo_episode_count: int = Field(0, description="Number of contiguous severe hypoglycemic events (<54 mg/dL)")
    hyper_episode_count: int = Field(0, description="Number of contiguous hyperglycemic events (>180 mg/dL)")
    mean_hypo_duration_minutes: float = Field(0.0, description="Average duration of hypo episodes in minutes")
    mean_hyper_duration_minutes: float = Field(0.0, description="Average duration of hyper episodes in minutes")

class GlucoseTimeSeriesPoint(BaseModel):
    timestamp: datetime
    cgm_glucose: float
    insulin_bolus: float = 0.0
    insulin_basal: float = 0.0
    meal_carbs: float = 0.0

class GlucoseAnalyticsResponse(BaseModel):
    patient_id: str
    period: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    has_data: bool
    total_readings: int
    days_of_data: float
    glycemic_variability: GlycemicVariability
    glycemic_bands: GlycemicBands
    episodes: HypoHyperEpisodes
    glucose_readings: List[GlucoseTimeSeriesPoint] = []
    research_disclaimer: str

class HourlyDiurnalPoint(BaseModel):
    hour: int = Field(..., ge=0, le=23, description="Hour of day (0-23)")
    reading_count: int = Field(0)
    mean_glucose: Optional[float] = None
    median_glucose: Optional[float] = None
    p10: Optional[float] = None
    p25: Optional[float] = None
    p75: Optional[float] = None
    p90: Optional[float] = None

class QuadrantProfile(BaseModel):
    quadrant: str = Field(..., description="Time window quadrant name")
    hours: str = Field(..., description="Time range (e.g. '00:00 - 06:00')")
    reading_count: int = Field(0)
    mean_glucose: Optional[float] = None
    std_glucose: Optional[float] = None
    cv_pct: Optional[float] = None
    tir_pct: Optional[float] = None
    tbr_pct: Optional[float] = None
    tar_pct: Optional[float] = None

class DiurnalAnalyticsResponse(BaseModel):
    patient_id: str
    period: str
    has_data: bool
    quadrants: List[QuadrantProfile]
    hourly_agp: List[HourlyDiurnalPoint]
    research_disclaimer: str

class HorizonErrorMetric(BaseModel):
    horizon_step: int = Field(..., ge=1, le=20)
    horizon_minutes: int = Field(..., ge=15, le=300)
    sample_count: int
    mae_mg_dl: Optional[float] = None
    rmse_mg_dl: Optional[float] = None
    bias_mg_dl: Optional[float] = None
    coverage_80_pct: Optional[float] = None
    coverage_95_pct: Optional[float] = None
    mean_width_80_mg_dl: Optional[float] = None
    mean_width_95_mg_dl: Optional[float] = None

class ForecastPerformanceResponse(BaseModel):
    patient_id: str
    period: str
    has_data: bool
    total_forecasts_logged: int
    evaluated_pairs_count: int
    pending_evaluation_count: int
    overall_mae_mg_dl: Optional[float] = None
    overall_rmse_mg_dl: Optional[float] = None
    overall_bias_mg_dl: Optional[float] = None
    overall_coverage_80_pct: Optional[float] = None
    overall_coverage_95_pct: Optional[float] = None
    overall_mean_width_80_mg_dl: Optional[float] = None
    overall_mean_width_95_mg_dl: Optional[float] = None
    horizon_metrics: List[HorizonErrorMetric] = []
    daily_trends: List[Dict[str, Any]] = []
    research_disclaimer: str

class RiskFactorsResponse(BaseModel):
    patient_id: str
    period: str
    has_data: bool
    total_alerts: int
    alert_counts: Dict[str, int]
    mean_iob_at_alert: Optional[float] = None
    mean_cob_at_alert: Optional[float] = None
    nutrition_totals: Dict[str, Any]
    wearable_trends: Dict[str, Any]
    research_disclaimer: str

class TimelineItem(BaseModel):
    id: str
    timestamp: datetime
    event_type: str = Field(..., description="'cgm', 'meal', 'insulin', 'forecast', 'decision', 'wearable'")
    title: str
    primary_value: str
    secondary_value: Optional[str] = None
    severity: Optional[str] = Field("normal", description="'normal', 'warning', 'critical', 'info'")
    metadata: Dict[str, Any] = {}

class TimelineResponse(BaseModel):
    patient_id: str
    period: str
    total_events: int
    limit: int
    offset: int
    events: List[TimelineItem]
    research_disclaimer: str

class AnalyticsSummaryResponse(BaseModel):
    patient_id: str
    period: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    has_data: bool
    total_readings: int
    days_of_data: float
    glycemic_variability: GlycemicVariability
    glycemic_bands: GlycemicBands
    episodes: HypoHyperEpisodes
    daily_metrics: Dict[str, Any]
    forecast_eval_summary: Optional[Dict[str, Any]] = None
    research_disclaimer: str
