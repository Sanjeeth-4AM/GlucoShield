# GlucoShield REST API Reference

**Base URL:** `http://localhost:8000/api/v1`  
**OpenAPI Specification:** Available at `/openapi.json` and interactive Swagger UI at `/docs`  
**Authentication Scheme:** HTTP Bearer (JWT Token via `/api/v1/auth/login`)  

---

## 1. Authentication & User Management

### `POST /api/v1/auth/register`
Registers a new user account.
- **Request Body:** `UserRegister` (`email`, `password`, `full_name`)
- **Response:** `UserResponse` (`id`, `email`, `full_name`, `created_at`)

### `POST /api/v1/auth/login`
Authenticates a user and returns an access token.
- **Request Body:** `UserLogin` (`email`, `password`)
- **Response:** `TokenResponse` (`access_token`, `token_type`, `user`)

### `GET /api/v1/auth/me`
Retrieves the profile of the authenticated user.
- **Headers:** `Authorization: Bearer <TOKEN>`
- **Response:** `UserResponse`

---

## 2. Multi-Horizon Forecasting & Risk

### `POST /api/v1/forecast`
Executes Combination C multi-horizon continuous forecasting and acute risk classification.
- **Request Body:** `ForecastRequest`
  - `patient_id`: String
  - `history_readings`: Array of 96 `TimeStepReading` objects (24 hours at 15-min cadence)
  - `static_profile`: Optional `PatientStaticProfile` (9 covariates)
  - `requested_model_version`: Optional ("COMBINATION_C" default, "V1_FROZEN", "PHASE13_VALIDATED")
- **Response:** `ForecastResponse`
  - `forecast`: `point_forecast_mg_dl` (20 steps), `lower_95_mg_dl`, `upper_95_mg_dl`, `lower_80_mg_dl`, `upper_80_mg_dl`
  - `risk_assessment`: `hypo_1h_prob`, `hypo_2h_prob`, `hypo_4h_prob`, `hyper_2h_prob`, `hyper_4h_prob`, `alert_level`, `active_alerts`
  - `explanation`: `headline`, `trend_summary`, `metabolic_factors`, `key_takeaway`
  - `telemetry`: Disagreement indices and physics contribution weight

### `POST /api/v1/what-if`
Simulates counterfactual prandial carbohydrate or insulin bolus modifications using the Hovorka ODE digital twin.
- **Request Body:** `WhatIfRequest`
  - `patient_id`: String
  - `history_readings`: 96 readings
  - `what_if_carbs`: Float (grams of carbohydrates)
  - `what_if_bolus`: Float (units of rapid-acting insulin)
- **Response:** `WhatIfResponse`
  - `simulated_trajectory`: 20-step continuous glucose projection
  - `simulated_peak`: Predicted peak glucose (mg/dL)
  - `simulated_nadir`: Predicted trajectory minimum (mg/dL)
  - `simulated_tir_pct`: Projected Time in Range percentage

---

## 3. Real Cohort & Comparative Intelligence

### `GET /api/v1/cohort/demo-patients`
Returns the de-identified Patient A (euglycemic controlled profile) and Patient B (hyperglycemic profile) benchmark records.
- **Response:** JSON object with `patientA` and `patientB` profiles, 96 CGM telemetry points, and baseline forecasts.

### `GET /api/v1/cohort/comparison`
Returns dual-patient comparative intelligence metrics derived directly from the research cohort.
- **Response:** Comparative scorecard (TIR, TAR, TBR, mean glucose, acute hypo risks, clinical interpretations).

---

## 4. Food Vision & Nutrition

### `POST /api/v1/food/analyze`
Analyzes meal photographs to estimate food categories and macronutrients.
- **Request Body:** `FoodAnalyzeRequest` (Base64-encoded image or multipart file)
- **Response:** `FoodAnalyzeResponse`
  - `food_name`: Predicted food classification
  - `estimated_carbs_g`: Estimated carbohydrate content
  - `estimated_protein_g`: Estimated protein content
  - `estimated_fat_g`: Estimated fat content
  - `confidence_score`: Recognition confidence
  - `nutritional_source`: USDA FoodData Central identifier

---

## 5. System Health & Observability

### `GET /api/v1/health`
Returns full backend system health, model artifact verification status, and database connection.
- **Response:** `HealthResponse` (`status`, `active_model_version`, `artifact_integrity`, `neural_forecaster_loaded`)

### `GET /api/v1/health/live`
Lightweight Kubernetes / Docker liveness probe (`{"status": "alive"}`).

### `GET /api/v1/health/ready`
Readiness probe verifying that PyTorch models and scalers are loaded in memory (`{"status": "ready"}`).
