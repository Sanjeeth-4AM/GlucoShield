# GlucoShield — Phase 7C V2 Exercise Architecture Options
**Document ID:** `GLUCOSHIELD-RPT-PHASE7C-ARCH-001`  
**Timestamp:** 2026-08-28T17:19:00 Local Time  
**Author:** Lead Deep Learning & Physiological Systems Engineer  
**Status:** **ARCHITECTURE ASSESSMENT COMPLETE (NO IMPLEMENTATION IN STEP 1)**  

---

## 1. Architectural Overview & Context

Physical activity is the single largest non-pharmacological perturbation affecting glucose homeostasis in Type 1 and Type 2 diabetes.

This document critically assesses **two distinct architectural pathways** for incorporating wearable activity telemetry into GlucoShield V2:
* **Option A:** Feature-Level Multimodal Extension (Data-Driven Neural Augmentation)
* **Option B:** Physiology-Aware Exercise Digital Twin (Mechanistic ODE Compartment Expansion)

---

## 2. Option A: Feature-Level Multimodal Extension

```
[24h CGM + Insulin + Meals (22 Channels)] ──────┐
                                                 │
[Wearable Activity Stream: 6 Channels] ──────────┼──> [Expanded GRU-128 Backbone] ──> [5-Hour Forecast]
(steps, hr_mean, hr_std, accel_mag, load, mask) │
                                                 │
[Static Lab Profile (9 Channels)] ───────────────┘
```

### A. Detailed Evaluation:
* **Scientific Justification:** Modern recurrent neural networks (GRU/LSTM) possess high representational capacity to learn non-linear lag dynamics between physical exertion bursts and delayed glucose declines without requiring rigid parametric ODE assumptions.
* **Implementation Complexity:** **LOW-MEDIUM**. Involves expanding input dimension from 22 to 28 channels, adding dropout regularization, and fitting on synchronized OhioT1DM sequences.
* **Required Assumptions:** Minimal physiological assumptions; assumes the network learns temporal convolution of exertion over historical windows.
* **Dataset Support:** Supported by both OhioT1DM (12 patients, 8 weeks) and D1NAMO.
* **Overfitting Risk:** **MODERATE**. With 12 patients in OhioT1DM, strict patient-disjoint regularization (dropout $=0.25$, weight decay $=10^{-4}$, early stopping) is mandatory to prevent memorization of individual subject motion profiles.
* **Cohort Support Verdict:** Supported by OhioT1DM's $>650\text{ patient-days}$ of longitudinal sequence windows.

---

## 3. Option B: Physiology-Aware Exercise Digital Twin

```
[Wearable Activity Telemetry] ──> [Exercise Compartment E_1, E_2]
                                         │
                                         ▼ (Non-insulin clearance: - k_ex * E_2 * G)
[Gut S_1, S_2] ──> [Plasma Glucose G_p] <── [Insulin X] <── [Subcutaneous I_sc, I_p]
                                         │
                                         ▼
               [Differentiable RK4 Dynamic State Integrator]
```

### A. Detailed Evaluation:
* **Scientific Justification:** Derived from the physiological literature (e.g. Roy & Parker, *IEEE TBME 2007*; Dalla Man et al., *IEEE TBME 2009*; Breton, *J Diabetes Sci Technol 2008*). Adds an exercise active tissue compartment $E(t)$ that drives non-insulin-mediated clearance:
  $$\frac{dG_p}{dt} = \text{Gut}(t) + \text{EGP}(t) - \left(k_1 + X(t) + k_{\text{ex}} E_2(t)\right) G_p(t)$$
  $$\frac{dE_1}{dt} = -\frac{1}{\tau_{\text{ex}}} E_1(t) + \text{Intensity}(t), \quad \frac{dE_2}{dt} = \frac{1}{\tau_{\text{ex}}} (E_1(t) - E_2(t))$$
* **Implementation Complexity:** **HIGH**. Requires adding 2 state variables ($E_1, E_2$), calibrating exercise sensitivity parameters ($k_{\text{ex}}, \tau_{\text{ex}}$) per patient, and enforcing numerical Lyapunov stability in differentiable RK4 integration.
* **Required Assumptions:** Assumes uniform muscle clearance kinetics across aerobic and anaerobic exercise; assumes linear intensity scaling with heart rate reserve.
* **Dataset Support:** Requires co-recorded continuous Heart Rate AND Steps (present in OhioT1DM 2018 cohort and D1NAMO; missing in OhioT1DM 2020 cohort).
* **Overfitting Risk:** **HIGH (Parameter Identifiability Risk)**. With limited exercise bouts per patient, calibrating $k_{\text{ex}}$ alongside baseline insulin sensitivity $S_I$ risks non-unique local minima (parameter confounding between exercise clearance and active insulin).
* **Cohort Support Verdict:** Demands caution. Calibration requires at least $5 - 10$ documented exercise bouts with high-contrast heart rate telemetry per patient.

---

## 4. Architectural Trade-off Summary Table

| Evaluation Criterion | Option A: Multimodal Neural Extension | Option B: Exercise Physiological Digital Twin |
|---|:---:|:---:|
| **Primary Mechanism** | High-capacity recurrent feature fusion | Mechanistic non-insulin muscle clearance ODE |
| **New Model Parameters** | $+1,536\text{ weights}$ (input linear projection) | $+4\text{ differential equations \& } 3\text{ ODE constants}$ |
| **ODE Compartment Count** | **6 (Unchanged from V1)** | **8 (Adds } E_1, E_2 \text{ exercise transit)}$ |
| **Identifiability Risk** | Low (Trained via standard backprop) | **High (Confounding between } S_I \text{ and } k_{\text{ex}}\text{)}$ |
| **Missing Wearable Resilience** | High (Masked channel defaults to zero) | Moderate (Requires conditional ODE bypass) |
| **Counterfactual Workout Simulation** | Weak (Black-box response) | **Strong (Can simulate "What if I run for 30m?")** |
| **Recommended Staging** | **PHASE 7C.1 (IMMEDIATE TARGET)** | **PHASE 7C.2 (ADVANCED STAGE)** |

---

## 5. Scientific Recommendation on Additional ODE Compartments

> [!IMPORTANT]
> **GOVERNANCE DECISION:**  
> An 8-compartment ODE should **NOT be deployed prematurely** until the data access for OhioT1DM is secured and empirical feature-level neural validation (Option A) confirms significant predictive gain.  
> Option A should serve as the initial validation step; once exercise predictive signal is statistically confirmed, the mechanistic exercise ODE compartment (Option B) can be calibrated safely.

---
*Certified for Phase 7C architecture options.*
