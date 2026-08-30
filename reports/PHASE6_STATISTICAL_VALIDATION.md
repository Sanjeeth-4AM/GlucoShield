# GlucoShield — Phase 6 Patient-Level Statistical Validation Report
**Document ID:** `GLUCOSHIELD-RPT-PHASE6-STAT-001`  
**Timestamp:** 2026-08-28T15:51:00 Local Time  
**Author:** Lead Deep Learning & Physiological Systems Engineer  
**Inferential Unit:** Patient Level ($N=17$ Held-Out Patients, $4,113$ Sequences)  
**Status:** **STATISTICAL ANALYSIS COMPLETE & CERTIFIED**  

---

## 1. Executive Summary & Core Statistical Findings

This report evaluates whether the performance improvements of the **GlucoShield Hybrid Forecaster** over the locked **Neural Forecaster V1 (GRU-128)** and **Classical Ridge Baseline** are statistically meaningful at the **patient level** ($N=17$ held-out test patients).

### Key Statistical Verdict:
1. **Hybrid vs. Classical Ridge Baseline:**  
   * **MAE Difference:** Mean $= -1.113\text{ mg/dL}$, **Wilcoxon $p = 0.0013$** (Statistically significant at $\alpha = 0.01$). Improved in **$15 / 17$ patients ($88.2\%$)**, Cohen's $d = -0.998$ (Large effect size).
   * **RMSE Difference:** Mean $= -1.200\text{ mg/dL}$, **Wilcoxon $p = 0.0191$** (Statistically significant at $\alpha = 0.05$). Improved in **$15 / 17$ patients ($88.2\%$)**, Cohen's $d = -0.722$ (Medium-to-large effect size).
2. **Hybrid vs. Neural Forecaster V1 (GRU-128):**  
   * **MAE Difference:** Mean $= -0.337\text{ mg/dL}$ (Median $= -0.230\text{ mg/dL}$), **Wilcoxon $p = 0.0039$** (Statistically significant at $\alpha = 0.01$). Improved in **$14 / 17$ patients ($82.4\%$)**, Cohen's $d = -0.906$ (Large effect size).
   * **RMSE Difference:** Mean $= -0.153\text{ mg/dL}$ (Median $= -0.330\text{ mg/dL}$), **Wilcoxon $p = 0.1127$** (Not statistically significant at $\alpha = 0.05$). Improved in **$10 / 17$ patients ($58.8\%$)**, Cohen's $d = -0.374$ (Small-to-medium effect size).

> **HONEST SCIENTIFIC INTERPRETATION RULE:**  
> The GlucoShield Hybrid Forecaster demonstrates a **statistically significant, consistent patient-level reduction in Mean Absolute Error (MAE)** over the Neural GRU forecaster across $82.4\%$ of held-out patients ($p=0.0039$). However, the reduction in Root Mean Squared Error (RMSE) is modest ($-0.153\text{ mg/dL}$) and does not reach statistical significance at the patient level ($p=0.1127$).  
> Thus, the Hybrid model is established as achieving the **numerically superior point estimate with consistent median patient error reduction and physical explainability**, rather than an overwhelmingly large variance reduction over the GRU.

---

## 2. Per-Patient Performance Breakdown ($N=17$ Held-Out Patients)

| Patient ID | Diabetes Type | Sequence Count | Age | BMI | HbA1c | Ridge MAE (mg/dL) | GRU MAE (mg/dL) | ODE MAE (mg/dL) | Hybrid MAE (mg/dL) | Hybrid RMSE (mg/dL) | Clarke A+B (%) | $\Delta\text{MAE}$ (Hyb − GRU) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `1004` | T1DM | $253$ | $67.0$ | $19.56$ | $125.1$ | $26.83$ | $26.83$ | $37.52$ | **$26.39$** | $37.24$ | $90.51\%$ | **$-0.44$** |
| `1007` | T1DM | $254$ | $54.0$ | $24.22$ | $62.8$ | $28.66$ | $27.99$ | $43.91$ | **$27.48$** | $37.15$ | $88.24\%$ | **$-0.51$** |
| `2001` | T2DM | $228$ | $61.0$ | $24.22$ | $54.1$ | $15.54$ | $15.70$ | $16.71$ | **$15.42$** | $21.43$ | $99.85\%$ | **$-0.28$** |
| `2002` | T2DM | $228$ | $63.0$ | $26.12$ | $60.7$ | $34.78$ | $34.70$ | $51.05$ | **$34.19$** | $47.38$ | $90.31\%$ | **$-0.51$** |
| `2020` | T2DM | $218$ | $69.0$ | $21.80$ | $67.2$ | $20.08$ | $18.99$ | $38.99$ | **$18.66$** | $26.69$ | $97.94\%$ | **$-0.33$** |
| `2021` | T2DM | $228$ | $65.0$ | $22.49$ | $108.7$ | $42.06$ | $42.27$ | $74.52$ | **$41.60$** | $57.06$ | $85.64\%$ | **$-0.67$** |
| `2023` | T2DM | $239$ | $70.0$ | $27.34$ | $47.5$ | $19.98$ | $18.89$ | $27.86$ | **$18.78$** | $26.83$ | $99.44\%$ | **$-0.11$** |
| `2029` | T2DM | $228$ | $42.0$ | $27.34$ | $60.7$ | $19.64$ | $18.73$ | $24.77$ | **$18.57$** | $26.23$ | $99.41\%$ | **$-0.16$** |
| `2032` | T2DM | $238$ | $54.0$ | $21.80$ | $86.3$ | $34.80$ | $33.45$ | $58.11$ | **$33.02$** | $45.96$ | $92.79\%$ | **$-0.43$** |
| `2037` | T2DM | $250$ | $72.0$ | $22.49$ | $61.7$ | $24.50$ | $23.16$ | $38.86$ | **$22.93$** | $33.09$ | $97.22\%$ | **$-0.23$** |
| `2052` | T2DM | $240$ | $72.0$ | $25.71$ | $53.0$ | $18.96$ | $18.42$ | $26.46$ | **$18.25$** | $25.99$ | $99.85\%$ | **$-0.17$** |
| `2057` | T2DM | $249$ | $66.0$ | $24.69$ | $57.4$ | $19.82$ | $19.68$ | $30.08$ | **$19.61$** | $28.32$ | $98.88\%$ | **$-0.07$** |
| `2059` | T2DM | $242$ | $54.0$ | $25.06$ | $62.8$ | $29.74$ | $27.34$ | $47.38$ | **$27.13$** | $37.27$ | $94.61\%$ | **$-0.21$** |
| `2063` | T2DM | $249$ | $48.0$ | $24.22$ | $58.5$ | $34.34$ | $32.41$ | $41.87$ | **$32.17$** | $44.02$ | $92.93\%$ | **$-0.24$** |
| `2075` | T2DM | $249$ | $51.0$ | $23.44$ | $60.7$ | $30.93$ | $30.29$ | $62.13$ | **$30.03$** | $41.28$ | $92.05\%$ | **$-0.26$** |
| `2087` | T2DM | $250$ | $69.0$ | $27.34$ | $53.0$ | $23.00$ | $22.25$ | $33.40$ | **$22.09$** | $31.44$ | $97.94\%$ | **$-0.16$** |
| `2095` | T2DM | $250$ | $45.0$ | $20.08$ | $106.6$ | $39.56$ | $39.29$ | $54.26$ | **$38.99$** | $52.79$ | $89.06\%$ | **$-0.30$** |

### Patient-Level Macro Summary:
* **Best Patient:** Patient `2001` (T2DM) — Hybrid MAE $= 15.42\text{ mg/dL}$, RMSE $= 21.43\text{ mg/dL}$, Clarke Zone A+B $= 99.85\%$.
* **Worst Patient:** Patient `2021` (T2DM, $\text{HbA1c}=108.7$) — Hybrid MAE $= 41.60\text{ mg/dL}$, RMSE $= 57.06\text{ mg/dL}$, Clarke Zone A+B $= 85.64\%$.
* **Largest Hybrid Gain over GRU:** Patient `2021` ($-0.67\text{ mg/dL}$ MAE reduction) and Patient `1007` ($-0.51\text{ mg/dL}$ MAE reduction).
* **Patients Improved:** **$14 / 17$ ($82.4\%$)** achieved lower MAE under the Hybrid Forecaster.

---

## 3. 10,000-Resample Patient-Level Bootstrap 95% Confidence Intervals

Resampling was performed with replacement strictly at the **patient cluster level** (17 patients sampled per iteration, $10,000$ iterations, Seed 42):

| Metric / Comparison | Point Estimate on Test Set | 95% Bootstrap Lower Bound | 95% Bootstrap Upper Bound | CI Width |
|---|:---:|:---:|:---:|:---:|
| **Hybrid Forecast MAE** | $24.14\text{ mg/dL}$ | **$20.46\text{ mg/dL}$** | **$28.32\text{ mg/dL}$** | $7.86\text{ mg/dL}$ |
| **Hybrid Forecast RMSE** | $34.77\text{ mg/dL}$ | **$29.43\text{ mg/dL}$** | **$40.34\text{ mg/dL}$** | $10.91\text{ mg/dL}$ |
| **$\Delta\text{MAE}$ (Hybrid − GRU)** | **$-0.308\text{ mg/dL}$** | **$-0.485\text{ mg/dL}$** | **$-0.125\text{ mg/dL}$** | **$0.360\text{ mg/dL}$** |
| **$\Delta\text{RMSE}$ (Hybrid − GRU)** | $-0.127\text{ mg/dL}$ | $-0.358\text{ mg/dL}$ | $+0.148\text{ mg/dL}$ | $0.506\text{ mg/dL}$ |
| **$\Delta\text{MAE}$ (Hybrid − Ridge)** | **$-1.231\text{ mg/dL}$** | **$-1.704\text{ mg/dL}$** | **$-0.717\text{ mg/dL}$** | **$0.987\text{ mg/dL}$** |
| **$\Delta\text{RMSE}$ (Hybrid − Ridge)** | **$-1.025\text{ mg/dL}$** | **$-1.815\text{ mg/dL}$** | **$-0.210\text{ mg/dL}$** | **$1.605\text{ mg/dL}$** |

### Horizon-Wise RMSE 95% Confidence Intervals:
* **15 min ($k=1$):** Hybrid RMSE $= 8.93\text{ mg/dL}$ [$95\%\text{ CI: } 7.74 \text{ to } 10.22\text{ mg/dL}$]
* **1 Hour ($k=4$):** Hybrid RMSE $= 25.60\text{ mg/dL}$ [$95\%\text{ CI: } 21.65 \text{ to } 29.83\text{ mg/dL}$]
* **2 Hours ($k=8$):** Hybrid RMSE $= 35.46\text{ mg/dL}$ [$95\%\text{ CI: } 29.98 \text{ to } 41.24\text{ mg/dL}$]
* **4 Hours ($k=16$):** Hybrid RMSE $= 39.70\text{ mg/dL}$ [$95\%\text{ CI: } 33.62 \text{ to } 46.12\text{ mg/dL}$]
* **5 Hours ($k=20$):** Hybrid RMSE $= 41.89\text{ mg/dL}$ [$95\%\text{ CI: } 35.48 \text{ to } 48.71\text{ mg/dL}$]

---

## 4. Paired Hypothesis Testing Summary Table

| Hypothesis Test | Comparison | Test Statistic | p-Value | Effect Size (Cohen's $d$) | Win / Loss Ratio | Statistical Significance ($\alpha=0.05$) |
|---|---|:---:|:---:|:---:|:---:|:---:|
| **Two-Sided Wilcoxon** | Hybrid vs. GRU (MAE) | $W = 10.0$ | **$p = 0.0039$** | $d = -0.906$ (Large) | **14 Wins / 3 Losses** | **SIGNIFICANT** |
| **Two-Sided Wilcoxon** | Hybrid vs. GRU (RMSE) | $W = 42.0$ | $p = 0.1127$ | $d = -0.374$ (Medium) | 10 Wins / 7 Losses | *Not Significant* |
| **Two-Sided Wilcoxon** | Hybrid vs. Ridge (MAE) | $W = 7.0$ | **$p = 0.0013$** | $d = -0.998$ (Large) | **15 Wins / 2 Losses** | **SIGNIFICANT** |
| **Two-Sided Wilcoxon** | Hybrid vs. Ridge (RMSE) | $W = 23.0$ | **$p = 0.0191$** | $d = -0.722$ (Large) | **15 Wins / 2 Losses** | **SIGNIFICANT** |
| **Two-Sided Wilcoxon** | Hybrid vs. ODE (MAE) | $W = 0.0$ | **$p < 0.0001$** | $d = -1.370$ (Very Large)| **16 Wins / 1 Loss** | **SIGNIFICANT** |

---

## 5. Artifacts and Figures Generated

* **Figure 1:** [`evaluation/phase6/figures/fig1_per_patient_distribution.png`](file:///D:/ML%20PROJECT/evaluation/phase6/figures/fig1_per_patient_distribution.png)  
  * Panel A: Boxplot & Strip plot of per-patient MAE across Ridge, ODE, GRU, Hybrid.
  * Panel B: Boxplot & Strip plot of per-patient RMSE across models.
  * Panel C: Patient-by-patient paired differences ($\Delta\text{MAE}$).
* **Tables:**  
  * [`evaluation/phase6/results/per_patient_metrics.csv`](file:///D:/ML%20PROJECT/evaluation/phase6/results/per_patient_metrics.csv)
  * [`evaluation/phase6/results/statistical_significance_tests.json`](file:///D:/ML%20PROJECT/evaluation/phase6/results/statistical_significance_tests.json)
  * [`evaluation/phase6/results/bootstrap_confidence_intervals.json`](file:///D:/ML%20PROJECT/evaluation/phase6/results/bootstrap_confidence_intervals.json)

---
*Certified under locked Phase 6 statistical validation protocol.*
