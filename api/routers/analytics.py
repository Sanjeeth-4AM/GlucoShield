"""
GlucoShield Longitudinal Analytics API Router
=============================================
Endpoints for querying longitudinal trends, summaries, glycemic distributions,
time-in-range metrics, diurnal AGP profiles, forecast accuracy tracking,
risk factor correlations, and unified chronological timelines.

STRICT ACCESS CONTROL:
All endpoints require authentication and enforce patient ownership validation
via `verify_patient_ownership` to prevent horizontal privilege escalation (IDOR).
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import PatientProfile
from api.deps import verify_patient_ownership
from api.schemas_analytics import (
    AnalyticsSummaryResponse,
    GlucoseAnalyticsResponse,
    DiurnalAnalyticsResponse,
    ForecastPerformanceResponse,
    RiskFactorsResponse,
    TimelineResponse
)
from api.analytics_service import (
    get_patient_analytics_summary,
    get_patient_glucose_analytics,
    get_patient_diurnal_profile,
    get_patient_forecast_performance,
    get_patient_risk_analytics,
    get_patient_timeline
)

router = APIRouter(prefix="/api/v1/patients", tags=["Longitudinal Analytics"])

@router.get("/{patient_id}/analytics/summary", response_model=AnalyticsSummaryResponse)
def get_analytics_summary(
    patient: PatientProfile = Depends(verify_patient_ownership),
    period: str = Query("14d", pattern="^(24h|today|7d|14d|30d|all)$", description="Aggregation window"),
    start_time: Optional[datetime] = Query(None, description="Explicit start timestamp"),
    end_time: Optional[datetime] = Query(None, description="Explicit end timestamp"),
    db: Session = Depends(get_db)
):
    """
    Retrieves high-level longitudinal summary: glycemic variability (CV, GMI, LBGI, HBGI),
    time-in-range bands (TIR, TITR, TBR, TAR), hypo/hyper episodes, and daily factor metrics.
    """
    return get_patient_analytics_summary(
        db=db,
        patient_id=patient.id,
        period=period,
        start_time=start_time,
        end_time=end_time
    )

@router.get("/{patient_id}/analytics/glucose", response_model=GlucoseAnalyticsResponse)
def get_glucose_analytics(
    patient: PatientProfile = Depends(verify_patient_ownership),
    period: str = Query("14d", pattern="^(24h|today|7d|14d|30d|all)$"),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    include_readings: bool = Query(True, description="Whether to include downsampled readings time series"),
    db: Session = Depends(get_db)
):
    """
    Retrieves detailed glycemic analytics, distribution bands, and time-series readings.
    """
    return get_patient_glucose_analytics(
        db=db,
        patient_id=patient.id,
        period=period,
        start_time=start_time,
        end_time=end_time,
        include_readings=include_readings
    )

@router.get("/{patient_id}/analytics/diurnal", response_model=DiurnalAnalyticsResponse)
def get_diurnal_analytics(
    patient: PatientProfile = Depends(verify_patient_ownership),
    period: str = Query("14d", pattern="^(24h|today|7d|14d|30d|all)$"),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Retrieves 24-hour diurnal AGP profile percentiles and 4-quadrant circadian glucose statistics.
    """
    return get_patient_diurnal_profile(
        db=db,
        patient_id=patient.id,
        period=period,
        start_time=start_time,
        end_time=end_time
    )

@router.get("/{patient_id}/analytics/forecast-performance", response_model=ForecastPerformanceResponse)
def get_forecast_performance(
    patient: PatientProfile = Depends(verify_patient_ownership),
    period: str = Query("14d", pattern="^(24h|today|7d|14d|30d|all)$"),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Evaluates historical forecast accuracy against actual subsequent CGM readings.
    Returns MAE, RMSE, Mean Bias, empirical coverage for 80% & 95% intervals, and horizon breakdown.
    """
    return get_patient_forecast_performance(
        db=db,
        patient_id=patient.id,
        period=period,
        start_time=start_time,
        end_time=end_time
    )

@router.get("/{patient_id}/analytics/risk-factors", response_model=RiskFactorsResponse)
def get_risk_factors(
    patient: PatientProfile = Depends(verify_patient_ownership),
    period: str = Query("14d", pattern="^(24h|today|7d|14d|30d|all)$"),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Computes longitudinal clinical risk alerts, context factors (IOB, COB), nutrition totals,
    and wearable activity correlations.
    """
    return get_patient_risk_analytics(
        db=db,
        patient_id=patient.id,
        period=period,
        start_time=start_time,
        end_time=end_time
    )

@router.get("/{patient_id}/analytics/timeline", response_model=TimelineResponse)
def get_unified_timeline(
    patient: PatientProfile = Depends(verify_patient_ownership),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    event_type: Optional[str] = Query(None, pattern="^(cgm|meal|insulin|forecast|decision|wearable)$"),
    period: str = Query("14d", pattern="^(24h|today|7d|14d|30d|all)$"),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Retrieves a unified, paginated, chronological stream of all patient events
    (CGM, meals, insulin, forecasts, decisions, wearables).
    """
    return get_patient_timeline(
        db=db,
        patient_id=patient.id,
        limit=limit,
        offset=offset,
        event_type=event_type,
        period=period,
        start_time=start_time,
        end_time=end_time
    )
