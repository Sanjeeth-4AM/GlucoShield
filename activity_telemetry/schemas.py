"""
GlucoShield Activity Telemetry Schemas
======================================
Structured data types for raw telemetry, aligned 15-minute windows,
engineered features, coverage reports, and detected activity episodes.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

@dataclass
class RawTelemetrySample:
    """A single timestamped raw telemetry reading."""
    timestamp: str  # ISO 8601 UTC
    heart_rate: Optional[float] = None  # bpm
    accel_x: Optional[float] = None     # g
    accel_y: Optional[float] = None     # g
    accel_z: Optional[float] = None     # g
    steps: Optional[float] = None       # step count in delta t
    cgm_glucose: Optional[float] = None # mg/dL
    respiration_rate: Optional[float] = None # breaths/min


@dataclass
class ActivityFeatures15m:
    """Engineered 15-minute activity features aligned with GlucoShield grid."""
    timestamp: str
    participant_id: str
    
    # Primary Wearable Features
    steps_15m: Optional[float] = None
    hr_mean_15m: Optional[float] = None
    hr_std_15m: Optional[float] = None
    accel_mag_15m: Optional[float] = None
    is_active_15m: int = 0
    active_load_60m: float = 0.0
    hr_reserve_pct: Optional[float] = None
    exercise_onset_flag: int = 0
    
    # Associated Glucose
    cgm_glucose: Optional[float] = None
    
    # Quality & Missingness Indicators
    sensor_coverage_pct: float = 0.0
    sensor_missing: int = 0  # 1 if coverage < threshold
    quality_flag: str = "GOOD"  # GOOD, PARTIAL, SENSOR_MISSING, UNKNOWN

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "participant_id": self.participant_id,
            "steps_15m": round(self.steps_15m, 1) if self.steps_15m is not None else None,
            "hr_mean_15m": round(self.hr_mean_15m, 1) if self.hr_mean_15m is not None else None,
            "hr_std_15m": round(self.hr_std_15m, 2) if self.hr_std_15m is not None else None,
            "accel_mag_15m": round(self.accel_mag_15m, 4) if self.accel_mag_15m is not None else None,
            "is_active_15m": self.is_active_15m,
            "active_load_60m": round(self.active_load_60m, 1),
            "hr_reserve_pct": round(self.hr_reserve_pct, 1) if self.hr_reserve_pct is not None else None,
            "exercise_onset_flag": self.exercise_onset_flag,
            "cgm_glucose": round(self.cgm_glucose, 1) if self.cgm_glucose is not None else None,
            "sensor_coverage_pct": round(self.sensor_coverage_pct, 1),
            "sensor_missing": self.sensor_missing,
            "quality_flag": self.quality_flag
        }


@dataclass
class ParticipantCoverageReport:
    """Summary quality metrics for a single participant's wearable recording."""
    participant_id: str
    total_duration_hours: float
    total_15m_windows: int
    valid_cgm_windows: int
    valid_wearable_windows: int
    cgm_coverage_pct: float
    wearable_coverage_pct: float
    joint_coverage_pct: float
    detected_active_windows: int
    active_time_pct: float
    mean_resting_hr: Optional[float] = None
    mean_active_hr: Optional[float] = None


@dataclass
class ActivityEpisode:
    """Contiguous active workout episode."""
    participant_id: str
    start_timestamp: str
    end_timestamp: str
    duration_minutes: float
    mean_hr: float
    peak_hr: float
    total_steps: float
    mean_accel: float
    pre_glucose: Optional[float] = None
    post_glucose: Optional[float] = None
    glucose_delta: Optional[float] = None
