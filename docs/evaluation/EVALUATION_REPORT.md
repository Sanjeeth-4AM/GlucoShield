# GlucoShield Experimental Evaluation & Benchmark Report

**Target Module:** Evaluation & Comparative Benchmarks  
**Dataset:** Shanghai Continuous Glucose Monitoring Cohort  
**Evaluation Set:** Frozen Test Partition ($N=4,113$ Sequences, 17 Patients, Zero Patient Overlap)  
**Verification Date:** November 3, 2026  

---

## 1. Overall Model Benchmark Scorecard

Continuous trajectory accuracy (5-hour / 20-step horizon) and acute event classification on the untouched test partition:

| Model Architecture | Test MAE (mg/dL) | Test RMSE (mg/dL) | Clarke Zone A (%) | Clarke Zone B (%) | Clarke A+B (%) | 4h Hypo AUPRC |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Persistence Baseline** | 36.42 | 49.01 | 58.40% | 27.72% | 86.12% | 0.512 |
| **Linear Extrapolation** | 62.15 | 81.39 | 43.20% | 28.20% | 71.40% | 0.435 |
| **Ridge Regression** | 25.37 | 35.80 | 66.80% | 27.30% | 94.10% | 0.741 |
| **Standalone Hovorka ODE**| 39.80 | 52.67 | 56.10% | 28.40% | 84.50% | 0.589 |
| **Neural V1 (GRU-128)** | **24.45** | **34.90** | **68.20%** | **27.08%** | **95.28%** | **0.828 ± 0.004** |
| **Gated Hybrid** | 24.14 | 34.77 | 68.58% | 26.77% | 95.36% | 0.819 |
| **Combination C (Serving)**| **24.45 (point)**| **34.90 (point)**| **68.20%** | **27.08%** | **95.28%** | **0.828 (96.39% CI)** |

---

## 2. Multi-Horizon Error Progression

Error progression across the 5-hour multi-horizon window demonstrates stable continuous forecasting:

| Horizon Milestone | Step | Target Time Ahead | MAE (mg/dL) | RMSE (mg/dL) | Clarke Zone A+B (%) |
|:---|:---:|:---:|:---:|:---:|:---:|
| **15 Minutes** | Step 1 | +15 min | 6.42 | 8.93 | 99.82% |
| **30 Minutes** | Step 2 | +30 min | 11.20 | 15.64 | 99.14% |
| **1 Hour** | Step 4 | +60 min | 17.85 | 24.80 | 97.80% |
| **2 Hours** | Step 8 | +120 min | 24.15 | 34.12 | 95.62% |
| **3 Hours** | Step 12 | +180 min | 28.40 | 39.85 | 93.40% |
| **4 Hours** | Step 16 | +240 min | 30.65 | 42.10 | 91.85% |
| **5 Hours** | Step 20 | +300 min | 31.20 | 41.89 | 90.72% |

---

## 3. Multi-Seed Training Stability Scorecard

To confirm training reproducibility, the architecture was trained and validated across three independent seeds (42, 123, 7) using identical hyperparameter configurations:

| Metric | Seed 42 | Seed 123 | Seed 7 | Multi-Seed Mean ± Std |
|:---|:---:|:---:|:---:|:---:|
| **Val RMSE (mg/dL)** | 31.14 | 31.40 | 31.72 | **$31.42 \pm 0.29$** |
| **Val MAE (mg/dL)** | 21.62 | 21.88 | 22.12 | **$21.87 \pm 0.25$** |
| **Hypo 4h AUPRC** | 0.832 | 0.828 | 0.824 | **$0.828 \pm 0.004$** |
| **Clarke Zone A+B** | 95.42% | 95.31% | 95.20% | **$95.31\% \pm 0.11\%$** |

---

## 4. External Validation & Uncertainty Calibration

When tested on unseen external validation cohorts (Category D external validation with zero retraining):
- **Frozen V1 GRU-128 Point RMSE:** $44.15\text{ mg/dL}$
- **Legacy V1 MC-Dropout 95% Coverage:** $72.10\%$ (Suffers severe uncertainty collapse under distribution shift)
- **Phase 13 Calibrated Quantile 95% Coverage:** **$96.39\%$** (Fully calibrated, satisfies statistical nominal coverage)

---

## 5. Visual Evaluation Artifacts

- **Clarke Error Grid Analysis:** [`clarke_error_grid_distribution.png`](file:///D:/ML%20PROJECT/docs/evaluation/clarke_error_grid_distribution.png)
- **Model Benchmark Comparison:** [`model_benchmark_comparison.png`](file:///D:/ML%20PROJECT/docs/evaluation/model_benchmark_comparison.png)
- **Training Loss Curves:** [`training_loss_curves.png`](file:///D:/ML%20PROJECT/docs/evaluation/training_loss_curves.png)
- **Multi-Horizon RMSE Progression:** [`multi_horizon_rmse_progression.png`](file:///D:/ML%20PROJECT/docs/evaluation/multi_horizon_rmse_progression.png)
