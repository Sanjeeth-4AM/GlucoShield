# GlucoShield — Day 4 Digital Twin & Hybrid Model Selection Report
**Document ID:** `GLUCOSHIELD-RPT-DAY4-SEL-001`  
**Timestamp:** 2026-08-28T15:32:00 Local Time  
**Author:** Lead AI/Physiological Systems Engineer  
**Dataset Split:** Validation Set (`data/final/meta_val.csv`, $N=4,585$ sequences, 17 patients: 2 T1DM + 15 T2DM)  
**Status:** **SELECTION COMPLETE & LOCKED**  

---

## 1. Executive Summary

This report documents the rigorous model selection protocol executed strictly on the **Validation Set** ($N=4,585$ sequences from 17 disjoint patients). The goal was to benchmark:
1. Standalone Mechanistic Digital Twin configurations (Population ODE vs. Tier 1 Prior ODE vs. Tier 1+2 Moving Horizon Calibrated ODE).
2. Differentiable Adaptive Hybrid Forecaster configurations across three independent random initialization seeds (Seeds 42, 123, 7).

---

## 2. Standalone Mechanistic Digital Twin Validation Results

The 6-compartment physiological differential equation system was evaluated in standalone forward simulation mode ($20\text{ future steps} = 5\text{ hours}$) across three levels of personalization:

| Architecture / Level | Val RMSE (mg/dL) | Val MAE (mg/dL) | Clarke Zone A+B (%) | Key Scientific Finding |
|---|:---:|:---:|:---:|---|
| **Level 0: Population ODE** | $49.74$ | $34.01$ | $91.32\%$ | Uses fixed population physiological parameters ($\bar{S}_I, \bar{V}_G, \bar{k}_a, \dots$). Serves as the uncalibrated first-principles baseline. |
| **Level 1: Biomarker Prior ODE** | **$46.58$** | $34.33$ | $90.85\%$ | Tier 1 `BiomarkerPriorNetwork` personalizes baseline metabolic parameters directly from 9 static clinical biomarkers. **Gain: $+3.16\text{ mg/dL}$ RMSE improvement over population**. |
| **Level 2: Calibrated ODE (MHE)** | $46.68$ | $34.27$ | $90.82\%$ | Tier 1 Prior + Tier 2 causal Moving Horizon Estimator (MHE) optimizing historical loss over 24-hour history. |

### Scientific Finding on Standalone ODE:
As established in the project charter, pure standalone ODEs have higher overall trajectory RMSE ($46.58\text{ mg/dL}$) than neural networks ($31.01\text{ mg/dL}$) because simplified compartment models cannot capture arbitrary individual lifestyle habits, unlogged snacks, or sensor calibration shifts. However, the ODE maintains strict mass conservation and enables counterfactual simulation.

---

## 3. Hybrid Fusion Multi-Seed Validation Stability (3 Seeds)

The `GlucoShieldHybridForecaster` integrates the frozen `GlucoShieldMultiTaskRNN` (GRU-128) with the differentiable RK4 Digital Twin via an `AdaptiveFusionGate` ($\boldsymbol{\alpha}(k)$) and `residual_head`:

$$\hat{\mathbf{y}}_{\text{hybrid}}(k) = \alpha(k) \hat{\mathbf{y}}_{\text{neural}}(k) + (1 - \alpha(k)) \hat{\mathbf{y}}_{\text{ODE}}(k) + \hat{\mathbf{r}}_{\text{res}}(k)$$

| Seed Index | Random Seed | Best Epoch | Train Loss | Val RMSE (mg/dL) | Val MAE (mg/dL) | Clarke Zone A+B (%) | Training Time |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | **Seed 42** | Epoch 15 | $18.7980$ | $31.02$ | $21.19$ | $95.53\%$ | $10.45\text{s}$ |
| 2 | **Seed 123** | Epoch 13 | $18.7782$ | $30.98$ | $21.17$ | $95.54\%$ | $7.22\text{s}$ |
| 3 | **Seed 7 (Winner)** | **Epoch 8** | **$18.8319$** | **$30.93$** | **$21.16$** | **$95.55\%$** | **$6.90\text{s}$** |
| **Summary** | **3-Seed Mean** | — | — | **$30.98 \pm 0.04$** | **$21.17 \pm 0.01$** | **$95.54 \pm 0.01\%$** | **High Stability** |

---

## 4. Final Model Selection Decision & Locking

* **Winner:** **Seed 7** achieved the lowest validation RMSE of **$30.93\text{ mg/dL}$** (and lowest MAE of $21.16\text{ mg/dL}$).
* **Locked Checkpoint:** [`models/glucoshield_hybrid_best.pt`](file:///D:/ML%20PROJECT/models/glucoshield_hybrid_best.pt).
* **Rationale:** Seed 7 demonstrates optimal multi-horizon gate convergence with rapid training stability and peak Clarke Zone A+B clinical safety ($95.55\%$).

---
*Certified under locked Day 4 validation protocol.*
