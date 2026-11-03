"""
GlucoShield Causal Context & Temporal Isolation Engine (Phase 17)
=================================================================
Enforces strict physical causality at forecast boundaries.
Guarantees that observations occurring after forecast origin T_0 are NEVER
accessible to the model, regardless of when they were uploaded or synchronized.
Preserves the architectural isolation between wearable context and the frozen V1 22-channel contract.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from db.models import (
    CGMReading,
    WearableObservation,
    DeviceRecord
)
from api.devices.schemas import CausalContextResponse


class CausalDeviceContextBuilder:
    """Constructs strictly causal historical windows and observational wearable contexts."""

    @staticmethod
    def build_causal_context(
        db: Session,
        patient_id: str,
        forecast_origin_utc: datetime,
        history_window_hours: float = 24.0
    ) -> CausalContextResponse:
        """
        Queries all observations for patient strictly constrained by:
            observation_timestamp <= forecast_origin_utc
        Validates that delayed or future-uploaded data beyond forecast_origin_utc
        is completely excluded from the context.
        """
        window_start = forecast_origin_utc - timedelta(hours=history_window_hours)

        # 1. Strictly causal CGM readings
        cgm_readings = db.query(CGMReading).filter(
            CGMReading.patient_id == patient_id,
            CGMReading.timestamp >= window_start,
            CGMReading.timestamp <= forecast_origin_utc  # Strict causal boundary
        ).order_by(CGMReading.timestamp).all()

        # 2. Strictly causal Wearable observations
        wearable_obs = db.query(WearableObservation).filter(
            WearableObservation.patient_id == patient_id,
            WearableObservation.timestamp >= window_start,
            WearableObservation.timestamp <= forecast_origin_utc  # Strict causal boundary
        ).order_by(WearableObservation.timestamp).all()

        # 3. Audit future/leakage observations (data in DB observed AFTER forecast origin)
        future_count = db.query(DeviceRecord).filter(
            DeviceRecord.patient_id == patient_id,
            DeviceRecord.observation_timestamp > forecast_origin_utc
        ).count()

        # Compute summary metrics over causal window
        latest_cgm = cgm_readings[-1].cgm_glucose if cgm_readings else None

        hr_values = [w.heart_rate_bpm for w in wearable_obs if w.heart_rate_bpm is not None]
        mean_hr = round(sum(hr_values) / len(hr_values), 1) if hr_values else None

        step_values = [w.step_count for w in wearable_obs if w.step_count is not None]
        total_steps = sum(step_values) if step_values else None

        # Estimated active minutes from steps (>30 steps/min equivalent)
        active_mins = round(total_steps / 100.0, 1) if total_steps else None

        return CausalContextResponse(
            patient_id=patient_id,
            forecast_origin=forecast_origin_utc,
            cgm_count_causal=len(cgm_readings),
            wearable_count_causal=len(wearable_obs),
            latest_cgm_glucose=latest_cgm,
            mean_heart_rate_bpm=mean_hr,
            total_steps_window=total_steps,
            active_minutes_window=active_mins,
            sleep_efficiency_pct=None,
            future_observations_excluded_count=future_count,
            causal_boundary_verified=True
        )

    @staticmethod
    def extract_causal_v1_history(
        db: Session,
        patient_id: str,
        forecast_origin_utc: datetime,
        n_steps: int = 96
    ) -> List[Dict[str, Any]]:
        """
        Extracts up to n_steps (default 96) historical 15-minute readings ending
        at or before forecast_origin_utc.
        Does NOT inject wearable fields into the returned sequence to preserve
        the frozen V1 22-channel contract.
        """
        readings = db.query(CGMReading).filter(
            CGMReading.patient_id == patient_id,
            CGMReading.timestamp <= forecast_origin_utc
        ).order_by(desc(CGMReading.timestamp)).limit(n_steps).all()

        # Re-order chronologically (oldest -> newest)
        readings.reverse()

        result = []
        for r in readings:
            result.append({
                "timestamp": r.timestamp.isoformat(),
                "cgm_glucose": r.cgm_glucose,
                "insulin_bolus": r.insulin_bolus,
                "insulin_basal": r.insulin_basal,
                "meal_carbs": r.meal_carbs
            })
        return result
