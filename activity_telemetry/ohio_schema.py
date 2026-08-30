"""
GlucoShield OhioT1DM Schema Configuration & Data Contracts
==========================================================
Configurable schema mappings and validation report dataclasses for OhioT1DM telemetry.
Supports XML / CSV structures without assuming hardcoded column layouts.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

@dataclass
class OhioT1DMConfig:
    """Configurable signal mapping specification for OhioT1DM datasets."""
    participant_id_field: str = "patient_id"
    timestamp_field: str = "ts"
    glucose_field: str = "glucose_level"
    heart_rate_field: str = "heartrate"
    step_field: str = "step"
    accel_field: str = "acceleration"
    accel_x_field: str = "accel_x"
    accel_y_field: str = "accel_y"
    accel_z_field: str = "accel_z"
    basal_field: str = "basal"
    bolus_field: str = "bolus"
    meal_field: str = "meal"
    
    # Unit Specifications
    glucose_unit: str = "mg/dL"  # mg/dL or mmol/L
    heart_rate_unit: str = "bpm"
    timestamp_format: str = "%Y-%m-%d %H:%M:%S"
    
    # Expected Native Sample Intervals
    expected_cgm_interval_min: float = 5.0
    expected_wearable_interval_min: float = 5.0


@dataclass
class OhioValidationReport:
    """Structured data contract validation report for an OhioT1DM participant or cohort."""
    participant_id: str
    is_valid: bool
    total_raw_records: int
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None
    duration_days: float = 0.0
    
    # Signal Completeness & Missingness (%)
    glucose_records: int = 0
    glucose_missing_pct: float = 0.0
    heart_rate_records: int = 0
    heart_rate_missing_pct: float = 0.0
    step_records: int = 0
    step_missing_pct: float = 0.0
    accel_records: int = 0
    accel_missing_pct: float = 0.0
    bolus_events: int = 0
    meal_events: int = 0
    
    # Data Integrity Checks
    monotonic_timestamps: bool = True
    duplicate_timestamps_found: int = 0
    out_of_range_glucose_count: int = 0
    out_of_range_hr_count: int = 0
    future_leakage_detected: bool = False
    mixed_participant_leakage: bool = False
    
    # Validation Errors & Warnings
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "participant_id": self.participant_id,
            "is_valid": self.is_valid,
            "total_raw_records": self.total_raw_records,
            "date_range_start": self.date_range_start,
            "date_range_end": self.date_range_end,
            "duration_days": round(self.duration_days, 1),
            "glucose_records": self.glucose_records,
            "glucose_missing_pct": round(self.glucose_missing_pct, 1),
            "heart_rate_records": self.heart_rate_records,
            "heart_rate_missing_pct": round(self.heart_rate_missing_pct, 1),
            "step_records": self.step_records,
            "step_missing_pct": round(self.step_missing_pct, 1),
            "accel_records": self.accel_records,
            "accel_missing_pct": round(self.accel_missing_pct, 1),
            "bolus_events": self.bolus_events,
            "meal_events": self.meal_events,
            "monotonic_timestamps": self.monotonic_timestamps,
            "duplicate_timestamps_found": self.duplicate_timestamps_found,
            "out_of_range_glucose_count": self.out_of_range_glucose_count,
            "out_of_range_hr_count": self.out_of_range_hr_count,
            "future_leakage_detected": self.future_leakage_detected,
            "mixed_participant_leakage": self.mixed_participant_leakage,
            "errors": self.errors,
            "warnings": self.warnings
        }
