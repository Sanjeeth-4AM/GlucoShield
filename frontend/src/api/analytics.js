/**
 * GlucoShield Phase 14 — Longitudinal Analytics API Client
 */

const API_BASE = "";

export async function apiGetAnalyticsSummary(token, patientId, period = "14d") {
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  const res = await fetch(`${API_BASE}/api/v1/patients/${patientId}/analytics/summary?period=${period}`, {
    headers
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch analytics summary (${res.status})`);
  }
  return await res.json();
}

export async function apiGetGlucoseAnalytics(token, patientId, period = "14d") {
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  const res = await fetch(`${API_BASE}/api/v1/patients/${patientId}/analytics/glucose?period=${period}`, {
    headers
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch glucose analytics (${res.status})`);
  }
  return await res.json();
}

export async function apiGetDiurnalAnalytics(token, patientId, period = "14d") {
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  const res = await fetch(`${API_BASE}/api/v1/patients/${patientId}/analytics/diurnal?period=${period}`, {
    headers
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch diurnal analytics (${res.status})`);
  }
  return await res.json();
}

export async function apiGetForecastPerformance(token, patientId, period = "14d") {
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  const res = await fetch(`${API_BASE}/api/v1/patients/${patientId}/analytics/forecast-performance?period=${period}`, {
    headers
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch forecast performance (${res.status})`);
  }
  return await res.json();
}

export async function apiGetRiskFactors(token, patientId, period = "14d") {
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  const res = await fetch(`${API_BASE}/api/v1/patients/${patientId}/analytics/risk-factors?period=${period}`, {
    headers
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch risk factors (${res.status})`);
  }
  return await res.json();
}

export async function apiGetTimeline(token, patientId, limit = 50, offset = 0, eventType = null, period = "14d") {
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  let url = `${API_BASE}/api/v1/patients/${patientId}/analytics/timeline?limit=${limit}&offset=${offset}&period=${period}`;
  if (eventType) {
    url += `&event_type=${eventType}`;
  }
  const res = await fetch(url, { headers });
  if (!res.ok) {
    throw new Error(`Failed to fetch timeline (${res.status})`);
  }
  return await res.json();
}

/**
 * Generates synthetic mock analytics data when in offline or demo mode
 */
export function generateDemoAnalytics(period = "14d") {
  return {
    summary: {
      has_data: true,
      total_readings: 1344,
      days_of_data: 14.0,
      glycemic_variability: {
        mean_glucose: 128.4,
        median_glucose: 124.0,
        std_glucose: 28.6,
        cv_pct: 22.3,
        min_glucose: 58.0,
        max_glucose: 242.0,
        gmi_pct: 6.38,
        lbgi: 1.45,
        hbgi: 3.82
      },
      glycemic_bands: {
        tir_pct: 78.5,
        tir_minutes: 15840,
        titr_pct: 58.2,
        titr_minutes: 11730,
        tbr_l1_pct: 2.8,
        tbr_l1_minutes: 570,
        tbr_l2_pct: 0.7,
        tbr_l2_minutes: 135,
        tar_l1_pct: 15.2,
        tar_l1_minutes: 3060,
        tar_l2_pct: 2.8,
        tar_l2_minutes: 570
      },
      episodes: {
        hypo_episode_count: 3,
        severe_hypo_episode_count: 1,
        hyper_episode_count: 8,
        mean_hypo_duration_minutes: 35.0,
        mean_hyper_duration_minutes: 52.5
      },
      daily_metrics: {
        meal_count: 42,
        total_carbs_g: 2520.0,
        mean_daily_carbs_g: 180.0,
        total_calories_kcal: 28400.0,
        mean_daily_bolus_units: 18.5,
        mean_daily_basal_units: 22.0,
        total_daily_dose_tdd: 40.5,
        bolus_basal_ratio: 0.84
      },
      forecast_eval_summary: {
        evaluated_pairs_count: 240,
        overall_mae_mg_dl: 14.8,
        overall_rmse_mg_dl: 19.2,
        overall_bias_mg_dl: -1.4,
        coverage_80_pct: 82.5,
        coverage_95_pct: 96.1
      }
    },
    diurnal: {
      has_data: true,
      quadrants: [
        { quadrant: "Night", hours: "00:00 - 06:00", reading_count: 336, mean_glucose: 112.4, std_glucose: 18.2, cv_pct: 16.2, tir_pct: 88.4, tbr_pct: 3.1, tar_pct: 8.5 },
        { quadrant: "Morning", hours: "06:00 - 12:00", reading_count: 336, mean_glucose: 138.2, std_glucose: 34.5, cv_pct: 25.0, tir_pct: 74.2, tbr_pct: 2.4, tar_pct: 23.4 },
        { quadrant: "Afternoon", hours: "12:00 - 18:00", reading_count: 336, mean_glucose: 134.8, std_glucose: 29.1, cv_pct: 21.6, tir_pct: 77.8, tbr_pct: 1.8, tar_pct: 20.4 },
        { quadrant: "Evening", hours: "18:00 - 24:00", reading_count: 336, mean_glucose: 128.0, std_glucose: 26.3, cv_pct: 20.5, tir_pct: 81.2, tbr_pct: 3.5, tar_pct: 15.3 }
      ],
      hourly_agp: Array.from({ length: 24 }, (_, h) => {
        const base = 115 + Math.sin((h - 6) / 3.8) * 22;
        return {
          hour: h,
          reading_count: 56,
          mean_glucose: Math.round(base * 10) / 10,
          median_glucose: Math.round((base - 2) * 10) / 10,
          p10: Math.round((base - 25) * 10) / 10,
          p25: Math.round((base - 14) * 10) / 10,
          p75: Math.round((base + 16) * 10) / 10,
          p90: Math.round((base + 30) * 10) / 10
        };
      })
    },
    forecast: {
      has_data: true,
      total_forecasts_logged: 24,
      evaluated_pairs_count: 480,
      pending_evaluation_count: 0,
      overall_mae_mg_dl: 14.8,
      overall_rmse_mg_dl: 19.2,
      overall_bias_mg_dl: -1.4,
      overall_coverage_80_pct: 82.5,
      overall_coverage_95_pct: 96.1,
      overall_mean_width_80_mg_dl: 38.4,
      overall_mean_width_95_mg_dl: 68.2,
      horizon_metrics: [
        { horizon_step: 1, horizon_minutes: 15, sample_count: 24, mae_mg_dl: 5.2, rmse_mg_dl: 7.1, bias_mg_dl: -0.4, coverage_80_pct: 88.5, coverage_95_pct: 98.0, mean_width_80_mg_dl: 22.0, mean_width_95_mg_dl: 42.0 },
        { horizon_step: 2, horizon_minutes: 30, sample_count: 24, mae_mg_dl: 8.8, rmse_mg_dl: 11.4, bias_mg_dl: -0.8, coverage_80_pct: 85.0, coverage_95_pct: 97.2, mean_width_80_mg_dl: 28.0, mean_width_95_mg_dl: 52.0 },
        { horizon_step: 4, horizon_minutes: 60, sample_count: 24, mae_mg_dl: 13.5, rmse_mg_dl: 17.2, bias_mg_dl: -1.2, coverage_80_pct: 83.2, coverage_95_pct: 96.5, mean_width_80_mg_dl: 36.0, mean_width_95_mg_dl: 64.0 },
        { horizon_step: 8, horizon_minutes: 120, sample_count: 24, mae_mg_dl: 18.2, rmse_mg_dl: 23.5, bias_mg_dl: -1.6, coverage_80_pct: 81.0, coverage_95_pct: 95.8, mean_width_80_mg_dl: 46.0, mean_width_95_mg_dl: 80.0 },
        { horizon_step: 12, horizon_minutes: 180, sample_count: 24, mae_mg_dl: 21.0, rmse_mg_dl: 27.2, bias_mg_dl: -2.1, coverage_80_pct: 79.5, coverage_95_pct: 94.5, mean_width_80_mg_dl: 54.0, mean_width_95_mg_dl: 92.0 },
        { horizon_step: 20, horizon_minutes: 300, sample_count: 24, mae_mg_dl: 24.5, rmse_mg_dl: 31.8, bias_mg_dl: -2.8, coverage_80_pct: 78.0, coverage_95_pct: 93.8, mean_width_80_mg_dl: 62.0, mean_width_95_mg_dl: 104.0 },
      ]
    },
    timeline: {
      total_events: 18,
      limit: 50,
      offset: 0,
      events: [
        { id: "ev_1", timestamp: new Date(Date.now() - 15 * 60000).toISOString(), event_type: "cgm", title: "CGM Glucose Reading", primary_value: "128.0 mg/dL", secondary_value: "Carbs: 0g, Bolus: 0U", severity: "normal" },
        { id: "ev_2", timestamp: new Date(Date.now() - 45 * 60000).toISOString(), event_type: "meal", title: "Meal: Quinoa Chicken Bowl", primary_value: "52.0g Carbs", secondary_value: "540 kcal (vision)", severity: "info" },
        { id: "ev_3", timestamp: new Date(Date.now() - 40 * 60000).toISOString(), event_type: "insulin", title: "Insulin Bolus", primary_value: "4.5 Units", secondary_value: "Aspart (Novolog)", severity: "info" },
        { id: "ev_4", timestamp: new Date(Date.now() - 120 * 60000).toISOString(), event_type: "forecast", title: "5-Hour Forecast Generated", primary_value: "135.0 mg/dL (Now)", secondary_value: "5h Nadir: 112.0 / Peak: 168.0 mg/dL", severity: "normal" },
        { id: "ev_5", timestamp: new Date(Date.now() - 180 * 60000).toISOString(), event_type: "decision", title: "Decision Synthesis", primary_value: "NORMAL", secondary_value: "Routine monitoring suggested", severity: "normal" },
        { id: "ev_6", timestamp: new Date(Date.now() - 240 * 60000).toISOString(), event_type: "wearable", title: "Wearable Telemetry Sync", primary_value: "6,420 steps", secondary_value: "74 bpm", severity: "info" }
      ]
    }
  };
}
