# GlucoShield — Phase 7C Telemetry Temporal Alignment Feasibility
**Document ID:** `GLUCOSHIELD-RPT-PHASE7C-ALIGN-001`  
**Timestamp:** 2026-08-28T17:17:00 Local Time  
**Author:** Lead Deep Learning & Physiological Systems Engineer  
**Status:** **ALIGNMENT FEASIBILITY CONFIRMED**  

---

## 1. Executive Summary & Temporal Resolution Compatibility

GlucoShield's core forecasting engine operates on a standardized **15-minute discrete time grid** ($\Delta t = 15\text{ minutes}$, $96\text{ steps} = 24\text{ hours}$ history, $20\text{ steps} = 5\text{ hours}$ forecast).

Both **OhioT1DM** and **D1NAMO** natively record CGM at **5-minute intervals** and wearable telemetry at **1 Hz to 5-minute intervals**. This document defines the exact, mathematically sound downsampling and causal aggregation transformations required to map raw wearable streams into the GlucoShield 15-minute grid without future lookahead leakage.

---

## 2. Mathematical Temporal Aggregation Pipeline (5-min / 1 Hz $\rightarrow$ 15-min)

```
[Raw Wearable Stream: 1 Hz / 5-min bins]
                  │
                  ▼
[Causal 15-Minute Window Slicing: (t - 15m, t]]
                  │
                  ├── Cumulative Flux Signals (Steps): Summation
                  │   step_count_15m = SUM_{t-15m}^{t} steps
                  │
                  ├── Continuous State Signals (Heart Rate, Accel Magnitude): Mean & Volatility
                  │   hr_mean_15m = MEAN_{t-15m}^{t} heart_rate
                  │   hr_std_15m  = STD_{t-15m}^{t} heart_rate
                  │   accel_mag_15m = MEAN_{t-15m}^{t} sqrt(a_x^2 + a_y^2 + a_z^2)
                  │
                  └── Impulsive / Event Signals (Insulin Bolus, Rescue Carbs): Timestamp Alignment
                      bolus_15m = SUM_{t-15m}^{t} bolus_units
```

---

## 3. Strict Signal Aggregation Rules Table

| Raw Signal Name | Raw Source Resolution | 15-Minute Aggregation Operator | Target Feature Name | Justification & Causal Integrity |
|---|:---:|:---:|---|---|
| **CGM Glucose** | 5-minute instantaneous | Instantaneous reading at step boundary $t$ | `glucose` (mg/dL) | Preserves exact state at current time step. |
| **Step Count** | 1-min or 5-min intervals | Sum over past 15 min: $\sum_{i=1}^3 \text{steps}_i$ | `steps_15m` (Count) | Measures total mechanical work performed in the interval. |
| **Heart Rate** | 1 Hz or 5-min intervals | Mean over past 15 min: $\frac{1}{K}\sum \text{HR}_i$ | `hr_mean_15m` (bpm) | Measures sustained circulatory demand. |
| **Heart Rate Volatility** | 1 Hz or 5-min intervals | Standard deviation over 15 min | `hr_std_15m` (bpm) | Captures erratic exertion bursts vs steady-state rest. |
| **Accelerometer Magnitude** | 1 Hz to 50 Hz raw | Mean Euclidean norm: $\frac{1}{N}\sum \sqrt{a_x^2+a_y^2+a_z^2}$ | `accel_mag_15m` ($g$) | Proxy for metabolic equivalent of task (METs). |
| **Resting Heart Rate (RHR)** | Daily nocturnal baseline | Lowest 30-min rolling mean during sleep (02:00-05:00) | `rhr_baseline` (bpm) | Patient baseline anchor (updated daily). |
| **Heart Rate Reserve (HRR)** | Derived | $\frac{\text{HR}_{\text{mean}} - \text{RHR}}{\text{HR}_{\text{max}} - \text{RHR}} \times 100\%$ | `hr_reserve_pct` ($\%$) | Standardized exertion metric across fitness levels. |

---

## 4. Missing-Data & Sensor Dropout Strategy

1. **Watch Off-Wrist / Charging Gaps:**
   * When wearable contact is lost, `steps_15m = 0.0` and `hr_mean_15m = RHR` (default resting state).
   * A binary channel `wearable_present \in \{0, 1\}` is explicitly fed to the neural network and fusion gate.
2. **CGM Dropouts (Gaps $\le 30\text{ min}$):**
   * Backward zero-order hold interpolation.
3. **Long Gaps ($>60\text{ min}$):**
   * Sequence boundary split (zero synthetic extrapolation across major dropouts).

---
*Certified for Phase 7C temporal alignment feasibility.*
