"""
GlucoShield Device Ingestion & Deduplication Service (Phase 17)
==============================================================
Implements provider-independent normalization, unit conversion, deterministic
idempotency hash deduplication, delayed-arrival detection, and clinical table mirroring.
"""

import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Tuple, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from db.models import (
    DeviceConnection,
    DeviceRecord,
    CGMReading,
    WearableObservation,
    MealRecord,
    InsulinRecord,
    PatientProfile
)
from api.devices.schemas import (
    MeasurementType,
    DeviceProvider,
    QualityStatus,
    DeviceObservationIn,
    DeviceSyncRequest,
    DeviceSyncResponse
)


class DeviceIngestionService:
    """Core synchronization and normalization coordinator for patient devices."""

    MAX_CLOCK_SKEW_FUTURE_SECONDS = 300.0  # 5 minutes maximum future timestamp allowance
    MIN_PLAUSIBLE_YEAR = 2000              # Rejects impossible historical timestamps

    @staticmethod
    def normalize_timestamp(dt: datetime, tz_str: Optional[str] = "UTC") -> Tuple[datetime, str]:
        """
        Normalizes any datetime into a UTC-naive datetime for storage,
        while identifying and validating the source timezone descriptor.
        """
        resolved_tz = tz_str or "UTC"

        # Case 1: Datetime is timezone-aware
        if dt.tzinfo is not None:
            dt_utc = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt_utc, resolved_tz

        # Case 2: Datetime is naive, but timezone offset provided in tz_str
        if resolved_tz in ("+05:30", "IST", "Asia/Kolkata"):
            ist_offset = timezone(timedelta(hours=5, minutes=30))
            dt_aware = dt.replace(tzinfo=ist_offset)
            dt_utc = dt_aware.astimezone(timezone.utc).replace(tzinfo=None)
            return dt_utc, resolved_tz

        if resolved_tz.startswith(("+", "-")) and len(resolved_tz) == 6 and ":" in resolved_tz:
            try:
                sign = 1 if resolved_tz[0] == "+" else -1
                parts = resolved_tz[1:].split(":")
                hours = int(parts[0])
                mins = int(parts[1])
                offset = timezone(sign * timedelta(hours=hours, minutes=mins))
                dt_aware = dt.replace(tzinfo=offset)
                dt_utc = dt_aware.astimezone(timezone.utc).replace(tzinfo=None)
                return dt_utc, resolved_tz
            except Exception:
                pass

        # Case 3: Default assume UTC
        return dt, resolved_tz

    @staticmethod
    def validate_and_normalize_measurement(
        m_type: MeasurementType,
        raw_val: Optional[float],
        raw_unit: str
    ) -> Tuple[Optional[float], str, Optional[str]]:
        """
        Validates physiological bounds and standardizes measurement units.
        Returns: (normalized_value, standard_unit, error_message_if_invalid)
        """
        # Preserve explicit MISSING data without fabricating a zero or mean
        if raw_val is None:
            unit_map = {
                MeasurementType.GLUCOSE: "mg/dL",
                MeasurementType.HEART_RATE: "bpm",
                MeasurementType.STEPS: "count",
                MeasurementType.ACTIVE_MINUTES: "minutes",
                MeasurementType.SLEEP_SESSION: "minutes",
                MeasurementType.MEAL_CARBS: "grams",
                MeasurementType.INSULIN_DOSE: "units",
                MeasurementType.CONTEXT_EVENT: "rating"
            }
            return None, unit_map.get(m_type, raw_unit), None

        val = float(raw_val)
        unit = raw_unit.strip().lower()

        if m_type == MeasurementType.GLUCOSE:
            if unit in ("mmol/l", "mmol/"):
                val = round(val * 18.0182, 1)
            elif unit not in ("mg/dl", "mg/"):
                return None, "mg/dL", f"Unsupported glucose unit: '{raw_unit}'. Expected mg/dL or mmol/L."

            if val < 20.0 or val > 600.0:
                return None, "mg/dL", f"Glucose value {val} mg/dL is outside plausible range [20, 600]."
            return val, "mg/dL", None

        if m_type == MeasurementType.HEART_RATE:
            if unit != "bpm":
                pass # treat as bpm
            if val < 30.0 or val > 250.0:
                return None, "bpm", f"Heart rate {val} bpm is outside plausible range [30, 250]."
            return round(val, 1), "bpm", None

        if m_type == MeasurementType.STEPS:
            if val < 0.0 or val > 100000.0:
                return None, "count", f"Step count {val} is outside plausible range [0, 100000]."
            return float(int(val)), "count", None

        if m_type == MeasurementType.ACTIVE_MINUTES:
            if val < 0.0 or val > 1440.0:
                return None, "minutes", f"Active minutes {val} is outside daily range [0, 1440]."
            return round(val, 1), "minutes", None

        if m_type == MeasurementType.SLEEP_SESSION:
            if val < 0.0 or val > 1440.0:
                return None, "minutes", f"Sleep duration {val} is outside daily range [0, 1440]."
            return round(val, 1), "minutes", None

        if m_type == MeasurementType.MEAL_CARBS:
            if val < 0.0 or val > 350.0:
                return None, "grams", f"Carbohydrate intake {val}g is outside safe clinical range [0, 350]."
            return round(val, 1), "grams", None

        if m_type == MeasurementType.INSULIN_DOSE:
            if val < 0.0 or val > 100.0:
                return None, "units", f"Insulin dose {val}U is outside safe clinical range [0, 100]."
            return round(val, 2), "units", None

        # Generic context event
        return val, raw_unit, None

    @staticmethod
    def compute_idempotency_key(
        patient_id: str,
        provider: str,
        device_id: str,
        m_type: str,
        obs_time_utc: datetime,
        raw_source_id: Optional[str]
    ) -> str:
        """Computes deterministic SHA-256 fingerprint for deduplication."""
        fingerprint = f"{patient_id}:{provider.lower()}:{device_id}:{m_type.lower()}:{obs_time_utc.strftime('%Y-%m-%d %H:%M:%S')}:{raw_source_id or ''}"
        return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()

    def sync_device_observations(
        self,
        db: Session,
        patient: PatientProfile,
        request: DeviceSyncRequest
    ) -> DeviceSyncResponse:
        """
        Executes end-to-end device synchronization:
        1. Ensures DeviceConnection record exists
        2. Validates timestamps (rejects impossible/future timestamps)
        3. Normalizes units and timezones
        4. Detects duplicates via deterministic idempotency keys
        5. Persists to device_records and mirrors to clinical tables
        6. Updates device connection telemetry and freshness
        """
        now_utc = datetime.utcnow()
        sync_id = str(uuid.uuid4())

        # Ensure or fetch DeviceConnection
        conn = db.query(DeviceConnection).filter(
            DeviceConnection.patient_id == patient.id,
            DeviceConnection.device_id == request.device_id
        ).first()

        if not conn:
            conn = DeviceConnection(
                patient_id=patient.id,
                device_id=request.device_id,
                provider=request.provider.value,
                device_name=request.device_name or f"{request.provider.value} Device",
                connection_status="connected"
            )
            db.add(conn)
            db.flush()
        else:
            conn.connection_status = "connected"

        accepted_count = 0
        duplicate_count = 0
        rejected_count = 0
        errors: List[str] = []
        latest_obs_time: Optional[datetime] = None

        for idx, obs in enumerate(request.observations):
            # 1. Timestamp Normalization
            obs_utc, src_tz = self.normalize_timestamp(obs.observation_timestamp, obs.source_timezone)

            # 2. Timestamp Sanity Checks
            if obs_utc.year < self.MIN_PLAUSIBLE_YEAR:
                rejected_count += 1
                errors.append(f"Obs[{idx}]: Timestamp {obs_utc.isoformat()} is before plausible year {self.MIN_PLAUSIBLE_YEAR}.")
                continue

            max_allowed = now_utc + timedelta(seconds=self.MAX_CLOCK_SKEW_FUTURE_SECONDS)
            if obs_utc > max_allowed:
                rejected_count += 1
                errors.append(f"Obs[{idx}]: Future timestamp {obs_utc.isoformat()} exceeds clock skew limit.")
                continue

            # 3. Measurement Validation & Normalization
            norm_val, norm_unit, val_err = self.validate_and_normalize_measurement(
                obs.measurement_type,
                obs.value,
                obs.unit
            )
            if val_err:
                rejected_count += 1
                errors.append(f"Obs[{idx}]: {val_err}")
                continue

            # 4. Deterministic Idempotency Key
            idemp_key = self.compute_idempotency_key(
                patient.id,
                request.provider.value,
                request.device_id,
                obs.measurement_type.value,
                obs_utc,
                obs.raw_source_id
            )

            # Check if this exact event was already ingested
            existing_rec = db.query(DeviceRecord).filter(
                DeviceRecord.patient_id == patient.id,
                DeviceRecord.idempotency_key == idemp_key
            ).first()

            if existing_rec:
                duplicate_count += 1
                # Skip clinical duplication, mark connection counter
                continue

            # 5. Determine Quality / Trust Flag
            quality_flag = obs.quality_status.value if obs.quality_status else QualityStatus.VALID.value
            if norm_val is None:
                quality_flag = QualityStatus.MISSING.value
            elif (now_utc - obs_utc).total_seconds() > 3600.0:
                # Delayed upload: true event occurred >1 hr before server receipt
                quality_flag = QualityStatus.DELAYED.value

            # 6. Persist DeviceRecord
            dev_rec = DeviceRecord(
                patient_id=patient.id,
                device_id=request.device_id,
                idempotency_key=idemp_key,
                provider=request.provider.value,
                measurement_type=obs.measurement_type.value,
                value=norm_val,
                unit=norm_unit,
                observation_timestamp=obs_utc,
                source_timezone=src_tz,
                ingestion_timestamp=now_utc,
                quality_flag=quality_flag,
                raw_source_id=obs.raw_source_id,
                metadata_json=obs.metadata
            )
            db.add(dev_rec)

            # 7. Mirror to Core Clinical Tables
            self._mirror_to_clinical_tables(db, patient.id, obs.measurement_type, norm_val, obs_utc, request.provider.value)

            accepted_count += 1
            if latest_obs_time is None or obs_utc > latest_obs_time:
                latest_obs_time = obs_utc

        # Update Connection Diagnostics
        conn.last_sync_at = now_utc
        if latest_obs_time:
            if conn.last_observation_at is None or latest_obs_time > conn.last_observation_at:
                conn.last_observation_at = latest_obs_time
        conn.records_synced_total += accepted_count
        conn.duplicate_count += duplicate_count
        conn.error_count += rejected_count

        db.commit()

        # Compute data freshness
        freshness_s = None
        if conn.last_observation_at:
            freshness_s = max(0.0, (now_utc - conn.last_observation_at).total_seconds())

        status = "SUCCESS"
        if rejected_count > 0 and accepted_count > 0:
            status = "PARTIAL_SUCCESS"
        elif rejected_count > 0 and accepted_count == 0:
            status = "FAILED"

        new_cursor = None
        if latest_obs_time:
            new_cursor = latest_obs_time.isoformat()

        return DeviceSyncResponse(
            sync_id=sync_id,
            device_id=request.device_id,
            status=status,
            records_received=len(request.observations),
            records_accepted=accepted_count,
            duplicates_ignored=duplicate_count,
            records_rejected=rejected_count,
            errors=errors,
            data_freshness_seconds=freshness_s,
            new_cursor=new_cursor
        )

    def _mirror_to_clinical_tables(
        self,
        db: Session,
        patient_id: str,
        m_type: MeasurementType,
        val: Optional[float],
        obs_utc: datetime,
        provider: str
    ):
        """Mirrors valid normalized device observations into existing clinical tables."""
        if val is None:
            return

        if m_type == MeasurementType.GLUCOSE:
            cgm = db.query(CGMReading).filter(
                CGMReading.patient_id == patient_id,
                CGMReading.timestamp == obs_utc
            ).first()
            if not cgm:
                cgm = CGMReading(
                    patient_id=patient_id,
                    timestamp=obs_utc,
                    cgm_glucose=val,
                    insulin_bolus=0.0,
                    insulin_basal=0.0,
                    meal_carbs=0.0
                )
                db.add(cgm)
            else:
                cgm.cgm_glucose = val

        elif m_type in (MeasurementType.HEART_RATE, MeasurementType.STEPS):
            wear = db.query(WearableObservation).filter(
                WearableObservation.patient_id == patient_id,
                WearableObservation.timestamp == obs_utc
            ).first()
            if not wear:
                wear = WearableObservation(
                    patient_id=patient_id,
                    timestamp=obs_utc,
                    step_count=val if m_type == MeasurementType.STEPS else None,
                    heart_rate_bpm=val if m_type == MeasurementType.HEART_RATE else None,
                    device_source=provider
                )
                db.add(wear)
            else:
                if m_type == MeasurementType.STEPS:
                    wear.step_count = val
                elif m_type == MeasurementType.HEART_RATE:
                    wear.heart_rate_bpm = val

        elif m_type == MeasurementType.MEAL_CARBS:
            meal = MealRecord(
                patient_id=patient_id,
                timestamp=obs_utc,
                meal_name=f"Device Meal ({provider})",
                portion_g=100.0,
                carbs_g=val,
                user_confirmed=True,
                source=provider
            )
            db.add(meal)

        elif m_type == MeasurementType.INSULIN_DOSE:
            ins = InsulinRecord(
                patient_id=patient_id,
                timestamp=obs_utc,
                units=val,
                dose_type="bolus",
                insulin_type=f"Device Sync ({provider})",
                notes=f"Auto-synced from {provider}"
            )
            db.add(ins)
