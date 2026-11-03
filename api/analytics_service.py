"""
GlucoShield Longitudinal Analytics Service Layer
================================================
Transforms stored historical patient data into longitudinal trends, glycemic summaries,
time-in-range distributions, diurnal AGP profiles, causal forecast accuracy evaluations,
risk factor correlations, and unified chronological timelines.

STRICT GOVERNANCE & SAFETY:
  - Analytics only: pure read service querying indexed persistence tables.
  - Zero modification to forecasting weights, checkpoints, scalers, or ODE parameters.
  - All clinical indices (TIR, GMI, HBGI/LBGI) are descriptive consensus metrics.
  - Zero-division and empty dataset safeguards throughout.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc

from db.models import (
    CGMReading,
    MealRecord,
    InsulinRecord,
    ForecastRecord,
    DecisionRecord,
    WearableObservation,
    PatientProfile
)
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

RESEARCH_DISCLAIMER = (
    "RESEARCH PROTOTYPE ONLY: Longitudinal analytics, glycemic variability indicators (CV, GMI, LBGI, HBGI), "
    "and retrospective forecast evaluations are descriptive and intended solely for research observation and "
    "retrospective review. They do not constitute diagnostic, prescriptive, or clinical safety claims."
)

def resolve_time_window(
    db: Session,
    patient_id: str,
    period: str = "14d",
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Resolves start_time and end_time for a query window.
    If period is 'all', returns (start_time, end_time) without constraint.
    If explicit start_time and end_time are provided, they take precedence.
    If period is '24h', '7d', '14d', '30d', anchors to the patient's latest recorded reading
    (or current UTC time if no readings exist or if explicit end_time is given).
    """
    if start_time is not None and end_time is not None:
        return start_time, end_time

    if period == "all":
        return start_time, end_time

    # Determine reference end time
    if end_time is not None:
        ref_end = end_time
    else:
        # Check latest CGM reading for patient to anchor historical records
        latest_cgm = db.query(func.max(CGMReading.timestamp)).filter(
            CGMReading.patient_id == patient_id
        ).scalar()
        if latest_cgm is not None:
            ref_end = latest_cgm
        else:
            ref_end = datetime.now(timezone.utc).replace(tzinfo=None)

    # Compute duration delta
    period_deltas = {
        "24h": timedelta(hours=24),
        "today": timedelta(hours=24),
        "7d": timedelta(days=7),
        "14d": timedelta(days=14),
        "30d": timedelta(days=30),
    }
    delta = period_deltas.get(period, timedelta(days=14))
    computed_start = start_time if start_time is not None else (ref_end - delta)
    return computed_start, ref_end


def compute_glycemic_metrics(glucose_readings: List[CGMReading]) -> Tuple[GlycemicVariability, GlycemicBands, HypoHyperEpisodes]:
    """
    Computes standard consensus glycemic variability indices, time-in-range distributions,
    and contiguous hypo/hyper episode metrics.
    """
    if not glucose_readings:
        return (
            GlycemicVariability(),
            GlycemicBands(),
            HypoHyperEpisodes()
        )

    g_vals = np.array([r.cgm_glucose for r in glucose_readings], dtype=float)
    n = len(g_vals)

    # 1. Glycemic Variability
    mean_g = float(np.mean(g_vals))
    median_g = float(np.median(g_vals))
    min_g = float(np.min(g_vals))
    max_g = float(np.max(g_vals))
    std_g = float(np.std(g_vals, ddof=1)) if n > 1 else 0.0
    cv_pct = float(round((std_g / mean_g) * 100.0, 2)) if mean_g > 0 else 0.0

    # Glucose Management Indicator (GMI) - Bergenstal et al. 2018
    # Formula: GMI (%) = 3.31 + 0.02392 * mean_glucose (mg/dL)
    gmi_pct = float(round(3.31 + 0.02392 * mean_g, 2))

    # Low and High Blood Glucose Index (LBGI, HBGI) - Kovatchev et al.
    g_clipped = np.clip(g_vals, 20.0, 600.0)
    f_g = 1.509 * ((np.log(g_clipped) ** 1.084) - 5.381)
    r_g = 10.0 * (f_g ** 2)
    rl = np.where(f_g < 0, r_g, 0.0)
    rh = np.where(f_g > 0, r_g, 0.0)
    lbgi = float(round(float(np.mean(rl)), 2))
    hbgi = float(round(float(np.mean(rh)), 2))

    variability = GlycemicVariability(
        mean_glucose=round(mean_g, 1),
        median_glucose=round(median_g, 1),
        std_glucose=round(std_g, 1),
        cv_pct=cv_pct,
        min_glucose=round(min_g, 1),
        max_glucose=round(max_g, 1),
        gmi_pct=gmi_pct,
        lbgi=lbgi,
        hbgi=hbgi
    )

    # 2. Glycemic Bands (Consensus Standard)
    # TIR: 70 - 180 mg/dL
    # TITR: 70 - 140 mg/dL
    # TBR L1: 54 - 69 mg/dL
    # TBR L2: < 54 mg/dL
    # TAR L1: 181 - 250 mg/dL
    # TAR L2: > 250 mg/dL
    tir_count = int(np.sum((g_vals >= 70.0) & (g_vals <= 180.0)))
    titr_count = int(np.sum((g_vals >= 70.0) & (g_vals <= 140.0)))
    tbr_l1_count = int(np.sum((g_vals >= 54.0) & (g_vals < 70.0)))
    tbr_l2_count = int(np.sum(g_vals < 54.0))
    tar_l1_count = int(np.sum((g_vals > 180.0) & (g_vals <= 250.0)))
    tar_l2_count = int(np.sum(g_vals > 250.0))

    bands = GlycemicBands(
        tir_pct=round((tir_count / n) * 100.0, 2),
        tir_minutes=tir_count * 15,
        titr_pct=round((titr_count / n) * 100.0, 2),
        titr_minutes=titr_count * 15,
        tbr_l1_pct=round((tbr_l1_count / n) * 100.0, 2),
        tbr_l1_minutes=tbr_l1_count * 15,
        tbr_l2_pct=round((tbr_l2_count / n) * 100.0, 2),
        tbr_l2_minutes=tbr_l2_count * 15,
        tar_l1_pct=round((tar_l1_count / n) * 100.0, 2),
        tar_l1_minutes=tar_l1_count * 15,
        tar_l2_pct=round((tar_l2_count / n) * 100.0, 2),
        tar_l2_minutes=tar_l2_count * 15,
    )

    # 3. Contiguous Hypo / Hyper Episodes
    # Sorted chronologically
    sorted_readings = sorted(glucose_readings, key=lambda r: r.timestamp)
    hypo_episodes = 0
    severe_hypo_episodes = 0
    hyper_episodes = 0

    hypo_durations = []
    hyper_durations = []

    in_hypo = False
    cur_hypo_len = 0
    in_severe_hypo = False
    in_hyper = False
    cur_hyper_len = 0

    for r in sorted_readings:
        val = r.cgm_glucose

        # Hypo check (< 70 mg/dL)
        if val < 70.0:
            if not in_hypo:
                in_hypo = True
                hypo_episodes += 1
                cur_hypo_len = 1
            else:
                cur_hypo_len += 1

            if val < 54.0:
                if not in_severe_hypo:
                    in_severe_hypo = True
                    severe_hypo_episodes += 1
            else:
                in_severe_hypo = False
        else:
            if in_hypo:
                hypo_durations.append(cur_hypo_len * 15)
                in_hypo = False
                cur_hypo_len = 0
            in_severe_hypo = False

        # Hyper check (> 180 mg/dL)
        if val > 180.0:
            if not in_hyper:
                in_hyper = True
                hyper_episodes += 1
                cur_hyper_len = 1
            else:
                cur_hyper_len += 1
        else:
            if in_hyper:
                hyper_durations.append(cur_hyper_len * 15)
                in_hyper = False
                cur_hyper_len = 0

    if in_hypo:
        hypo_durations.append(cur_hypo_len * 15)
    if in_hyper:
        hyper_durations.append(cur_hyper_len * 15)

    mean_hypo_dur = float(round(float(np.mean(hypo_durations)), 1)) if hypo_durations else 0.0
    mean_hyper_dur = float(round(float(np.mean(hyper_durations)), 1)) if hyper_durations else 0.0

    episodes = HypoHyperEpisodes(
        hypo_episode_count=hypo_episodes,
        severe_hypo_episode_count=severe_hypo_episodes,
        hyper_episode_count=hyper_episodes,
        mean_hypo_duration_minutes=mean_hypo_dur,
        mean_hyper_duration_minutes=mean_hyper_dur
    )

    return variability, bands, episodes


def get_patient_glucose_analytics(
    db: Session,
    patient_id: str,
    period: str = "14d",
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    include_readings: bool = True
) -> GlucoseAnalyticsResponse:
    """
    Retrieves longitudinal glucose analytics, glycemic variability, and standard bands.
    """
    w_start, w_end = resolve_time_window(db, patient_id, period, start_time, end_time)

    q = db.query(CGMReading).filter(CGMReading.patient_id == patient_id)
    if w_start:
        q = q.filter(CGMReading.timestamp >= w_start)
    if w_end:
        q = q.filter(CGMReading.timestamp <= w_end)

    readings = q.order_by(asc(CGMReading.timestamp)).all()
    has_data = len(readings) > 0
    total_readings = len(readings)
    days_of_data = round(total_readings / 96.0, 2) if total_readings > 0 else 0.0

    variability, bands, episodes = compute_glycemic_metrics(readings)

    time_series = []
    if include_readings and has_data:
        # Downsample if too large for direct chart response (> 2000 points)
        step = 1 if len(readings) <= 2000 else int(np.ceil(len(readings) / 2000.0))
        for r in readings[::step]:
            time_series.append(GlucoseTimeSeriesPoint(
                timestamp=r.timestamp,
                cgm_glucose=round(r.cgm_glucose, 1),
                insulin_bolus=round(r.insulin_bolus, 2),
                insulin_basal=round(r.insulin_basal, 2),
                meal_carbs=round(r.meal_carbs, 1)
            ))

    return GlucoseAnalyticsResponse(
        patient_id=patient_id,
        period=period,
        start_time=w_start,
        end_time=w_end,
        has_data=has_data,
        total_readings=total_readings,
        days_of_data=days_of_data,
        glycemic_variability=variability,
        glycemic_bands=bands,
        episodes=episodes,
        glucose_readings=time_series,
        research_disclaimer=RESEARCH_DISCLAIMER
    )


def get_patient_diurnal_profile(
    db: Session,
    patient_id: str,
    period: str = "14d",
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
) -> DiurnalAnalyticsResponse:
    """
    Computes 24-hour diurnal AGP profile and 4-quadrant circadian glucose statistics.
    """
    w_start, w_end = resolve_time_window(db, patient_id, period, start_time, end_time)

    q = db.query(CGMReading).filter(CGMReading.patient_id == patient_id)
    if w_start:
        q = q.filter(CGMReading.timestamp >= w_start)
    if w_end:
        q = q.filter(CGMReading.timestamp <= w_end)

    readings = q.all()
    has_data = len(readings) > 0

    # Hourly buckets [0 .. 23]
    hourly_buckets: Dict[int, List[float]] = {h: [] for h in range(24)}
    # Quadrant buckets
    # Night: 00-05:59, Morning: 06-11:59, Afternoon: 12-17:59, Evening: 18-23:59
    quadrant_buckets: Dict[str, List[float]] = {
        "Night (00:00 - 06:00)": [],
        "Morning (06:00 - 12:00)": [],
        "Afternoon (12:00 - 18:00)": [],
        "Evening (18:00 - 24:00)": []
    }

    for r in readings:
        val = r.cgm_glucose
        hour = r.timestamp.hour
        hourly_buckets[hour].append(val)

        if 0 <= hour < 6:
            quadrant_buckets["Night (00:00 - 06:00)"].append(val)
        elif 6 <= hour < 12:
            quadrant_buckets["Morning (06:00 - 12:00)"].append(val)
        elif 12 <= hour < 18:
            quadrant_buckets["Afternoon (12:00 - 18:00)"].append(val)
        else:
            quadrant_buckets["Evening (18:00 - 24:00)"].append(val)

    hourly_agp = []
    for h in range(24):
        vals = hourly_buckets[h]
        if vals:
            v_arr = np.array(vals)
            hourly_agp.append(HourlyDiurnalPoint(
                hour=h,
                reading_count=len(vals),
                mean_glucose=round(float(np.mean(v_arr)), 1),
                median_glucose=round(float(np.median(v_arr)), 1),
                p10=round(float(np.percentile(v_arr, 10)), 1),
                p25=round(float(np.percentile(v_arr, 25)), 1),
                p75=round(float(np.percentile(v_arr, 75)), 1),
                p90=round(float(np.percentile(v_arr, 90)), 1)
            ))
        else:
            hourly_agp.append(HourlyDiurnalPoint(hour=h, reading_count=0))

    quadrant_profiles = []
    for q_name, vals in quadrant_buckets.items():
        if vals:
            v_arr = np.array(vals)
            cnt = len(v_arr)
            mean_v = float(np.mean(v_arr))
            std_v = float(np.std(v_arr, ddof=1)) if cnt > 1 else 0.0
            cv_v = round((std_v / mean_v) * 100.0, 2) if mean_v > 0 else 0.0
            tir_cnt = int(np.sum((v_arr >= 70.0) & (v_arr <= 180.0)))
            tbr_cnt = int(np.sum(v_arr < 70.0))
            tar_cnt = int(np.sum(v_arr > 180.0))

            quadrant_profiles.append(QuadrantProfile(
                quadrant=q_name.split(" ")[0],
                hours=q_name.split(" ")[1].replace("(", "").replace(")", ""),
                reading_count=cnt,
                mean_glucose=round(mean_v, 1),
                std_glucose=round(std_v, 1),
                cv_pct=cv_v,
                tir_pct=round((tir_cnt / cnt) * 100.0, 2),
                tbr_pct=round((tbr_cnt / cnt) * 100.0, 2),
                tar_pct=round((tar_cnt / cnt) * 100.0, 2)
            ))
        else:
            quadrant_profiles.append(QuadrantProfile(
                quadrant=q_name.split(" ")[0],
                hours=q_name.split(" ")[1].replace("(", "").replace(")", ""),
                reading_count=0
            ))

    return DiurnalAnalyticsResponse(
        patient_id=patient_id,
        period=period,
        has_data=has_data,
        quadrants=quadrant_profiles,
        hourly_agp=hourly_agp,
        research_disclaimer=RESEARCH_DISCLAIMER
    )


def get_patient_forecast_performance(
    db: Session,
    patient_id: str,
    period: str = "14d",
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
) -> ForecastPerformanceResponse:
    """
    Evaluates historical forecast accuracy by joining past ForecastRecords
    with actual ground truth CGMReadings at matching future horizons (T0 + 15m .. T0 + 300m).
    Computes MAE, RMSE, Mean Bias Error, and empirical 80%/95% interval coverage.
    """
    w_start, w_end = resolve_time_window(db, patient_id, period, start_time, end_time)

    q = db.query(ForecastRecord).filter(ForecastRecord.patient_id == patient_id)
    if w_start:
        q = q.filter(ForecastRecord.timestamp >= w_start)
    if w_end:
        q = q.filter(ForecastRecord.timestamp <= w_end)

    forecast_records = q.order_by(asc(ForecastRecord.timestamp)).all()
    total_forecasts = len(forecast_records)

    if total_forecasts == 0:
        return ForecastPerformanceResponse(
            patient_id=patient_id,
            period=period,
            has_data=False,
            total_forecasts_logged=0,
            evaluated_pairs_count=0,
            pending_evaluation_count=0,
            horizon_metrics=[],
            daily_trends=[],
            research_disclaimer=RESEARCH_DISCLAIMER
        )

    # Pre-fetch CGM readings in relevant timeframe to avoid N+1 DB queries
    min_t = min(f.timestamp for f in forecast_records)
    max_t = max(f.timestamp for f in forecast_records) + timedelta(minutes=315)

    cgm_list = db.query(CGMReading).filter(
        CGMReading.patient_id == patient_id,
        CGMReading.timestamp >= min_t,
        CGMReading.timestamp <= max_t
    ).order_by(asc(CGMReading.timestamp)).all()

    # Index CGM readings by timestamp rounded to nearest minute or store in sorted array
    cgm_times = [r.timestamp for r in cgm_list]
    cgm_vals = np.array([r.cgm_glucose for r in cgm_list], dtype=float)

    # Horizon trackers: step 1..20
    horizon_errors: Dict[int, List[float]] = {step: [] for step in range(1, 21)}
    horizon_ae: Dict[int, List[float]] = {step: [] for step in range(1, 21)}
    horizon_se: Dict[int, List[float]] = {step: [] for step in range(1, 21)}
    horizon_cov_80: Dict[int, List[bool]] = {step: [] for step in range(1, 21)}
    horizon_cov_95: Dict[int, List[bool]] = {step: [] for step in range(1, 21)}
    horizon_w_80: Dict[int, List[float]] = {step: [] for step in range(1, 21)}
    horizon_w_95: Dict[int, List[float]] = {step: [] for step in range(1, 21)}

    daily_eval: Dict[str, Dict[str, List[float]]] = {}

    all_errors = []
    all_ae = []
    all_se = []
    all_cov_80 = []
    all_cov_95 = []
    all_w_80 = []
    all_w_95 = []
    pending_count = 0
    evaluated_pairs_count = 0

    tol = timedelta(minutes=7, seconds=30)

    for fc in forecast_records:
        t0 = fc.timestamp
        date_str = t0.strftime("%Y-%m-%d")
        if date_str not in daily_eval:
            daily_eval[date_str] = {"ae": [], "se": []}

        pt_forecast = fc.point_forecast or []
        l_80 = fc.lower_80 or []
        u_80 = fc.upper_80 or []
        l_95 = fc.lower_95 or []
        u_95 = fc.upper_95 or []

        for step in range(1, 21):
            if step - 1 >= len(pt_forecast):
                continue
            pred_val = pt_forecast[step - 1]
            target_time = t0 + timedelta(minutes=step * 15)

            # Search matching CGM reading within target_time +- tol
            match_idx = None
            for idx, c_time in enumerate(cgm_times):
                if abs(c_time - target_time) <= tol:
                    match_idx = idx
                    break

            if match_idx is not None:
                actual_val = cgm_vals[match_idx]
                err = pred_val - actual_val
                ae = abs(err)
                se = err ** 2

                horizon_errors[step].append(err)
                horizon_ae[step].append(ae)
                horizon_se[step].append(se)

                all_errors.append(err)
                all_ae.append(ae)
                all_se.append(se)
                daily_eval[date_str]["ae"].append(ae)
                daily_eval[date_str]["se"].append(se)

                # Coverage checks
                if step - 1 < len(l_80) and step - 1 < len(u_80):
                    in_80 = (l_80[step - 1] <= actual_val <= u_80[step - 1])
                    w80 = max(0.0, u_80[step - 1] - l_80[step - 1])
                    horizon_cov_80[step].append(in_80)
                    horizon_w_80[step].append(w80)
                    all_cov_80.append(in_80)
                    all_w_80.append(w80)

                if step - 1 < len(l_95) and step - 1 < len(u_95):
                    in_95 = (l_95[step - 1] <= actual_val <= u_95[step - 1])
                    w95 = max(0.0, u_95[step - 1] - l_95[step - 1])
                    horizon_cov_95[step].append(in_95)
                    horizon_w_95[step].append(w95)
                    all_cov_95.append(in_95)
                    all_w_95.append(w95)

                evaluated_pairs_count += 1
            else:
                pending_count += 1

    # Horizon breakdown metrics
    horizon_metrics = []
    for step in range(1, 21):
        aes = horizon_ae[step]
        ses = horizon_se[step]
        errs = horizon_errors[step]
        c80 = horizon_cov_80[step]
        c95 = horizon_cov_95[step]
        w80 = horizon_w_80[step]
        w95 = horizon_w_95[step]

        if aes:
            horizon_metrics.append(HorizonErrorMetric(
                horizon_step=step,
                horizon_minutes=step * 15,
                sample_count=len(aes),
                mae_mg_dl=round(float(np.mean(aes)), 2),
                rmse_mg_dl=round(float(np.sqrt(np.mean(ses))), 2),
                bias_mg_dl=round(float(np.mean(errs)), 2),
                coverage_80_pct=round(float(np.mean(c80) * 100.0), 2) if c80 else None,
                coverage_95_pct=round(float(np.mean(c95) * 100.0), 2) if c95 else None,
                mean_width_80_mg_dl=round(float(np.mean(w80)), 1) if w80 else None,
                mean_width_95_mg_dl=round(float(np.mean(w95)), 1) if w95 else None,
            ))
        else:
            horizon_metrics.append(HorizonErrorMetric(
                horizon_step=step,
                horizon_minutes=step * 15,
                sample_count=0
            ))

    daily_trends = []
    for d_str, metrics in sorted(daily_eval.items()):
        if metrics["ae"]:
            daily_trends.append({
                "date": d_str,
                "evaluated_points": len(metrics["ae"]),
                "mae_mg_dl": round(float(np.mean(metrics["ae"])), 2),
                "rmse_mg_dl": round(float(np.sqrt(np.mean(metrics["se"]))), 2)
            })

    has_eval_data = len(all_ae) > 0

    return ForecastPerformanceResponse(
        patient_id=patient_id,
        period=period,
        has_data=has_eval_data,
        total_forecasts_logged=total_forecasts,
        evaluated_pairs_count=evaluated_pairs_count,
        pending_evaluation_count=pending_count,
        overall_mae_mg_dl=round(float(np.mean(all_ae)), 2) if has_eval_data else None,
        overall_rmse_mg_dl=round(float(np.sqrt(np.mean(all_se))), 2) if has_eval_data else None,
        overall_bias_mg_dl=round(float(np.mean(all_errors)), 2) if has_eval_data else None,
        overall_coverage_80_pct=round(float(np.mean(all_cov_80) * 100.0), 2) if all_cov_80 else None,
        overall_coverage_95_pct=round(float(np.mean(all_cov_95) * 100.0), 2) if all_cov_95 else None,
        overall_mean_width_80_mg_dl=round(float(np.mean(all_w_80)), 1) if all_w_80 else None,
        overall_mean_width_95_mg_dl=round(float(np.mean(all_w_95)), 1) if all_w_95 else None,
        horizon_metrics=horizon_metrics,
        daily_trends=daily_trends,
        research_disclaimer=RESEARCH_DISCLAIMER
    )


def get_patient_risk_analytics(
    db: Session,
    patient_id: str,
    period: str = "14d",
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
) -> RiskFactorsResponse:
    """
    Computes longitudinal clinical risk alert distribution, context factors (IOB, COB at alert time),
    nutrition totals, and wearable correlations.
    """
    w_start, w_end = resolve_time_window(db, patient_id, period, start_time, end_time)

    # 1. Decisions & Alerts
    dq = db.query(DecisionRecord).filter(DecisionRecord.patient_id == patient_id)
    if w_start:
        dq = dq.filter(DecisionRecord.timestamp >= w_start)
    if w_end:
        dq = dq.filter(DecisionRecord.timestamp <= w_end)
    decisions = dq.all()

    alert_counts = {"NORMAL": 0, "WARNING_HYPO": 0, "CRITICAL_HYPO": 0, "WARNING_HYPER": 0, "CRITICAL_HYPER": 0}
    for d in decisions:
        status = d.alert_status or "NORMAL"
        alert_counts[status] = alert_counts.get(status, 0) + 1

    # 2. Forecasts at alert times to get IOB/COB context
    fq = db.query(ForecastRecord).filter(ForecastRecord.patient_id == patient_id)
    if w_start:
        fq = fq.filter(ForecastRecord.timestamp >= w_start)
    if w_end:
        fq = fq.filter(ForecastRecord.timestamp <= w_end)
    forecasts = fq.all()

    alert_iobs = []
    alert_cobs = []
    for f in forecasts:
        risk = f.risk_assessment or {}
        alert_level = risk.get("alert_level", "NORMAL")
        if alert_level != "NORMAL":
            if f.current_iob is not None:
                alert_iobs.append(f.current_iob)
            if f.current_cob is not None:
                alert_cobs.append(f.current_cob)

    mean_iob = round(float(np.mean(alert_iobs)), 2) if alert_iobs else None
    mean_cob = round(float(np.mean(alert_cobs)), 1) if alert_cobs else None

    # 3. Nutrition Totals
    mq = db.query(MealRecord).filter(MealRecord.patient_id == patient_id)
    if w_start:
        mq = mq.filter(MealRecord.timestamp >= w_start)
    if w_end:
        mq = mq.filter(MealRecord.timestamp <= w_end)
    meals = mq.all()

    total_carbs = sum(m.carbs_g for m in meals if m.carbs_g is not None)
    total_calories = sum(m.calories_kcal for m in meals if m.calories_kcal is not None)
    meal_count = len(meals)

    # 4. Insulin Totals
    iq = db.query(InsulinRecord).filter(InsulinRecord.patient_id == patient_id)
    if w_start:
        iq = iq.filter(InsulinRecord.timestamp >= w_start)
    if w_end:
        iq = iq.filter(InsulinRecord.timestamp <= w_end)
    insulins = iq.all()

    bolus_units = sum(i.units for i in insulins if i.dose_type == "bolus" and i.units is not None)
    basal_units = sum(i.units for i in insulins if i.dose_type == "basal" and i.units is not None)
    total_dose = bolus_units + basal_units

    # Days in window
    if w_start and w_end:
        days_span = max(1.0, (w_end - w_start).total_seconds() / 86400.0)
    else:
        days_span = 14.0

    nutrition_totals = {
        "meal_count": meal_count,
        "total_carbs_g": round(total_carbs, 1),
        "mean_daily_carbs_g": round(total_carbs / days_span, 1),
        "total_calories_kcal": round(total_calories, 1),
        "mean_daily_bolus_units": round(bolus_units / days_span, 2),
        "mean_daily_basal_units": round(basal_units / days_span, 2),
        "total_daily_dose_tdd": round(total_dose / days_span, 2),
        "bolus_basal_ratio": round(bolus_units / basal_units, 2) if basal_units > 0 else None
    }

    # 5. Wearable telemetry
    wq = db.query(WearableObservation).filter(WearableObservation.patient_id == patient_id)
    if w_start:
        wq = wq.filter(WearableObservation.timestamp >= w_start)
    if w_end:
        wq = wq.filter(WearableObservation.timestamp <= w_end)
    wearables = wq.all()

    steps_list = [w.step_count for w in wearables if w.step_count is not None]
    hr_list = [w.heart_rate_bpm for w in wearables if w.heart_rate_bpm is not None]

    wearable_trends = {
        "observation_count": len(wearables),
        "mean_daily_steps": round(sum(steps_list) / days_span, 0) if steps_list else None,
        "mean_heart_rate_bpm": round(float(np.mean(hr_list)), 1) if hr_list else None
    }

    has_data = (len(decisions) > 0 or len(forecasts) > 0 or len(meals) > 0 or len(insulins) > 0)

    return RiskFactorsResponse(
        patient_id=patient_id,
        period=period,
        has_data=has_data,
        total_alerts=len(decisions),
        alert_counts=alert_counts,
        mean_iob_at_alert=mean_iob,
        mean_cob_at_alert=mean_cob,
        nutrition_totals=nutrition_totals,
        wearable_trends=wearable_trends,
        research_disclaimer=RESEARCH_DISCLAIMER
    )


def get_patient_timeline(
    db: Session,
    patient_id: str,
    limit: int = 50,
    offset: int = 0,
    event_type: Optional[str] = None,
    period: str = "14d",
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
) -> TimelineResponse:
    """
    Retrieves a unified, paginated, chronological stream of all patient events:
    CGM readings, meal logs, insulin dosing, forecasts, decision alerts, and wearable syncs.
    """
    w_start, w_end = resolve_time_window(db, patient_id, period, start_time, end_time)

    events: List[TimelineItem] = []

    # 1. CGM Readings
    if event_type in [None, "cgm"]:
        cq = db.query(CGMReading).filter(CGMReading.patient_id == patient_id)
        if w_start:
            cq = cq.filter(CGMReading.timestamp >= w_start)
        if w_end:
            cq = cq.filter(CGMReading.timestamp <= w_end)
        # Fetch latest CGM readings
        for r in cq.order_by(desc(CGMReading.timestamp)).limit(limit + offset).all():
            g = r.cgm_glucose
            if g < 54.0:
                sev = "critical"
            elif g < 70.0 or g > 250.0:
                sev = "warning"
            else:
                sev = "normal"

            events.append(TimelineItem(
                id=f"cgm_{r.id}",
                timestamp=r.timestamp,
                event_type="cgm",
                title="CGM Glucose Reading",
                primary_value=f"{g:.1f} mg/dL",
                secondary_value=f"Carbs: {r.meal_carbs}g, Bolus: {r.insulin_bolus}U",
                severity=sev,
                metadata={"glucose": g, "bolus": r.insulin_bolus, "carbs": r.meal_carbs}
            ))

    # 2. Meal Records
    if event_type in [None, "meal"]:
        mq = db.query(MealRecord).filter(MealRecord.patient_id == patient_id)
        if w_start:
            mq = mq.filter(MealRecord.timestamp >= w_start)
        if w_end:
            mq = mq.filter(MealRecord.timestamp <= w_end)
        for m in mq.order_by(desc(MealRecord.timestamp)).limit(limit + offset).all():
            cal_txt = f"{m.calories_kcal:.0f} kcal" if m.calories_kcal else "Cal unlogged"
            events.append(TimelineItem(
                id=f"meal_{m.id}",
                timestamp=m.timestamp,
                event_type="meal",
                title=f"Meal: {m.meal_name}",
                primary_value=f"{m.carbs_g:.1f}g Carbs",
                secondary_value=f"{cal_txt} ({m.source})",
                severity="info",
                metadata={"carbs": m.carbs_g, "calories": m.calories_kcal, "source": m.source}
            ))

    # 3. Insulin Records
    if event_type in [None, "insulin"]:
        iq = db.query(InsulinRecord).filter(InsulinRecord.patient_id == patient_id)
        if w_start:
            iq = iq.filter(InsulinRecord.timestamp >= w_start)
        if w_end:
            iq = iq.filter(InsulinRecord.timestamp <= w_end)
        for ins in iq.order_by(desc(InsulinRecord.timestamp)).limit(limit + offset).all():
            events.append(TimelineItem(
                id=f"ins_{ins.id}",
                timestamp=ins.timestamp,
                event_type="insulin",
                title=f"Insulin {ins.dose_type.capitalize()}",
                primary_value=f"{ins.units:.1f} Units",
                secondary_value=ins.insulin_type or "Insulin",
                severity="info",
                metadata={"units": ins.units, "dose_type": ins.dose_type}
            ))

    # 4. Forecast Records
    if event_type in [None, "forecast"]:
        fq = db.query(ForecastRecord).filter(ForecastRecord.patient_id == patient_id)
        if w_start:
            fq = fq.filter(ForecastRecord.timestamp >= w_start)
        if w_end:
            fq = fq.filter(ForecastRecord.timestamp <= w_end)
        for fc in fq.order_by(desc(ForecastRecord.timestamp)).limit(limit + offset).all():
            risk = fc.risk_assessment or {}
            alert_lvl = risk.get("alert_level", "NORMAL")
            sev = "critical" if "CRITICAL" in alert_lvl else ("warning" if "WARNING" in alert_lvl else "normal")
            pts = fc.point_forecast or []
            nadir = min(pts) if pts else fc.current_glucose
            peak = max(pts) if pts else fc.current_glucose
            events.append(TimelineItem(
                id=f"fc_{fc.id}",
                timestamp=fc.timestamp,
                event_type="forecast",
                title="5-Hour Forecast Generated",
                primary_value=f"{fc.current_glucose:.1f} mg/dL (Now)",
                secondary_value=f"5h Nadir: {nadir:.1f} / Peak: {peak:.1f} mg/dL",
                severity=sev,
                metadata={"current_glucose": fc.current_glucose, "alert_level": alert_lvl}
            ))

    # 5. Decision Records
    if event_type in [None, "decision"]:
        dq = db.query(DecisionRecord).filter(DecisionRecord.patient_id == patient_id)
        if w_start:
            dq = dq.filter(DecisionRecord.timestamp >= w_start)
        if w_end:
            dq = dq.filter(DecisionRecord.timestamp <= w_end)
        for dec in dq.order_by(desc(DecisionRecord.timestamp)).limit(limit + offset).all():
            sev = "critical" if "CRITICAL" in dec.alert_status else ("warning" if "WARNING" in dec.alert_status else "normal")
            events.append(TimelineItem(
                id=f"dec_{dec.id}",
                timestamp=dec.timestamp,
                event_type="decision",
                title="Decision Synthesis",
                primary_value=dec.alert_status,
                secondary_value=dec.recommended_action,
                severity=sev,
                metadata={"alert_status": dec.alert_status, "action": dec.recommended_action}
            ))

    # 6. Wearable Observations
    if event_type in [None, "wearable"]:
        wq = db.query(WearableObservation).filter(WearableObservation.patient_id == patient_id)
        if w_start:
            wq = wq.filter(WearableObservation.timestamp >= w_start)
        if w_end:
            wq = wq.filter(WearableObservation.timestamp <= w_end)
        for wear in wq.order_by(desc(WearableObservation.timestamp)).limit(limit + offset).all():
            steps = f"{wear.step_count:.0f} steps" if wear.step_count is not None else "No steps"
            hr = f"{wear.heart_rate_bpm:.0f} bpm" if wear.heart_rate_bpm is not None else ""
            events.append(TimelineItem(
                id=f"wear_{wear.id}",
                timestamp=wear.timestamp,
                event_type="wearable",
                title="Wearable Telemetry Sync",
                primary_value=steps,
                secondary_value=hr,
                severity="info",
                metadata={"steps": wear.step_count, "heart_rate": wear.heart_rate_bpm}
            ))

    # Sort all events chronologically descending
    events.sort(key=lambda e: e.timestamp, reverse=True)
    total_events = len(events)
    paginated_events = events[offset:offset + limit]

    return TimelineResponse(
        patient_id=patient_id,
        period=period,
        total_events=total_events,
        limit=limit,
        offset=offset,
        events=paginated_events,
        research_disclaimer=RESEARCH_DISCLAIMER
    )


def get_patient_analytics_summary(
    db: Session,
    patient_id: str,
    period: str = "14d",
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
) -> AnalyticsSummaryResponse:
    """
    Computes an executive longitudinal analytics summary combining glucose variability,
    time-in-range distributions, hypo/hyper episodes, daily factor averages, and forecast evaluation.
    """
    w_start, w_end = resolve_time_window(db, patient_id, period, start_time, end_time)

    # 1. Glucose summary
    glucose_resp = get_patient_glucose_analytics(
        db, patient_id, period, w_start, w_end, include_readings=False
    )

    # 2. Risk & factor summary
    risk_resp = get_patient_risk_analytics(db, patient_id, period, w_start, w_end)

    # 3. Forecast evaluation summary
    fc_resp = get_patient_forecast_performance(db, patient_id, period, w_start, w_end)
    fc_eval_summary = None
    if fc_resp.has_data:
        fc_eval_summary = {
            "evaluated_pairs_count": fc_resp.evaluated_pairs_count,
            "overall_mae_mg_dl": fc_resp.overall_mae_mg_dl,
            "overall_rmse_mg_dl": fc_resp.overall_rmse_mg_dl,
            "overall_bias_mg_dl": fc_resp.overall_bias_mg_dl,
            "coverage_80_pct": fc_resp.overall_coverage_80_pct,
            "coverage_95_pct": fc_resp.overall_coverage_95_pct,
        }

    return AnalyticsSummaryResponse(
        patient_id=patient_id,
        period=period,
        start_time=w_start,
        end_time=w_end,
        has_data=glucose_resp.has_data,
        total_readings=glucose_resp.total_readings,
        days_of_data=glucose_resp.days_of_data,
        glycemic_variability=glucose_resp.glycemic_variability,
        glycemic_bands=glucose_resp.glycemic_bands,
        episodes=glucose_resp.episodes,
        daily_metrics=risk_resp.nutrition_totals,
        forecast_eval_summary=fc_eval_summary,
        research_disclaimer=RESEARCH_DISCLAIMER
    )
