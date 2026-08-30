# GlucoShield — Digital Twin Step-by-Step Implementation Plan
**Document ID:** `GLUCOSHIELD-PLAN-DAY4-TWIN-001`  
**Status:** READY FOR REVIEW  
**Companion Architecture Spec:** [`DAY4_DIGITAL_TWIN_ARCHITECTURE.md`](file:///D:/ML%20PROJECT/reports/DAY4_DIGITAL_TWIN_ARCHITECTURE.md)  

---

## 1. Overview & Objective

This document outlines the phased, test-driven implementation plan for building, calibrating, verifying, and fusing the **GlucoShield Mechanistic Digital Twin & Physiology Engine** with the locked `GLUCOSHIELD_NEURAL_FORECASTER_V1`.

Implementation will strictly maintain dataset locks, avoid test-set snooping, enforce physiological parameter constraints, and execute on the **NVIDIA GeForce RTX 4050 Laptop GPU**.

---

## 2. Step-by-Step Implementation Roadmap

```
Step 1: Core ODE Engine & Compartments
         (G, G_CGM, X, I, S1, S2, Q1, Q2)
                    │
                    ▼
Step 2: Differentiable Numerical Integrator (RK4)
         (1-minute micro-stepping with state projection)
                    │
                    ▼
Step 3: Synthetic & Clinical Unit Testing
         (Physiological plausibility, mass conservation, monotonic bolus response)
                    │
                    ▼
Step 4: Static Biomarker Prior Estimator
         (Mapping 9 static features -> physiological parameter prior)
                    │
                    ▼
Step 5: Differentiable 24-Hour Online Calibrator
         (MHE / EKF parameter calibration on 96-timestep history)
                    │
                    ▼
Step 6: Counterfactual "What-If" Simulator API
         (Scenario testing: meal dose, insulin timing, rescue carbs)
                    │
                    ▼
Step 7: Adaptive Gated Hybrid Fusion Engine
         (Fusing Neural Forecaster V1 + Digital Twin with horizon gating)
                    │
                    ▼
Step 8: Standalone & Hybrid Evaluation Benchmark
         (Validation selection -> Single frozen test set evaluation)
```

---

## 3. Detailed Milestone Tasks

### Milestone 1: Core ODE Compartment Definitions (`physiology/compartments.py`)
- [ ] Implement `MetabolicState` container holding:
  - $\mathbf{x} = [G, G_{\text{CGM}}, X, I, S_1, S_2, Q_1, Q_2]^T$
- [ ] Implement rate-of-change function $\mathbf{f}(\mathbf{x}, u_{\text{ins}}, D; \boldsymbol{\theta})$ for:
  - 2-compartment gut absorption ($Q_1 \to Q_2 \to R_a$)
  - 2-compartment subcutaneous insulin absorption ($S_1 \to S_2 \to U_I$)
  - Plasma insulin & remote insulin action dynamics ($I, X$)
  - Plasma glucose balance with hepatic suppression ($G$)
  - Subcutaneous interstitial sensor diffusion lag ($G_{\text{CGM}}$)
- [ ] Implement parameter tensor class `PhysiologicalParameters` with strict clamping boundaries ($\boldsymbol{\theta}_{\text{min}}, \boldsymbol{\theta}_{\text{max}}$).

### Milestone 2: Differentiable Integrator (`physiology/integrator.py`)
- [ ] Implement batched 4th-Order Runge-Kutta (`RK4Integrator`) operating on PyTorch GPU tensors.
- [ ] Set micro-step size $h = 1.0\text{ minute}$ ($15$ internal micro-steps per $15$-minute CGM interval).
- [ ] Implement zero-order hold handling of meal ($D$) and insulin ($u$) inputs across micro-steps.
- [ ] Add state non-negativity projection and physiological glucose clamping ($G \ge 20\text{ mg/dL}$).

### Milestone 3: Physiology Verification & Unit Tests (`experiments/test_physiology_engine.py`)
- [ ] **Test A (Basal Equilibrium)**: Zero meals, basal insulin $\to$ glucose stays at $G_b \pm 5\text{ mg/dL}$.
- [ ] **Test B (Meal Postprandial Curve)**: 50g carb pulse $\to$ realistic glucose rise peaking at $45-75\text{ min}$, returning to baseline.
- [ ] **Test C (Bolus Clearance Curve)**: 5U insulin pulse $\to$ gradual glucose drop with nadir at $60-120\text{ min}$.
- [ ] **Test D (Monotonicity Check)**: 10U bolus must produce strictly lower nadir than 5U bolus for any identical meal.
- [ ] **Test E (Mass Conservation)**: Sum of integrated $R_a(t)$ matches ingested carbs times bioavailability $f$.

### Milestone 4: Biomarker Prior Parameter Estimator (`physiology/priors.py`)
- [ ] Build `BiomarkerPriorNetwork`: PyTorch neural module ($9 \to 32 \to 10$) mapping static clinical features ($\text{Age}, \text{BMI}, \text{HbA1c}, \text{C-peptide}, \text{is\_t1dm}$) to initial physiological parameters $\boldsymbol{\theta}_{\text{prior}}$.
- [ ] Apply sigmoid scaling to map outputs strictly into bounded clinical ranges.

### Milestone 5: Differentiable Online Calibrator (`physiology/calibrator.py`)
- [ ] Build `MovingHorizonCalibrator` utilizing the preceding 24-hour history window ($96$ timesteps).
- [ ] Optimize parameter adjustments $\Delta\boldsymbol{\theta}$ using AdamW / L-BFGS over $20$ iterations on GPU.
- [ ] Benchmark execution latency to ensure calibration completes in $<50\text{ ms}$ per patient window.

### Milestone 6: Counterfactual Simulator API (`physiology/simulator.py`)
- [ ] Implement `simulate_scenario(patient_state, parameters, intervention_plan, horizon_minutes=300)`.
- [ ] Support multiple parallel hypothetical trajectories (e.g., baseline vs alternative doses).
- [ ] Compute clinical summary metrics for each scenario:
  - $\text{Nadir}$, $\text{Time-to-Nadir}$, $\text{Peak}$, $\text{Time-to-Peak}$
  - $\text{Probability of Hypoglycemia } (P(G < 70\text{ mg/dL}))$
  - $\text{Time in Range } (70 - 180\text{ mg/dL})$

### Milestone 7: Adaptive Gated Hybrid Fusion (`physiology/hybrid_fusion.py`)
- [ ] Build `GlucoShieldHybridForecaster`:
  - Neural Branch: `GLUCOSHIELD_NEURAL_FORECASTER_V1` (Frozen weights)
  - Mechanistic Branch: `CalibratedDigitalTwin`
  - Fusion Gate: Computes horizon-dependent weighting vector $\boldsymbol{\alpha} \in \mathbb{R}^{20}$
- [ ] Train fusion gate parameters strictly on validation set.

### Milestone 8: Comprehensive Evaluation & Reporting (`experiments/run_digital_twin_eval.py`)
- [ ] Run full comparative evaluation across validation cohort for model selection.
- [ ] Perform single, locked evaluation on frozen test partition ($N=4,113$ sequences).
- [ ] Generate `DAY4_DIGITAL_TWIN_REPORT.md` with:
  - Trajectory metrics (Overall, Horizon-wise 15m to 5h, Clarke Error Grid Zones)
  - Macro-patient metrics and T1DM/T2DM subgroup breakdown
  - Direct comparison against Day 2 Ridge and Day 3 Neural Forecaster V1
  - Counterfactual simulation case studies and clinical verification figures.

---

## 4. Verification Checkpoints & Success Criteria

| Evaluation Milestone | Target Performance Criteria | Baseline to Beat |
|---|---|---|
| **Short Horizons ($15\text{m}-1\text{h}$)** | $\text{RMSE} \le 25.5\text{ mg/dL}$ | Ridge Baseline ($25.37\text{ mg/dL}$) |
| **Long Horizons ($2\text{h}-5\text{h}$)** | $\text{RMSE} \le 38.5\text{ mg/dL}$ | Standalone Neural V1 ($39.64\text{ mg/dL}$ at 4h, $41.77\text{ mg/dL}$ at 5h) |
| **Overall Test RMSE** | $\text{RMSE} \le 34.0\text{ mg/dL}$ | Standalone Neural V1 ($34.90\text{ mg/dL}$) |
| **Clinical Safety** | $\text{Clarke Zone A+B} \ge 95.5\%$ | Standalone Neural V1 ($95.28\%$) |
| **4-Hour Hypo Sensitivity** | $\ge 60.0\%$ | Standalone Neural V1 ($56.13\%$) |
| **Calibration Latency** | $<50\text{ ms}$ per sequence on RTX 4050 | Real-time clinical requirement |
