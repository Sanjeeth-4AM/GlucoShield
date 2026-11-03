# GlucoShield Forecast Regression Test Matrix

**Test Framework:** Node.js native test runner (`node:test`, `node:assert`)  
**Test File:** [`frontend/src/api/api.test.js`](file:///D:/ML%20PROJECT/frontend/src/api/api.test.js)  
**Total Tests:** 24 Passing | 0 Failing | 0 Skipped  
**Execution Time:** ~75 ms  

---

## 1. Test Suite Architecture

```
frontend/src/api/api.test.js
├── Suite 1: Frontend API Contracts & Demo Data Integrity (7 Tests)
│   ├── Test 1.1: 96 15-minute readings for 24-hour buffer
│   ├── Test 1.2: 20-step multi-horizon forecast with monotonic 95% >= 80% intervals
│   ├── Test 1.3: What-If simulation trajectory with peak, nadir, and TIR
│   ├── Test 1.4: Static profile 9-channel schema preservation
│   ├── Test 1.5: Clinical research disclaimer enforcement
│   ├── Test 1.6: React SyntheticEvent / circular reference sanitization
│   └── Test 1.7: Patient update PUT request Bearer token and field payload
├── Suite 2: Forecast Data Consistency & Clinical Integrity (8 Tests)
│   ├── Test 2.1: Distinct Historical vs Projected TIR without 94.2% fallback
│   ├── Test 2.2: 5 Hourly milestone steps in chronological order matching point_forecast_mg_dl
│   ├── Test 2.3: Origin glucose and peak projection derivation without synthetic fallbacks
│   ├── Test 2.4: Origin precedence (API origin > historical fallback > null)
│   ├── Test 2.5: Non-hourly peak index (+75m) and timing formatting (+1h 15m)
│   ├── Test 2.6: Non-finite sanitization and rejection of inverted uncertainty intervals
│   ├── Test 2.7: Immutability of base forecast mean under filter toggles and What-If
│   └── Test 2.8: Prepending NOW anchor when history is empty but origin is valid
└── Suite 3: 9 Representative Forecast Validation Cases (9 Tests)
    ├── Case 1: Normal forecast with complete response
    ├── Case 2: Missing optional risk-assessment fields
    ├── Case 3: Telemetry pending with historical readings available
    ├── Case 4: Empty history and no valid origin
    ├── Case 5: Short or malformed forecast arrays
    ├── Case 6: Missing uncertainty intervals
    ├── Case 7: Forecast with peak at non-hourly index (+30m)
    ├── Case 8: What-If scenario present and absent
    └── Case 9: API error or unavailable backend
```

---

## 2. Detailed Test Specifications & Assertion Matrix

| ID | Test Name | Scope | Input Conditions | Expected Output & Assertions | Status |
|---|---|---|---|---|---|
| **1.1** | Buffer Length & Range | Data Integrity | Scenario: `"stable"` | Array length = 96; readings numeric and within $[20, 600]$ mg/dL. | **PASS** |
| **1.2** | Multi-Horizon Intervals | Interval Semantics | 20 forecast steps | Length = 20 for all 5 arrays; $\Delta_{95} \ge \Delta_{80} - 0.01$ for all 20 steps. | **PASS** |
| **1.3** | What-If Simulation | Scenario Simulation | Carbs: 60g, Bolus: 4.5U, Basal: 120 | Simulated trajectory length = 20; peak/nadir numeric; $0 \le \text{TIR} \le 100$. | **PASS** |
| **1.4** | 9-Channel Static Schema | API Schema | `DEMO_STATIC_PROFILE` | Exactly 9 channels; `is_t1dm = 1.0`. | **PASS** |
| **1.5** | Research Disclaimer | Regulatory Safety | `RESEARCH_DISCLAIMER` | Contains "decision-support" and "investigational". | **PASS** |
| **1.6** | Circular Event Protection | Frontend Hook | Circular `SyntheticEvent` object | Successfully sanitizes and serializes without throwing circular JSON error. | **PASS** |
| **1.7** | Auth & Patient Payload | API Client | Mock JWT and profile update | Method = PUT; Authorization = Bearer; all 9 canonical channels serialized. | **PASS** |
| **2.1** | Distinct In-Range Calculation | Metric Separation | History: 3 in-range, 1 high; Forecast: 10 in-range, 10 high | Historical TIR = 75%; Projected TIR = 50%; neither equals `"94.2%"`. | **PASS** |
| **2.2** | Milestone Chronology | Milestone Mapping | Forecast points at indices 3, 7, 11, 15, 19 | Strictly maps to $+60\text{m}, +120\text{m}, +180\text{m}, +240\text{m}, +300\text{m}$; interval bounds monotonic. | **PASS** |
| **2.3** | Origin & Peak Derivation | Telemetry Binding | `current_state.glucose_mg_dl = 158.4`, `peak_mg_dl = 180.0` | Origin = 158.4; Peak = 180.0; Ensemble status = "Informational Advisory" (not "Verified Safe"). | **PASS** |
| **2.4** | Origin Precedence | Fallback Logic | Case A: Both present; Case B: API origin null; Case C: Both absent | Case A: API origin used; Case B: History used; Case C: `null` (never synthetic `142.0`). | **PASS** |
| **2.5** | Non-Hourly Peak Index | Peak Timing | Peak at index 4 (+75m = 230 mg/dL) | Max = 230; Timing formatted as `+1h 15m`; hourly milestones $T+1\text{h}$ (+60m) and $T+2\text{h}$ (+120m) preserved. | **PASS** |
| **2.6** | Interval Inversion Rejection | Interval Sanitization | Upper bound < lower bound, non-finite values | Inverted bounds rejected to `null`; string/NaN/Infinity sanitized to `null`. | **PASS** |
| **2.7** | Forecast Trajectory Immutability | Filter & Overlay | Toggling `all`, `80_only`, `mean_only`, adding/clearing What-If | Mean trajectory values remain bit-for-bit identical across all operations. | **PASS** |
| **2.8** | Empty History Anchor | Origin Anchor | `history = []`, `originGlucose = 142.5` | Prepend `NOW` anchor point at index 0 with offset 0 and value 142.5. | **PASS** |
| **3.1** | Case 1: Normal Complete | End-to-End | Full synthetic forecast response | All 20 steps, 80%/95% bounds, TIR evaluated cleanly. | **PASS** |
| **3.2** | Case 2: Missing Risk Fields | Robustness | `risk_assessment = null` | Peak derived from max point; primary status = "STABLE"; ensemble status = "Nominal Serving (Active)". | **PASS** |
| **3.3** | Case 3: Telemetry Pending | State Handling | `forecastData = null`, `isLoading = true` | Origin = latest CGM; Projected TIR = `null`; Historical TIR = 100%; milestone values = `"—"`. | **PASS** |
| **3.4** | Case 4: Empty History & Origin | State Handling | `history = []`, `origin = null` | Origin = `null`; Historical TIR = `null`; no synthetic numbers. | **PASS** |
| **3.5** | Case 5: Short Array (5 steps) | Array Robustness | Array with only 5 points | Milestone $T+1\text{h}$ populated; $T+2\text{h}$ through $T+5\text{h}$ display `"—"`. | **PASS** |
| **3.6** | Case 6: Missing Intervals | Interval Fallback | `lower_80_mg_dl = []`, `upper_80_mg_dl = []` | Ribbon displays "Unavailable"; Mean trajectory continues plotting. | **PASS** |
| **3.7** | Case 7: Non-Hourly Peak (+30m) | Peak Timing | Peak at index 1 (+30m = 195 mg/dL) | `maxVal = 195`, `peakMinute = 30`, format = `+0h 30m`; milestone $T+1\text{h}$ = 170. | **PASS** |
| **3.8** | Case 8: What-If Overlay Toggle | Scenario Isolation | Overlay present vs `null` | Base trajectory unmodified; scenario trajectory cleanly anchored at $T_0$. | **PASS** |
| **3.9** | Case 9: Backend 503 / Error | Error Recovery | `forecastData = null`, HTTP 503 error | Origin = `null`; Projected TIR = `null`; ensemble status = "Awaiting Forecast". | **PASS** |

---

## 3. Command Execution Verification

```powershell
node --test frontend/src/api/api.test.js
```
* **Exit Code:** 0
* **Output Summary:** 24 passed, 0 failed, 3 suites, duration 75 ms.
