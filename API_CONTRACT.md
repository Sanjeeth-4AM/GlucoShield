# GlucoShield REST API Contract (v1.0.0)
**Document ID:** `GLUCOSHIELD-SPEC-API-CONTRACT-001`  
**Base URL:** `http://localhost:8000`  
**Version:** `1.0.0`  
**Status:** **ACTIVE / CERTIFIED PRODUCTION CONTRACT**  

---

## 1. Overview & Architectural Philosophy

GlucoShield exposes a production-grade REST API service powered by **FastAPI** that wraps the clinical decision-support core:
1. **Hybrid Forecaster:** Combines a 22-channel Deep Recurrent Neural Network (GRU-128) with a Mechanistic Physics-Informed ODE Digital Twin (Hovorka/Bergman kinetics) via adaptive gated blending $\alpha(t) \in [0, 1]$.
2. **Uncertainty Quantification:** Multi-source uncertainty via Monte Carlo Dropout ($8-16$ samples) yielding calibrated 80% and 95% physical prediction intervals.
3. **Clinical Risk Engine:** Stratifies impending hypoglycemia (1h, 2h, 4h) and hyperglycemia (2h, 4h) with automated clinical alert levels (`NORMAL`, `WARNING`, `CRITICAL`).
4. **Counterfactual "What-If" ODE Simulation:** Mechanistic postprandial trajectory prediction under proposed meal carbohydrates or insulin boluses.
5. **Automated Food Vision:** Human-in-the-loop meal photograph / query analysis using HuggingFace Food-101 and USDA FoodData Central nutrition density databases.
6. **Wearable Activity Context:** Optional telemetry logging (smartwatch steps, heart rate) preserved strictly for observational logging without altering the frozen 22-channel dynamic forecaster tensor.

---

## 2. API Endpoints Summary

| Method | Endpoint | Description | Input | Output |
|---|---|---|---|---|
| `GET` | `/api/v1/health` | System health, model readiness, research disclaimer | None | `HealthResponse` |
| `POST` | `/api/v1/forecast` | 5-hour multi-horizon hybrid glucose forecast & risk | 24h history (96 readings) + Static Profile | `ForecastResponse` |
| `POST` | `/api/v1/what-if` | Counterfactual ODE simulation of proposed meal/bolus | 24h history + Carbs/Bolus | `WhatIfResponse` |
| `POST` | `/api/v1/food/analyze` | Food image/text analysis & macronutrient density | Image Base64 / Text Query | `FoodAnalyzeResponse` |
| `POST` | `/api/v1/decision/full-flow` | Unified multimodal full decision flow | 24h history + Meal photo + Bolus | `FullFlowDecisionResponse` |

---

## 3. Endpoint Specifications

### 3.1. `GET /api/v1/health`
**Description:** Returns backend operational status, model readiness, active channel contract, and mandatory research disclaimer.

**Response Schema (`200 OK`):**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "neural_forecaster_loaded": true,
  "hybrid_forecaster_loaded": true,
  "ode_digital_twin_ready": true,
  "food_vision_ready": true,
  "active_channels_contract": 22,
  "research_disclaimer": "GlucoShield is an investigational clinical decision-support research tool. Not approved as a primary diagnostic device or automated insulin delivery controller. All dosing decisions must be validated by a qualified healthcare professional.",
  "timestamp": "2026-08-28T14:40:00.000000"
}
```

---

### 3.2. `POST /api/v1/forecast`
**Description:** Ingests a 24-hour patient history window (exactly 96 15-minute readings) and returns the 5-hour hybrid point trajectory, calibrated 80% and 95% uncertainty intervals, acute risk probabilities, and natural language clinical explanations.

**Request Payload:**
```json
{
  "patient_id": "patient_001",
  "history_readings": [
    {
      "timestamp": "2026-08-28T00:00:00",
      "cgm_glucose": 125.0,
      "insulin_bolus": 0.0,
      "insulin_basal": 0.5,
      "meal_carbs": 0.0
    }
    // ... exactly 96 readings total (24 hours at 15-minute intervals)
  ],
  "static_profile": {
    "age": 45.0,
    "bmi": 26.5,
    "hba1c": 58.0,
    "glycated_albumin": 18.0,
    "fasting_glucose": 130.0,
    "fasting_c_peptide": 0.8,
    "macrovascular_comp_count": 0.0,
    "microvascular_comp_count": 0.0,
    "is_t1dm": 1.0
  },
  "wearable_context": {
    "steps_15m": [120.0, 85.0],
    "heart_rate_bpm": [72.0, 75.0],
    "device_source": "TicWatch Pro / Apple Watch"
  }
}
```

**Response Payload (`200 OK`):**
```json
{
  "disclaimer": "GlucoShield is an investigational clinical decision-support research tool...",
  "patient_id": "patient_001",
  "current_state": {
    "glucose_mg_dl": 125.0,
    "iob_units": 0.45,
    "cob_grams": 12.3,
    "primary_status": "STABLE"
  },
  "forecast": {
    "horizon_minutes": [15, 30, 45, 60, 75, 90, 105, 120, 135, 150, 165, 180, 195, 210, 225, 240, 255, 270, 285, 300],
    "point_forecast_mg_dl": [126.2, 127.8, 129.5, 131.0, 132.4, 133.1, 133.0, 132.1, 130.5, 128.4, 126.1, 123.8, 121.5, 119.4, 117.6, 116.1, 115.0, 114.2, 113.8, 113.5],
    "lower_80_mg_dl": [118.5, 119.2, 120.1, 120.8, 121.3, 121.2, 120.4, 118.8, 116.5, 113.7, 110.8, 107.9, 105.1, 102.5, 100.2, 98.2, 96.6, 95.3, 94.4, 93.8],
    "upper_80_mg_dl": [133.9, 136.4, 138.9, 141.2, 143.5, 145.0, 145.6, 145.4, 144.5, 143.1, 141.4, 139.7, 137.9, 136.3, 135.0, 134.0, 133.4, 133.1, 133.2, 133.2],
    "lower_95_mg_dl": [114.1, 114.3, 114.8, 115.0, 115.0, 114.4, 113.2, 111.2, 108.5, 105.3, 101.9, 98.6, 95.5, 92.6, 90.0, 87.7, 85.8, 84.2, 83.0, 82.2],
    "upper_95_mg_dl": [138.3, 141.3, 144.2, 147.0, 149.8, 151.8, 152.8, 153.0, 152.5, 151.5, 150.3, 149.0, 147.5, 146.2, 145.2, 144.5, 144.2, 144.2, 144.6, 144.8],
    "mean_uncertainty_std": 12.4
  },
  "hybrid_components": {
    "neural_prediction_mg_dl": [127.1, 128.9, 131.0, ...],
    "ode_simulation_mg_dl": [124.5, 125.8, 126.9, ...],
    "neural_weight_alpha": [0.88, 0.85, 0.81, ...],
    "mean_neural_weight_pct": 71.4
  },
  "risk_assessment": {
    "alert_level": "NORMAL",
    "hypo_1h_prob": 0.02,
    "hypo_2h_prob": 0.04,
    "hypo_4h_prob": 0.07,
    "hyper_2h_prob": 0.01,
    "hyper_4h_prob": 0.02,
    "nadir_mg_dl": 113.5,
    "time_to_nadir_min": 300,
    "peak_mg_dl": 133.1,
    "time_to_peak_min": 75,
    "active_alerts": []
  },
  "explanation": {
    "headline": "Glucose profile projected to remain in target euglycemic range.",
    "trend_summary": "CGM glucose is currently stable at 125 mg/dL with minimal rate of change.",
    "metabolic_factors": ["Active IOB: 0.45 U acting to lower glucose.", "Active COB: 12.3 g buffering descent."],
    "hybrid_attribution": "71% Deep Recurrent Sequence Weight | 29% Hovorka ODE Mechanistic Prior",
    "uncertainty_rationale": "Calibrated 95% interval width (+/- 26 mg/dL) reflects low metabolic volatility.",
    "key_takeaway": "No clinical intervention required at this time."
  },
  "wearable_context_logged": true
}
```

---

### 3.3. `POST /api/v1/what-if`
**Description:** Runs a counterfactual mechanistic ODE simulation for a hypothetical meal or bolus scenario.

**Request Payload:**
```json
{
  "patient_id": "patient_001",
  "history_readings": [ /* 96 readings */ ],
  "scenario_meal_carbs_g": 60.0,
  "scenario_insulin_bolus_u": 4.5
}
```

**Response Payload (`200 OK`):**
```json
{
  "disclaimer": "GlucoShield is an investigational clinical decision-support research tool...",
  "scenario_name": "what_if_meal_60g_bolus_4.5U",
  "simulated_trajectory": [126.5, 131.2, 138.4, 146.0, 152.8, 157.1, 158.4, 156.9, 152.7, 146.4, 138.8, 130.6, 122.5, 115.1, 108.9, 104.2, 101.1, 99.4, 98.8, 99.0],
  "nadir_glucose": 98.8,
  "time_to_nadir_min": 270,
  "peak_glucose": 158.4,
  "time_to_peak_min": 90,
  "time_in_range_pct": 100.0,
  "warnings": []
}
```

---

### 3.4. `POST /api/v1/food/analyze`
**Description:** Analyzes meal photo or food name, looks up macronutrient density, applies portion scaling, and enforces human confirmation safety policies.

**Request Payload:**
```json
{
  "food_name_query": "apple",
  "portion_g": 182.0
}
```

**Response Payload (`200 OK`):**
```json
{
  "image_food_candidates": [
    {
      "name": "apple",
      "confidence": 1.0,
      "source": "manual_user_entry",
      "raw_label": "apple"
    }
  ],
  "selected_food": "apple",
  "portion_g": 182.0,
  "nutrition_density": {
    "food_name": "apple",
    "carbs_g_per_100g": 13.8,
    "protein_g_per_100g": 0.3,
    "fat_g_per_100g": 0.2,
    "calories_kcal_per_100g": 52.0,
    "source": "usda_fooddata_central"
  },
  "final_macros": {
    "carbs_g": 25.1,
    "protein_g": 0.5,
    "fat_g": 0.4,
    "calories_kcal": 94.6
  },
  "requires_user_confirmation": true,
  "warnings": [
    "Advisory estimate only. Photo recognition cannot measure hidden oils, sugars, or exact recipe ratios."
  ]
}
```

---

### 3.5. `POST /api/v1/decision/full-flow`
**Description:** Complete multimodal orchestration endpoint. Integrates Food Vision $\rightarrow$ Hybrid Forecaster $\rightarrow$ Counterfactual Simulation $\rightarrow$ Clinical Summary into a unified report.

---

## 4. Physiological Bounds & Validation Rules

1. `cgm_glucose`: strictly $[20.0, 600.0]\text{ mg/dL}$. Values outside trigger `422 Unprocessable Entity`.
2. `history_readings`: exactly $96$ entries (24 hours). Lists $\ne 96$ trigger `422 Unprocessable Entity`.
3. `insulin_bolus`: $[0.0, 50.0]\text{ Units}$.
4. `meal_carbs`: $[0.0, 300.0]\text{ Grams}$.
5. `portion_g`: $[1.0, 2000.0]\text{ Grams}$.
