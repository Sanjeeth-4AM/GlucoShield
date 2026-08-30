# GlucoShield — Phase 7C: Final Multimodal Activity Ablation Report
**Document ID:** `GLUCOSHIELD-RPT-PHASE7C-FINAL-001`  
**Certified Protocol Version:** `v2.1.0`  
**Timestamp:** 2026-08-28T19:40:00 Local Time  
**Author:** Lead Deep Learning & Physiological Systems Engineer  
**Status:** **PHASE 7C BENCHMARK COMPLETED & CERTIFIED (V1 FROZEN)**  

---

## 1. Executive Summary & Scientific Verdict

Under Phase 7C Protocol v2.1.0, an exhaustive **13-Fold Leave-One-Patient-Out Cross-Validation (LOOCV)** ablation experiment was executed on the published **Glucdict Dataset** ($N = 13$ participants, 11,903 15-minute windows) to test whether augmenting the 22-channel dynamic baseline with 6 continuous wearable activity telemetry channels (Hardware Steps, Optical PPG Heart Rate, 3D Accelerometer Magnitude, Active Load, and Coverage Flags) improves 5-hour glucose forecasting.

### Benchmark Outcome:
* **Baseline Model A (22 Dynamic Channels):** Out-of-fold Mean $\text{MAE} = \mathbf{12.72\text{ mg/dL}}$
* **Multimodal Model B (28 Multimodal Channels):** Out-of-fold Mean $\text{MAE} = \mathbf{12.93\text{ mg/dL}}$
* **Overall $\Delta\text{MAE} (\text{Model A} - \text{Model B})$:** $\mathbf{-0.21\text{ mg/dL}}$ ($\mathbf{-1.64\%}$)
* **Active & Recovery Horizon $\Delta\text{MAE}$:** $\mathbf{-0.23\text{ mg/dL}}$
* **Paired Two-Sided Wilcoxon Signed-Rank Test ($N = 13$):** $\mathbf{W = 34.0, \; p = 0.454834}$ ($p \ge 0.05$, **NOT STATISTICALLY SIGNIFICANT**)
* **Scientific Verdict:** **NULL HYPOTHESIS RETAINED / REJECTION RULE TRIGGERED**. Wearable activity telemetry does not confer a statistically significant or clinically meaningful predictive benefit over CGM dynamics for endogenous glucose forecasting in free-living conditions.

---

## 2. Participant-Level Out-of-Fold Error Observations ($N = 13$)

| Fold Index | Held-Out Test Subject | Validation Subject | Training Cohort Size | Model A MAE ($\text{mg/dL}$) | Model B MAE ($\text{mg/dL}$) | $\Delta\text{MAE} (\text{A} - \text{B})$ | Percent Change | Active Window $\Delta\text{MAE}$ |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Fold 00** | **User8** | User6 | 11 pts | $14.98$ | $15.14$ | $-0.16\text{ mg/dL}$ | $-1.06\%$ | $-0.26\text{ mg/dL}$ |
| **Fold 01** | **User6** | User1 | 11 pts | $10.79$ | $10.75$ | $+0.04\text{ mg/dL}$ | $+0.38\%$ | $+0.13\text{ mg/dL}$ |
| **Fold 02** | **User1** | User5 | 11 pts | $14.89$ | $14.42$ | $+0.47\text{ mg/dL}$ | $+3.17\%$ | $-0.05\text{ mg/dL}$ |
| **Fold 03** | **User5** | User15 | 11 pts | $9.00$ | $9.69$ | $-0.69\text{ mg/dL}$ | $-7.67\%$ | $-0.89\text{ mg/dL}$ |
| **Fold 04** | **User15** | User12 | 11 pts | $13.39$ | $15.31$ | $-1.92\text{ mg/dL}$ | $-14.30\%$ | $-2.31\text{ mg/dL}$ |
| **Fold 05** | **User12** | User10 | 11 pts | $9.64$ | $9.54$ | $+0.11\text{ mg/dL}$ | $+1.10\%$ | $+0.10\text{ mg/dL}$ |
| **Fold 06** | **User10** | User9 | 11 pts | $10.45$ | $10.66$ | $-0.21\text{ mg/dL}$ | $-1.97\%$ | $-0.18\text{ mg/dL}$ |
| **Fold 07** | **User9** | User14 | 11 pts | $12.56$ | $12.41$ | $+0.15\text{ mg/dL}$ | $+1.16\%$ | $+0.01\text{ mg/dL}$ |
| **Fold 08** | **User14** | User4 | 11 pts | $29.48$ | $29.01$ | $+0.47\text{ mg/dL}$ | $+1.60\%$ | $+0.28\text{ mg/dL}$ |
| **Fold 09** | **User4** | User7 | 11 pts | $12.57$ | $13.49$ | $-0.92\text{ mg/dL}$ | $-7.33\%$ | $-0.75\text{ mg/dL}$ |
| **Fold 10** | **User7** | User13 | 11 pts | $6.22$ | $6.70$ | $-0.48\text{ mg/dL}$ | $-7.77\%$ | $-0.11\text{ mg/dL}$ |
| **Fold 11** | **User13** | User3 | 11 pts | $10.77$ | $10.47$ | $+0.31\text{ mg/dL}$ | $+2.84\%$ | $+0.85\text{ mg/dL}$ |
| **Fold 12** | **User3** | User8 | 11 pts | $10.67$ | $10.55$ | $+0.12\text{ mg/dL}$ | $+1.11\%$ | $+0.22\text{ mg/dL}$ |
| **Mean** | — | — | — | **$12.72$** | **$12.93$** | **$-0.21\text{ mg/dL}$** | **$-1.64\%$** | **$-0.23\text{ mg/dL}$** |

---

## 3. Pre-Registered Hypothesis Testing & Decision Criteria

```
================================================================================
PRE-REGISTERED HYPOTHESIS EVALUATION MATRIX
================================================================================
Criterion 1: Overall Mean Delta MAE >= +1.0 mg/dL
  --> Result: -0.21 mg/dL (FAILED: Did not achieve +1.0 mg/dL improvement)

Criterion 2: Active & Recovery Horizon Delta MAE >= +3.0 mg/dL
  --> Result: -0.23 mg/dL (FAILED: Did not achieve +3.0 mg/dL improvement)

Criterion 3: Statistical Significance (Wilcoxon Signed-Rank p < 0.05)
  --> Result: W = 34.0, p = 0.454834 (FAILED: p >= 0.05)

Criterion 4: Pre-Registered Rejection Threshold (Delta MAE < 0.5 mg/dL or p >= 0.05)
  --> Result: TRIGGERED (Delta MAE = -0.21 mg/dL < 0.5 mg/dL; p = 0.455 >= 0.05)
================================================================================
FINAL BENCHMARK DECISION:
REJECT HYPOTHESIS THAT MULTIMODAL ACTIVITY TELEMETRY IMPROVES ENDOGENOUS FORECASTING
================================================================================
```

---

## 4. Physiological Rationale & Scientific Interpretation

1. **Endogenous Homeostatic Counter-Regulation:** In non-diabetic cohorts, physical exercise triggers rapid endogenous hepatic glycogenolysis and gluconeogenesis, buffering glucose fluctuations without the severe hypoglycemia seen when exogenous insulin is active.
2. **Signal-to-Noise in Optical PPG & Consumer Accelerometry:** Optical PPG sensors on consumer smartwatches suffer from motion artifacts during intense physical exercise. Introducing high-frequency noisy sensor features without tight physiological ODE priors increases model parameter count and generalization variance across unseen individuals.
3. **Clinical Domain Contrast:** In Type 1 Diabetes (as modeled in GlucoShield V1), physical activity accelerates exogenous insulin clearance and increases peripheral insulin sensitivity ($S_I$), causing precipitous drops that require insulin-informed modeling. In contrast, in healthy free-living subjects, glucose remains tightly bounded ($70\text{–}140\text{ mg/dL}$), rendering CGM autoregressive dynamics the dominant predictor.

---

## 5. Governance & Artifact Preservation

* **GlucoShield V1 Core Remains Untouched:**
  * Neural Forecaster V1 (`models/glucoshield_neural_best.pt`) — **100% Bitwise Intact**.
  * Hybrid Forecaster (`models/glucoshield_hybrid_best.pt`) — **100% Bitwise Intact**.
  * ODE Digital Twin, Decision Engine, and Phase 6 Benchmarks — **100% Bitwise Intact**.
* **Phase 7C Checkpoints & Manifests Preserved:**
  * All 26 fold checkpoints: `activity_telemetry/experiments/checkpoints/phase7c_fold_*.pt`.
  * Results Manifest: `activity_telemetry/experiments/results/phase7c_ablation_results.json`.
  * Results Tabular CSV: `activity_telemetry/experiments/results/phase7c_ablation_results.csv`.
* **Automated Unit Tests:** **81 / 81 Tests Passing ($100.0\%$)**.

---
*Certified under Phase 7C Final Ablation Reporting Protocol.*
