# GlucoShield — Phase 7C Activity Feature Scientific Audit
**Document ID:** `GLUCOSHIELD-RPT-PHASE7C-FEAT-001`  
**Timestamp:** 2026-08-28T17:18:00 Local Time  
**Author:** Lead Deep Learning & Physiological Systems Engineer  
**Status:** **FEATURE AUDIT CERTIFIED**  

---

## 1. Executive Summary & Physiological Justification

Physical activity exerts a dual physiological effect on glucose metabolism:
1. **Acute Non-Insulin Glucose Clearance:** Muscle contraction triggers **GLUT-4 transporter translocation** to the plasma membrane independently of insulin, accelerating glucose uptake from interstitial fluid into working myocytes.
2. **Post-Exercise Insulin Sensitivity Surge:** Moderate-to-vigorous exercise increases peripheral insulin sensitivity ($S_I$) for $12 - 24\text{ hours}$ post-exercise, increasing nocturnal hypoglycemia risk.

This audit scientifically evaluates candidate wearable-derived features at a **15-minute sampling grid** for integration into GlucoShield V2.

---

## 2. Comprehensive 15-Minute Activity Feature Audit

| Candidate Feature | Physical Formula / Computation | Physiological Mechanism | Data Source Support | Scientific Validity Rating | Verdict |
|---|---|---|:---:|:---:|:---:|
| **15-Min Step Count** (`steps_15m`) | $\sum_{t-15\text{m}}^t \text{steps}$ | Mechanical locomotion load driving myocellular glycogen depletion and GLUT-4 uptake. | OhioT1DM (2018), D1NAMO, Smartwatches | **High (Direct Metric)** | **ACCEPTED (PRIMARY ACTIVITY CHANNEL)** |
| **15-Min Mean Heart Rate** (`hr_mean_15m`) | $\frac{1}{N}\sum \text{HR}_i$ (bpm) | Circulatory metabolic demand & sympathetic nervous activation. | OhioT1DM (2018), D1NAMO, Apple/Garmin | **High (Cardiovascular Exertion)** | **ACCEPTED (PRIMARY WEARABLE CHANNEL)** |
| **Heart Rate Volatility** (`hr_std_15m`) | $\sqrt{\frac{1}{N}\sum (\text{HR}_i - \bar{\text{HR}})^2}$ | Differentiates steady-state continuous jogging from intermittent high-intensity interval training (HIIT). | OhioT1DM (2018), D1NAMO | **Moderate-High** | **ACCEPTED (INTENSITY MODULATION)** |
| **Accelerometer Intensity** (`accel_mag_15m`) | $\frac{1}{K}\sum \sqrt{a_x^2+a_y^2+a_z^2}$ | Non-step physical movements (cycling, weightlifting, upper body exertion). | OhioT1DM (2018+2020), D1NAMO | **High** | **ACCEPTED (GENERAL ACTIVITY)** |
| **Active / Sedentary Indicator** (`is_active_15m`) | $\mathbb{I}(\text{steps}_{15\text{m}} > 100 \lor \text{HR}_{\text{mean}} > 1.25 \times \text{RHR})$ | Binary gating mask for physiological exercise compartment activation in ODE. | Derivable from steps & HR | **High (Gating Flag)** | **ACCEPTED (ODE GATING TRIGGER)** |
| **Rolling 60-Min Activity Load** (`active_load_60m`) | $\sum_{k=0}^3 \gamma^k \cdot \text{steps}_{t - 15k}$ ($\gamma=0.75$) | Exponential decay accounting for cumulative muscle fatigue and prolonged GLUT-4 activation. | Derivable from 15m steps | **High (Cumulative Clearance)** | **ACCEPTED (CUMULATIVE LOAD)** |
| **Heart Rate Reserve %** (`hr_reserve_pct`) | $\frac{\text{HR}_{\text{mean}} - \text{RHR}}{\text{HR}_{\text{max}} - \text{RHR}} \times 100\%$ | Normalized physiological exertion across varying individual aerobic fitness levels. | Requires resting HR baseline + age-predicted $\text{HR}_{\text{max}}$ ($220 - \text{age}$) | **High (Standardized Exertion)** | **ACCEPTED (CONDITIONAL ON RHR BASELINE)** |
| **Estimated Exercise Onset** (`exercise_onset_flag`) | Pulse indicator when active state initiates | Marks discrete workout start for ODE acute response triggering. | Derivable | **Moderate** | **ACCEPTED (EVENT PULSE)** |

---

## 3. Explicitly REJECTED Wearable Features

| Candidate Feature | Reason for Scientific Rejection at 15-Minute Forecasting Grid |
|---|---|
| **Raw ECG Beat-to-Beat RR Intervals (ms)** | Unnecessary for 15-minute macro-glycemic forecasting; requires massive bandwidth ($>100\text{ MB/day/patient}$) and introduces extreme motion artifact noise during vigorous exercise. |
| **Proprietary Vendor Stress Scores** | Undocumented black-box formulas (e.g. Garmin Stress, Whoop Strain) that vary across firmware updates, lack scientific reproducibility, and cannot be defended in clinical peer review. |
| **Continuous Blood Pressure Proxies** | Optical PPG pulse-transit-time blood pressure estimation on commercial watches has low clinical accuracy ($\text{error} > 15\text{ mmHg}$) and negligible acute 15-minute glycemic correlation. |
| **Real-Time VO2 Max** | VO2 Max is a chronic cardiorespiratory fitness marker that changes over months, not an acute 15-minute dynamic input. |

---
*Certified for Phase 7C activity feature scientific audit.*
