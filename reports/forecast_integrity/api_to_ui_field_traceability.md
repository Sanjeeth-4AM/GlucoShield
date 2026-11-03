# GlucoShield API-to-UI Field Traceability & Contract Audit

**Audit Date:** 2026-10-12  
**Service Target:** Certified Combination C Production Model Serving  
**Endpoint:** `POST /api/v1/forecast`  
**Frontend Consumers:** [`ForecastChart.jsx`](file:///D:/ML%20PROJECT/frontend/src/components/dashboard/ForecastChart.jsx), [`ForecastView.jsx`](file:///D:/ML%20PROJECT/frontend/src/components/forecast/ForecastView.jsx)  

---

## 1. Field Mapping & Provenance Matrix

| Displayed Value / Metric | Authorized API Source Field | Units | Provenance / Category | Handling of Null / Missing / Invalid Data | Former Fallback / Remediated Defect |
|---|---|---|---|---|---|
| **Current / Origin Glucose ($T_0$ / NOW)** | `forecastData.current_state.glucose_mg_dl` | mg/dL | Observed Telemetry | If API origin is `null`/`undefined`, falls back to latest observed CGM reading in `historyReadings`. If history is also empty, renders `null` / `"—"`. Sanitized against non-finite values. | Formerly defaulted to hardcoded `142.0` in both chart and analytical view. Remediation ensures zero synthetic number generation. |
| **Current Velocity** | `forecastData.current_state.velocity_mg_dl_per_15m` | mg/dL / 15m | Observed Telemetry | Renders `"—"` if missing. | Verified genuine telemetry from state vector $d_r[0, -1, 1]$. |
| **Current IOB (Insulin on Board)** | `forecastData.current_state.iob_units` | Units (U) | Derived Telemetry | Renders `"—"` if missing. | Genuine telemetry from state vector $d_r[0, -1, 16]$. |
| **Current COB (Carbs on Board)** | `forecastData.current_state.cob_grams` | Grams (g) | Derived Telemetry | Renders `"—"` if missing. | Genuine telemetry from state vector $d_r[0, -1, 19]$. |
| **20-Step Trajectory Points** | `forecastData.forecast.point_forecast_mg_dl[0..19]` | mg/dL | Forecast (Combination C) | Each step maps to $+ (i+1) \times 15\text{m}$ ($+15\text{m}$ to $+300\text{m}$). Sanitized via `isFinite()`; non-numeric values replaced with `null` so Recharts connects clean segments. | Plotted points strictly follow chronological order without displacement. |
| **Projected Peak Glucose** | `forecastData.risk_assessment.peak_mg_dl` | mg/dL | Derived Risk Metric | If `risk_assessment` is omitted, derived dynamically as $\max(\text{valid } point\_forecast\_mg\_dl)$. If array is empty, renders `null` / `"—"`. | Removed fallback to current glucose. |
| **Time to Projected Peak** | `forecastData.risk_assessment.time_to_peak_min` | Minutes from $T_0$ | Derived Risk Metric | If `risk_assessment` is omitted, derived dynamically as $(idx_{\max} + 1) \times 15\text{m}$. Formatted as `+Xh Ym`. If array is empty, renders `null` / `"—"`. | Formatted consistently across chart footer (`~180 mg/dL (+1h 15m)`) and Card 1 narrative. |
| **Projected Nadir Glucose** | `forecastData.risk_assessment.nadir_mg_dl` | mg/dL | Derived Risk Metric | If missing, derived as $\min(\text{valid } point\_forecast\_mg\_dl)$ or `"—"`. | Verified genuine risk evaluation output. |
| **Time to Projected Nadir** | `forecastData.risk_assessment.time_to_nadir_min` | Minutes from $T_0$ | Derived Risk Metric | If missing, derived as $(idx_{\min} + 1) \times 15\text{m}$ or `"—"`. | Verified genuine risk evaluation output. |
| **80% Uncertainty Bounds** | `forecastData.forecast.lower_80_mg_dl`, `upper_80_mg_dl` | mg/dL | Epistemic Uncertainty (Phase 13) | Sanitized with `isFinite()`. Inverted bounds ($u_{80} < l_{80}$) are rejected and set to `null`. If missing, ribbon flags "Unavailable" and Area rendering is suppressed. | Formerly synthesized via arbitrary offsets `val - 8` / `val + 8`. Now strictly bound to API values. |
| **95% Uncertainty Bounds** | `forecastData.forecast.lower_95_mg_dl`, `upper_95_mg_dl` | mg/dL | Epistemic Uncertainty (Phase 13) | Sanitized with `isFinite()`. Inverted bounds ($u_{95} < l_{95}$) are rejected and set to `null`. If missing, ribbon flags "Unavailable" and Area rendering is suppressed. | Formerly synthesized via arbitrary offsets `val - 16` / `val + 16`. Now strictly bound to API values. |
| **5-Hour Horizon Projected In-Range (%)** | Derived from `forecastData.forecast.point_forecast_mg_dl` | Percentage (%) | Derived Metric ($\% \in [70, 180]$) | Calculated strictly over valid finite future forecast steps: `(validPoints >= 70 && <= 180) / validPoints.length * 100`. If forecast points are empty, renders `null` / `"—"`. | Formerly defaulted to static string `"94.2%"` due to absent `risk_assessment.time_in_range_pct` field in API schema. Now strictly computed from real points. |
| **Observed Buffer In-Range (%)** | Derived from `historyReadings` | Percentage (%) | Observed Historical Metric ($\% \in [70, 180]$) | Calculated strictly over valid numeric historical CGM readings: `(validHistory >= 70 && <= 180) / validHistory.length * 100`. If history is empty, renders `null` / `"—"`. | Decoupled and explicitly distinguished from projected in-range percentage. |
| **Clinical Trajectory Headline / Narrative** | `forecastData.explanation.headline` | Text | Clinical Decision Narrative | If missing, dynamically generates neutral description: `"Forward trajectory evaluated under Combination C. Projected peak: ~X mg/dL (+Ym)."` | Formerly static hardcoded postprandial paragraph. Now driven by explanation engine. |
| **Trend Summary Badge** | `forecastData.explanation.trend_summary` or `risk_assessment.primary_status` | Categorical String | Clinical Decision Status | Defaults to `"STABLE"` if missing. | Formerly hardcoded static badge `"Postprandial"`. |
| **Ensemble Status / Health** | `forecastData.risk_assessment.alert_level` | Severity String | Diagnostic Telemetry | Evaluates `CRITICAL` $\rightarrow$ `"Critical Alert (Active)"`, `WARNING` $\rightarrow$ `"Warning Advisory (Active)"`, `INFO` $\rightarrow$ `"Informational Advisory"`, Nominal $\rightarrow$ `"Nominal Serving (Active)"`. | Formerly hardcoded marketing string `"Verified Safe"`. Replaced with neutral diagnostic status. |
| **Clinical Target Adherence** | Derived from Projected In-Range vs 70% threshold | Status String | Clinical Target Evaluation | If projected in-range $\ge 70\%$, renders `"Projected ≥70% Target Met"`; if $< 70\%$, renders `"Projected <70% Target"`; if pending, renders `"Pending Forecast"`. | Formerly hardcoded marketing string `"Optimal Control"`. Replaced with objective target status. |
| **Hourly Milestone Rows ($T+1\text{h}$ to $T+5\text{h}$)** | Indices $3, 7, 11, 15, 19$ of `point_forecast_mg_dl` and bounds | mg/dL | Horizon Checkpoints | For each milestone index $m$, if $m < \text{length}$, displays rounded integer; if $m \ge \text{length}$, displays `"—"`. | Chronologically verified ($+60\text{m}, +120\text{m}, +180\text{m}, +240\text{m}, +300\text{m}$). |
| **Milestone Rate of Change (ROC)** | Derived: $(val_t - val_{t-60}) / 60$ | mg/dL/min | Derived Milestone Metric | For $T+1\text{h}$, baseline is `originGlucose`. If either point is non-numeric, displays `"—"`. Formatted as `+X.Y mg/dL/m` or `-X.Y mg/dL/m`. | Uses consistent 60-minute denominator and origin baseline. |
| **What-If Simulation Trajectory** | `whatIfTrajectory` (from `WhatIfResponse.simulated_trajectory`) | mg/dL | Simulated Scenario | Plotted as secondary dashed blue line anchored at $T_0$. If `whatIfTrajectory` is `null`/`undefined`, line is suppressed; base forecast remains completely untouched. | Scenario data isolated from certified base forecast. |

---

## 2. Temporal & Timestamp Conventions

1. **Origin ($T_0$ / NOW):**
   * Represents the latest observed CGM reading time.
   * `minuteOffset = 0`.
   * Serves as common anchor point for Historical CGM line, Forecast Mean line, 80% & 95% Uncertainty Bands, and What-If Scenario line.
2. **Historical Buffer:**
   * Step cadence: $-15\text{m}$ intervals.
   * Window: up to 16 steps (4 hours) displayed in chart.
   * Full buffer: 96 steps (24 hours) passed to backend preprocessor.
3. **Forecast Horizon:**
   * Step cadence: $+15\text{m}$ intervals.
   * Horizon length: 20 steps ($+15\text{m}, +30\text{m}, \dots, +300\text{m} = 5\text{ hours}$).
   * Milestones: Hourly checkpoints at step 4 ($T+1\text{h}$), step 8 ($T+2\text{h}$), step 12 ($T+3\text{h}$), step 16 ($T+4\text{h}$), and step 20 ($T+5\text{h}$), corresponding to zero-indexed array elements $3, 7, 11, 15, 19$.
