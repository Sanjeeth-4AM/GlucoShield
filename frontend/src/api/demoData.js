/**
 * Realistic Synthetic Demo Data Scenarios for Offline & Demo Mode
 * Note: Clearly labeled as DEMO / SYNTHETIC DATA in the UI.
 */

import { RESEARCH_DISCLAIMER } from "./types.js";

export function generateSyntheticHistory(scenario = "stable") {
  const readings = [];
  const now = new Date();
  const startTime = new Date(now.getTime() - 24 * 60 * 60 * 1000);

  for (let i = 0; i < 96; i++) {
    const time = new Date(startTime.getTime() + i * 15 * 60 * 1000);
    let glucose = 120.0;
    let bolus = 0.0;
    let basal = 0.6;
    let carbs = 0.0;

    if (scenario === "stable") {
      glucose = 120 + Math.sin(i / 6.0) * 8 + Math.cos(i / 12.0) * 5;
      if (i === 32) { carbs = 40.0; bolus = 3.0; }
      if (i === 68) { carbs = 55.0; bolus = 4.2; }
    } else if (scenario === "postprandial") {
      if (i < 80) {
        glucose = 110 + Math.sin(i / 8.0) * 6;
      } else {
        const delta = i - 80;
        glucose = 110 + delta * 3.8;
      }
      if (i === 80) { carbs = 65.0; bolus = 4.5; }
    } else if (scenario === "hypo_risk") {
      if (i < 82) {
        glucose = 145 - (i / 82) * 20;
      } else {
        const delta = i - 82;
        glucose = Math.max(58.0, 125 - delta * 5.2);
      }
      if (i === 75) { bolus = 5.0; carbs = 15.0; } // Mismatched bolus
    } else if (scenario === "exercise") {
      glucose = 135 + Math.sin(i / 5.0) * 10;
      if (i === 85) { glucose = 115.0; }
    }

    readings.push({
      timestamp: time.toISOString(),
      cgm_glucose: Math.round(glucose * 10) / 10,
      insulin_bolus: bolus,
      insulin_basal: basal,
      meal_carbs: carbs
    });
  }

  return readings;
}

export const DEMO_STATIC_PROFILE = {
  age: 42.0,
  bmi: 25.8,
  hba1c: 56.0,
  glycated_albumin: 17.2,
  fasting_glucose: 124.0,
  fasting_c_peptide: 0.85,
  macrovascular_comp_count: 0.0,
  microvascular_comp_count: 0.0,
  is_t1dm: 1.0
};

export function getSyntheticForecastResponse(scenario = "stable") {
  let pointForecast = [];
  let lower80 = [];
  let upper80 = [];
  let lower95 = [];
  let upper95 = [];
  let neuralPred = [];
  let odeSim = [];
  let alpha = [];
  let riskAssessment = {};
  let explanation = {};
  let currentGlucose = 122.5;

  if (scenario === "stable") {
    currentGlucose = 122.5;
    pointForecast = [123.1, 124.0, 125.2, 126.1, 126.8, 127.0, 126.5, 125.4, 124.0, 122.3, 120.5, 118.9, 117.5, 116.4, 115.6, 115.0, 114.6, 114.4, 114.2, 114.1];
    lower80 = pointForecast.map(v => Math.round((v - 9.5) * 10) / 10);
    upper80 = pointForecast.map(v => Math.round((v + 10.2) * 10) / 10);
    lower95 = pointForecast.map(v => Math.round((v - 15.8) * 10) / 10);
    upper95 = pointForecast.map(v => Math.round((v + 17.4) * 10) / 10);
    neuralPred = pointForecast.map(v => Math.round((v + 1.2) * 10) / 10);
    odeSim = pointForecast.map(v => Math.round((v - 2.5) * 10) / 10);
    alpha = [0.85, 0.82, 0.79, 0.76, 0.74, 0.72, 0.71, 0.70, 0.69, 0.68, 0.68, 0.68, 0.69, 0.70, 0.71, 0.72, 0.73, 0.74, 0.75, 0.75];
    
    riskAssessment = {
      alert_level: "NORMAL",
      hypo_1h_prob: 0.02,
      hypo_2h_prob: 0.04,
      hypo_4h_prob: 0.06,
      hyper_2h_prob: 0.01,
      hyper_4h_prob: 0.02,
      nadir_mg_dl: 114.1,
      time_to_nadir_min: 300,
      peak_mg_dl: 127.0,
      time_to_peak_min: 75,
      active_alerts: []
    };

    explanation = {
      headline: "Glucose projected to remain stable within euglycemic target range (70-180 mg/dL).",
      trend_summary: "Current CGM reading is 122 mg/dL with negligible physiological velocity (+0.1 mg/dL/min).",
      metabolic_factors: [
        "Active IOB is low (0.35 U), producing mild steady basal clearance.",
        "Residual COB (6.2 g) provides balanced glycemic support."
      ],
      hybrid_attribution: "72% Deep Neural Sequence Weight | 28% Hovorka Mechanistic ODE Prior",
      uncertainty_rationale: "Tight 95% confidence intervals (+/- 16 mg/dL) reflect low post-absorptive volatility.",
      key_takeaway: "No intervention needed. Target range expected for the next 5 hours."
    };
  } else if (scenario === "postprandial") {
    currentGlucose = 168.0;
    pointForecast = [174.2, 182.5, 189.1, 194.0, 196.5, 195.2, 191.0, 184.5, 176.0, 166.2, 155.8, 145.5, 136.2, 128.5, 122.4, 118.0, 115.2, 113.8, 113.1, 113.0];
    lower80 = pointForecast.map(v => Math.round((v - 14.0) * 10) / 10);
    upper80 = pointForecast.map(v => Math.round((v + 15.5) * 10) / 10);
    lower95 = pointForecast.map(v => Math.round((v - 22.0) * 10) / 10);
    upper95 = pointForecast.map(v => Math.round((v + 24.5) * 10) / 10);
    neuralPred = pointForecast.map(v => Math.round((v + 3.0) * 10) / 10);
    odeSim = pointForecast.map(v => Math.round((v - 4.2) * 10) / 10);
    alpha = [0.88, 0.86, 0.83, 0.80, 0.76, 0.72, 0.68, 0.65, 0.63, 0.62, 0.62, 0.63, 0.65, 0.68, 0.70, 0.72, 0.74, 0.75, 0.76, 0.76];

    riskAssessment = {
      alert_level: "WARNING",
      hypo_1h_prob: 0.01,
      hypo_2h_prob: 0.03,
      hypo_4h_prob: 0.08,
      hyper_2h_prob: 0.68,
      hyper_4h_prob: 0.15,
      nadir_mg_dl: 113.0,
      time_to_nadir_min: 300,
      peak_mg_dl: 196.5,
      time_to_peak_min: 60,
      active_alerts: ["Transitory Postprandial Excursion (> 180 mg/dL expected at +60m)"]
    };

    explanation = {
      headline: "Moderate postprandial peak projected at 196 mg/dL followed by insulin-driven descent.",
      trend_summary: "Current CGM is 168 mg/dL rising at +2.1 mg/dL/min following recent meal intake.",
      metabolic_factors: [
        "Carbohydrate absorption rate (k_empt = 0.024 /min) dominant in 0-90 min window.",
        "Bolus insulin sensitivity (S_I = 5.2e-4) accelerates clearance between 90-240 min."
      ],
      hybrid_attribution: "74% Deep Neural Sequence Weight | 26% Hovorka Mechanistic ODE Prior",
      uncertainty_rationale: "Uncertainty interval (+/- 24 mg/dL) captures variability in gastric emptying rate.",
      key_takeaway: "Postprandial peak expected to resolve spontaneously by 3 hours. Avoid stacking insulin."
    };
  } else if (scenario === "hypo_risk") {
    currentGlucose = 84.0;
    pointForecast = [78.2, 71.5, 64.8, 59.2, 56.1, 55.4, 57.0, 60.5, 66.2, 73.0, 80.5, 88.0, 95.2, 101.4, 106.2, 110.0, 112.5, 114.0, 115.0, 115.2];
    lower80 = pointForecast.map(v => Math.round((v - 8.5) * 10) / 10);
    upper80 = pointForecast.map(v => Math.round((v + 9.5) * 10) / 10);
    lower95 = pointForecast.map(v => Math.round((v - 13.0) * 10) / 10);
    upper95 = pointForecast.map(v => Math.round((v + 14.5) * 10) / 10);
    neuralPred = pointForecast.map(v => Math.round((v - 2.0) * 10) / 10);
    odeSim = pointForecast.map(v => Math.round((v + 3.0) * 10) / 10);
    alpha = [0.89, 0.88, 0.85, 0.82, 0.79, 0.75, 0.71, 0.68, 0.66, 0.65, 0.65, 0.66, 0.68, 0.70, 0.72, 0.74, 0.76, 0.77, 0.78, 0.78];

    riskAssessment = {
      alert_level: "CRITICAL",
      hypo_1h_prob: 0.82,
      hypo_2h_prob: 0.91,
      hypo_4h_prob: 0.35,
      hyper_2h_prob: 0.00,
      hyper_4h_prob: 0.01,
      nadir_mg_dl: 55.4,
      time_to_nadir_min: 75,
      peak_mg_dl: 115.2,
      time_to_peak_min: 300,
      active_alerts: ["CRITICAL: Impending Hypoglycemia (< 70 mg/dL at +45m)", "Projected Nadir: 55 mg/dL at +75m"]
    };

    explanation = {
      headline: "CRITICAL ALERT: Rapid descent towards hypoglycemia (55 mg/dL) projected within 75 minutes.",
      trend_summary: "Current CGM is 84 mg/dL with steep downward velocity (-1.8 mg/dL/min).",
      metabolic_factors: [
        "Excess active IOB (3.4 U) without sufficient circulating carbohydrate buffer.",
        "Endogenous glucose production suppressed by high active insulin concentration."
      ],
      hybrid_attribution: "76% Deep Neural Sequence Weight | 24% Hovorka Mechanistic ODE Prior",
      uncertainty_rationale: "Lower 95% bound reaches 42 mg/dL. High clinical certainty of hypoglycemic excursion.",
      key_takeaway: "Actionable: Consider 15-20g fast-acting carbohydrates to avert projected hypoglycemic event."
    };
  }

  return {
    disclaimer: RESEARCH_DISCLAIMER,
    patient_id: "demo_synthetic_patient",
    current_state: {
      glucose_mg_dl: currentGlucose,
      iob_units: scenario === "hypo_risk" ? 3.4 : (scenario === "postprandial" ? 2.8 : 0.4),
      cob_grams: scenario === "postprandial" ? 48.0 : (scenario === "stable" ? 6.2 : 2.0),
      primary_status: riskAssessment.alert_level === "CRITICAL" ? "HYPOGLYCEMIA_ALERT" : (riskAssessment.alert_level === "WARNING" ? "ELEVATED" : "IN_TARGET_RANGE")
    },
    forecast: {
      horizon_minutes: [15, 30, 45, 60, 75, 90, 105, 120, 135, 150, 165, 180, 195, 210, 225, 240, 255, 270, 285, 300],
      point_forecast_mg_dl: pointForecast,
      lower_80_mg_dl: lower80,
      upper_80_mg_dl: upper80,
      lower_95_mg_dl: lower95,
      upper_95_mg_dl: upper95,
      mean_uncertainty_std: scenario === "postprandial" ? 14.5 : 8.2
    },
    hybrid_components: {
      neural_prediction_mg_dl: neuralPred,
      ode_simulation_mg_dl: odeSim,
      neural_weight_alpha: alpha,
      mean_neural_weight_pct: Math.round(alpha.reduce((a, b) => a + b, 0) / alpha.length * 100)
    },
    risk_assessment: riskAssessment,
    explanation: explanation,
    wearable_context_logged: true
  };
}

export function getSyntheticWhatIfResponse(carbs = 50.0, bolus = 4.0, baselineGlucose = 120.0) {
  const trajectory = [];
  for (let i = 0; i < 20; i++) {
    const t = (i + 1) * 15; // minutes
    // Hovorka postprandial shape
    const carbEffect = (carbs * 1.8) * (t / 60) * Math.exp(-t / 75);
    const insEffect = (bolus * 22.0) * (t / 50) * Math.exp(-t / 60);
    const g = Math.max(40.0, baselineGlucose + carbEffect - insEffect);
    trajectory.push(Math.round(g * 10) / 10);
  }

  const peak = Math.max(...trajectory);
  const nadir = Math.min(...trajectory);
  const timeToPeak = (trajectory.indexOf(peak) + 1) * 15;
  const timeToNadir = (trajectory.indexOf(nadir) + 1) * 15;
  const inRangeCount = trajectory.filter(g => g >= 70 && g <= 180).length;
  const tir = Math.round((inRangeCount / trajectory.length) * 100);

  const warnings = [];
  if (nadir < 70) warnings.push("Simulated trajectory breaches hypoglycemia threshold (< 70 mg/dL).");
  if (peak > 180) warnings.push("Simulated trajectory breaches hyperglycemia threshold (> 180 mg/dL).");

  return {
    disclaimer: RESEARCH_DISCLAIMER,
    scenario_name: `what_if_meal_${carbs.toFixed(0)}g_bolus_${bolus.toFixed(1)}U`,
    simulated_trajectory: trajectory,
    nadir_glucose: nadir,
    time_to_nadir_min: timeToNadir,
    peak_glucose: peak,
    time_to_peak_min: timeToPeak,
    time_in_range_pct: tir,
    warnings: warnings
  };
}
