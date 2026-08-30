# GlucoShield — Phase 6 Robustness & Stress Testing Report
**Document ID:** `GLUCOSHIELD-RPT-PHASE6-ROB-001`  
**Timestamp:** 2026-08-28T15:53:00 Local Time  
**Author:** Lead Deep Learning & Physiological Systems Engineer  
**Mode:** **INFERENCE-ONLY CONTROLLED STRESS TESTS**  
**Status:** **ROBUSTNESS AUDIT COMPLETE**  

---

## 1. Executive Summary

This report documents the robustness audit of the locked **GlucoShield Hybrid Forecaster (Seed 7)** against real-world clinical and hardware imperfections.

The evaluation was performed strictly on **perturbed copies** of the frozen test partition without altering original data or fine-tuning weights:
* **CGM Sensor Gaussian Noise:** Evaluated at $\sigma \in \{5, 10, 15, 20\}\text{ mg/dL}$.
* **Sensor Disconnections / Dropouts:** Evaluated at $15\text{m}, 30\text{m}, 60\text{m}, 120\text{m}$ using strictly causal backward zero-order hold.
* **Meal Carbohydrate Uncertainty:** Evaluated at $-50\%, -30\%, +30\%, +50\%$, and completely unlogged meals ($100\%$ missed meal).
* **Insulin Timing Uncertainty:** Evaluated at $\pm 15\text{m}$ and $\pm 30\text{m}$ timestamp jitter.

---

## 2. Robustness Stress Testing Results Table

| Stress Dimension | Perturbation Severity / Parameter | Test MAE (mg/dL) | Test RMSE (mg/dL) | Clarke Zone A+B (%) | Degradation vs. Clean Baseline (%) | Clinical Safety Assessment |
|---|---|:---:|:---:|:---:|:---:|---|
| **Clean Baseline** | No Perturbation | **$24.15$** | **$34.79$** | **$95.43\%$** | **$0.0\%$** | Optimal Benchmark |
| **CGM Noise** | $\sigma = 5.0\text{ mg/dL}$ (Minor Sensor Noise) | $26.02$ | $36.09$ | $94.96\%$ | $+7.8\%$ | Highly Resilient |
| **CGM Noise** | $\sigma = 10.0\text{ mg/dL}$ (Moderate Noise) | $29.59$ | $39.16$ | $94.48\%$ | $+22.5\%$ | Moderate Degradation |
| **CGM Noise** | $\sigma = 15.0\text{ mg/dL}$ (Severe Sensor Artifacts) | $32.80$ | $42.52$ | $93.85\%$ | $+35.8\%$ | Noticeable Softening |
| **CGM Noise** | $\sigma = 20.0\text{ mg/dL}$ (Extreme Sensor Fault) | $35.39$ | $45.29$ | $93.36\%$ | $+46.6\%$ | Failure Boundary |
| **Sensor Dropout** | $15\text{ min Gap}$ (1 step hold) | $25.90$ | $36.79$ | $94.93\%$ | $+7.3\%$ | Highly Resilient |
| **Sensor Dropout** | $30\text{ min Gap}$ (2 step hold) | $26.91$ | $37.98$ | $94.54\%$ | $+11.4\%$ | Safe Degradation |
| **Sensor Dropout** | $60\text{ min Gap}$ (4 step hold) | $28.55$ | $39.94$ | $93.90\%$ | $+18.3\%$ | Moderate Degradation |
| **Sensor Dropout** | $120\text{ min Gap}$ (8 step hold) | $30.24$ | $41.90$ | $93.16\%$ | $+25.2\%$ | Extended Hold Failure |
| **Meal Uncertainty** | $-30\%\text{ Underestimated Carbs}$ | $25.49$ | $36.85$ | $95.22\%$ | $+5.6\%$ | Robust ($\text{Clarke} > 95\%$) |
| **Meal Uncertainty** | $+30\%\text{ Overestimated Carbs}$ | $25.63$ | $35.61$ | $94.96\%$ | $+6.2\%$ | Robust ($\text{Clarke} \approx 95\%$) |
| **Meal Uncertainty** | $-50\%\text{ Severe Carb Under-log}$ | $27.91$ | $39.87$ | $94.71\%$ | $+15.6\%$ | Moderate Degradation |
| **Meal Uncertainty** | $+50\%\text{ Severe Carb Over-log}$ | $27.66$ | $37.28$ | $94.46\%$ | $+14.6\%$ | Moderate Degradation |
| **Meal Uncertainty** | **$100\%\text{ Missed Meal (Unlogged)}$** | **$36.52$** | **$50.40$** | **$92.49\%$** | **$+51.2\%$** | **Primary Failure Mode** |
| **Insulin Jitter** | $-15\text{ min Bolus Early}$ | $24.83$ | $35.65$ | $95.45\%$ | $+2.8\%$ | Highly Stable |
| **Insulin Jitter** | $+15\text{ min Bolus Late}$ | $24.14$ | $34.77$ | $95.42\%$ | $-0.0\%$ | Perfect Stability |
| **Insulin Jitter** | $-30\text{ min Bolus Early}$ | $25.46$ | $36.25$ | $95.29\%$ | $+5.4\%$ | High Stability |
| **Insulin Jitter** | $+30\text{ min Bolus Late}$ | $24.16$ | $34.78$ | $95.40\%$ | $+0.1\%$ | High Stability |

---

## 3. Scientific Analysis of Failure Boundaries

1. **Unlogged Meals (Primary Failure Mode):**  
   When a patient consumes a meal without logging it ($100\%$ missed meal), the model experiences its largest single degradation ($+51.2\%$ MAE increase from $24.15 \rightarrow 36.52\text{ mg/dL}$). This confirms that postprandial glucose dynamics are primarily driven by exogenous carbohydrate intake, highlighting the urgent need for **automated food vision** in future phases.
2. **Insulin Timing Resilience:**  
   Insulin timing jitter of $\pm 15\text{m}$ to $\pm 30\text{m}$ causes minimal degradation ($<5.4\%$), demonstrating that the 24-hour recurrent hidden state and exponential clearance kinetics gracefully absorb modest timing errors.
3. **Sensor Dropout Boundaries:**  
   Short dropouts ($15\text{m} - 30\text{m}$) cause minimal disruption ($+7.3\%$ to $+11.4\%$), while gaps exceeding 1 hour require explicit clinical warnings in the companion UI.

---

## 4. Associated Figures & Manifest

* **Figure 5:** [`evaluation/phase6/figures/fig5_robustness_degradation_curves.png`](file:///D:/ML%20PROJECT/evaluation/phase6/figures/fig5_robustness_degradation_curves.png)
* **Results JSON:** [`evaluation/phase6/results/robustness_stress_results.json`](file:///D:/ML%20PROJECT/evaluation/phase6/results/robustness_stress_results.json)

---
*Certified under Phase 6 robustness testing protocol.*
