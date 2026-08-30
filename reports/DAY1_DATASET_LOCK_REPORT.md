# GlucoShield: Day 1 Dataset Independent Audit & Lock Report

**Project**: GlucoShield – Multi-Modal AI & Digital Twin Diabetes Companion  
**Auditor**: Lead ML & Data Validation Engineer  
**Audit Date**: 2026-08-23  
**Dataset Version**: `1.0.0-locked`  
**Audit Status**: **CONDITIONAL PASS**  

---

## 1. Executive Summary

An exhaustive, independent validation and data integrity audit has been performed on the finalized GlucoShield dataset. The dataset consists of continuous glucose monitoring (CGM) time-series from 112 unique clinical patients (12 T1DM, 100 T2DM) resampled to 15-minute intervals, accompanied by patient-level static clinical biomarkers.

### Audit Verdict: **CONDITIONAL PASS**
* **Leakage Integrity**: **PASS** (Zero patient overlap between Train, Validation, and Test splits; zero temporal leakage).
* **Tensor Health**: **PASS** (Zero NaNs, zero Infs across all 28,447 sequences and 33 tensor files).
* **Causality & Alignment**: **PASS** (Input sequences and engineered rolling features are strictly backward-looking; targets are 100% aligned with future horizons).
* **Clinical Nuance / Caution**: **CONDITIONAL** (Keyword-based dietary carb estimation exhibits overestimation artifacts on large-volume liquid/porridge dishes, e.g., 660g for 1200g seafood porridge, which requires specific handling or feature weighting prior to deep learning model training).

---

## 2. Exact Dataset Inventory & Checksums

All finalized tensors and metadata files in `data/final/` and `data/metadata/` have been audited and fingerprinted via SHA256 hashes.

| File Path | Size (Bytes) | Size (MB) | SHA256 Checksum (First 16 chars) | Status |
| :--- | :--- | :--- | :--- | :--- |
| `data/final/X_train_scaled.npy` | 166,839,680 | 159.111 | `15e85c2c54bebeae...` | **LOCKED** |
| `data/final/X_train_raw.npy` | 166,839,680 | 159.111 | `73da91f3bc99d98f...` | **LOCKED** |
| `data/final/static_train_scaled.npy` | 711,092 | 0.678 | `b786f1e8fe37617b...` | **LOCKED** |
| `data/final/static_train_raw.npy` | 711,092 | 0.678 | `51bc38a9d1d94be3...` | **LOCKED** |
| `data/final/Y_train_trajectory.npy` | 1,580,048 | 1.507 | `4c8d23d8c1c4f5ea...` | **LOCKED** |
| `data/final/Y_train_hypo_1h.npy` | 79,124 | 0.075 | `be29188d4ec09140...` | **LOCKED** |
| `data/final/Y_train_hypo_2h.npy` | 79,124 | 0.075 | `2f411b4ba176c9ad...` | **LOCKED** |
| `data/final/Y_train_hypo_4h.npy` | 79,124 | 0.075 | `2a884ec8916d1f95...` | **LOCKED** |
| `data/final/Y_train_hyper_2h.npy` | 79,124 | 0.075 | `60281b376dff064f...` | **LOCKED** |
| `data/final/Y_train_hyper_4h.npy` | 79,124 | 0.075 | `0418c3971e464c12...` | **LOCKED** |
| `data/final/meta_train.csv` | 2,496,729 | 2.381 | `ea09723049195b05...` | **LOCKED** |
| `data/final/X_val_scaled.npy` | 38,734,208 | 36.940 | `e5bc41b12b55f187...` | **LOCKED** |
| `data/final/X_val_raw.npy` | 38,734,208 | 36.940 | `1846b0b2e88a531f...` | **LOCKED** |
| `data/final/static_val_scaled.npy` | 165,188 | 0.158 | `d6dfbfa201b173fa...` | **LOCKED** |
| `data/final/static_val_raw.npy` | 165,188 | 0.158 | `295a0fa5aa97573e...` | **LOCKED** |
| `data/final/Y_val_trajectory.npy` | 366,928 | 0.350 | `7376a9a8cf6db8b1...` | **LOCKED** |
| `data/final/Y_val_hypo_4h.npy` | 18,468 | 0.018 | `3a557b49cfcb7024...` | **LOCKED** |
| `data/final/Y_val_hyper_4h.npy` | 18,468 | 0.018 | `66872957ee055dfc...` | **LOCKED** |
| `data/final/meta_val.csv` | 578,781 | 0.552 | `3329d4aa3351ec30...` | **LOCKED** |
| `data/final/X_test_scaled.npy` | 34,746,752 | 33.137 | `38276f7a6f23ae94...` | **LOCKED** |
| `data/final/X_test_raw.npy` | 34,746,752 | 33.137 | `30a6aa260a9f5d16...` | **LOCKED** |
| `data/final/static_test_scaled.npy` | 148,196 | 0.141 | `ae2ea5cfa169cb45...` | **LOCKED** |
| `data/final/static_test_raw.npy` | 148,196 | 0.141 | `3a39e8025e1df11b...` | **LOCKED** |
| `data/final/Y_test_trajectory.npy` | 329,168 | 0.314 | `a90c42738a535e29...` | **LOCKED** |
| `data/final/Y_test_hypo_4h.npy` | 16,580 | 0.016 | `5a7442111d4aa697...` | **LOCKED** |
| `data/final/Y_test_hyper_4h.npy` | 16,580 | 0.016 | `473ea8909405d460...` | **LOCKED** |
| `data/final/meta_test.csv` | 520,552 | 0.496 | `3bf846872aa0df78...` | **LOCKED** |
| `data/metadata/feature_scaler.joblib` | 807 | < 0.001 | `4458f278eb079c66...` | **LOCKED** |
| `data/metadata/static_scaler.joblib` | 783 | < 0.001 | `b783515433d7b93b...` | **LOCKED** |
| `data/metadata/dataset_manifest.json` | 3,839 | 0.004 | `0e9b9bc88a536ff9...` | **LOCKED** |

---

## 3. Independent Validation Results

### A. Tensor Shapes & Counts
* **Train Split**: $N = 19,749$ samples
  * Input tensor `X_train_scaled`: `(19749, 96, 22)`
  * Static tensor `static_train_scaled`: `(19749, 9)`
  * Target trajectory `Y_train_trajectory`: `(19749, 20)`
* **Validation Split**: $N = 4,585$ samples
  * Input tensor `X_val_scaled`: `(4585, 96, 22)`
  * Static tensor `static_val_scaled`: `(4585, 9)`
  * Target trajectory `Y_val_trajectory`: `(4585, 20)`
* **Test Split**: $N = 4,113$ samples
  * Input tensor `X_test_scaled`: `(4113, 96, 22)`
  * Static tensor `static_test_scaled`: `(4113, 9)`
  * Target trajectory `Y_test_trajectory`: `(4113, 20)`
* **Combined Total**: **28,447 sequences** ($2,730,912$ observation timesteps).

### B. Missing Values & Infs
* Total NaNs in all feature tensors: **0**
* Total Infs in all feature tensors: **0**
* Total NaNs in all target tensors: **0**

---

## 4. Leakage & Boundary Audit

1. **Patient-Wise Disjointness**:
   $$\text{Patients}_{\text{train}} \cap \text{Patients}_{\text{val}} = \emptyset$$
   $$\text{Patients}_{\text{train}} \cap \text{Patients}_{\text{test}} = \emptyset$$
   $$\text{Patients}_{\text{val}} \cap \text{Patients}_{\text{test}} = \emptyset$$
   * Train: 78 unique patients (8 T1DM, 70 T2DM)
   * Validation: 17 unique patients (2 T1DM, 15 T2DM)
   * Test: 17 unique patients (2 T1DM, 15 T2DM)
   * **Result**: **PASS** (Zero patient overlap).

2. **Sequence Boundary Preservation**:
   * Every sequence window ($96\text{ steps input} + 20\text{ steps target} = 116\text{ consecutive steps}$) was generated strictly within a single continuous `record_id`.
   * Cross-patient or cross-visit transitions: **0**.

3. **Temporal Causality**:
   * For all 28,447 sequences: $t_{\text{start}} < t_{\text{input\_end}} < t_{\text{target\_start}} \le t_{\text{target\_end}}$.
   * Monotonicity check across all splits: **100.0% PASS**.

4. **Scaler Leakage Audit**:
   * `RobustScaler` and `StandardScaler` were fitted **exclusively on the training data** ($X_{\text{train}}$ flat shape `(1895904, 22)` and `static_train` shape `(19749, 9)`).
   * Validation and Test sets were transformed using the frozen training parameters.
   * Static clinical medians used for missing biomarker imputation were computed strictly from the training cohort ($N=78$).

---

## 5. Target Alignment & Event Prevalence Audit

The forecast target is a continuous trajectory vector of the subsequent 20 steps (5.0 hours). Ground-truth event classifications were audited against trajectory extrema:

| Horizon & Clinical Event | Definition | Train Rate | Val Rate | Test Rate |
| :--- | :--- | :--- | :--- | :--- |
| **Hypoglycemia (1 Hour)** | $\min(G_{t+1 \dots t+4}) < 70\text{ mg/dL}$ | 2.57% | 3.51% | 3.65% |
| **Hypoglycemia (2 Hours)** | $\min(G_{t+1 \dots t+8}) < 70\text{ mg/dL}$ | 4.31% | 6.09% | 6.30% |
| **Hypoglycemia (4 Hours)** | $\min(G_{t+1 \dots t+16}) < 70\text{ mg/dL}$ | **7.15%** | **10.43%** | **10.31%** |
| **Hyperglycemia (2 Hours)** | $\max(G_{t+1 \dots t+8}) > 180\text{ mg/dL}$ | 30.64% | 27.68% | 31.85% |
| **Hyperglycemia (4 Hours)** | $\max(G_{t+1 \dots t+16}) > 180\text{ mg/dL}$ | **41.37%** | **36.97%** | **42.74%** |

*Verification*: Max absolute difference between metadata `current_glucose`, `min_future_glucose`, `max_future_glucose` and underlying tensor extractions is $< 10^{-6}\text{ mg/dL}$.

---

## 6. Distribution & Demographic Analysis Across Splits

| Metric / Biomarker | Training Set ($N=78$) | Validation Set ($N=17$) | Test Set ($N=17$) | Clinical Equivalence |
| :--- | :--- | :--- | :--- | :--- |
| **Glucose (Input Mean $\pm$ Std)** | $144.1 \pm 52.8\text{ mg/dL}$ | $136.9 \pm 46.1\text{ mg/dL}$ | $145.4 \pm 55.4\text{ mg/dL}$ | Balanced |
| **Glucose (Target Mean $\pm$ Std)** | $143.9 \pm 52.5\text{ mg/dL}$ | $136.8 \pm 45.8\text{ mg/dL}$ | $145.2 \pm 55.2\text{ mg/dL}$ | Balanced |
| **Age (Years)** | $58.1 \pm 12.4$ | $59.2 \pm 10.9$ | $60.3 \pm 12.1$ | Homogeneous |
| **BMI ($\text{kg/m}^2$)** | $24.7 \pm 3.5$ | $24.8 \pm 2.8$ | $24.4 \pm 3.3$ | Homogeneous |
| **HbA1c ($\text{mmol/mol}$)** | $74.8 \pm 20.6$ | $69.6 \pm 16.6$ | $74.2 \pm 18.6$ | Homogeneous |
| **Fasting Glucose ($\text{mg/dL}$)** | $145.3 \pm 50.1$ | $134.9 \pm 39.4$ | $144.2 \pm 48.7$ | Homogeneous |
| **Fasting C-Peptide ($\text{nmol/L}$)** | $0.57 \pm 0.44$ | $0.68 \pm 0.48$ | $0.62 \pm 0.45$ | Homogeneous |

---

## 7. Outlier & Suspicious Value Analysis

### 1. High Carbohydrate Meal Logs (Up to 660g)
* **Investigation**: 52 timesteps out of 127,997 recorded estimated carbs $> 200\text{ g}$.
* **Max Single Event**: `Record T2DM_2085_0`, timestamp `2020-09-11 21:08:00`, `carbs_estimate_g = 660.0g`. Raw log: *"Seafood porridge 1200g"*.
* **Root Cause**: The clinical data logging recorded total meal dish weight (wet soup/water weight). A generic keyword multiplier ($1200\text{g} \times 0.55$) was applied. Since porridge is ~85% water, the actual consumable carbohydrate was closer to ~140g.
* **Impact**: Because `RobustScaler` (median & IQR) is utilized, this single high value does not distort population feature scaling, but models must be resilient to large carb inputs.

### 2. High Insulin Doses (10–15 IU)
* **Investigation**: 40 timesteps recorded single-timestep bolus insulin $\ge 10\text{ IU}$ (maximum: 15.0 IU).
* **Clinical Assessment**: Physiologically valid for severe insulin-resistant T2DM or postprandial correction boluses in adult patients.

### 3. Patient Sequence Imbalance
* Minimum sequences per patient: Patient `2035` (33 sequences, ~3.5 days of recording).
* Maximum sequences per patient: Patient `2069` (846 sequences, 3 visits across 4 weeks).
* **Clinical Assessment**: Standard for clinical observational cohorts. Patient-wise splitting ensures entire patient trajectories remain isolated in single splits.

---

## 8. Dataset Limitations & Digital Twin Modeling Risks

1. **Dietary Macro Granularity**: Carbohydrates in this cohort are derived from free-text meal logs, not weighed laboratory metabolic chamber logs.
2. **Missing Wearable Channels in Current Cohort**: Step count, heart rate variability, and sleep stages are not present in the Shanghai dataset.
3. **Cohort Size for T1DM**: 12 T1DM patients vs. 100 T2DM patients reflects real-world clinical prevalence, but requires stratified evaluation to ensure T1DM error metrics are tracked independently.

---

## 9. REQUIRED ACTIONS BEFORE MODEL TRAINING

> [!IMPORTANT]
> The following 4 engineering guidelines must be observed when developing the model architectures:

1. **Loss Function Design**:
   * Continuous forecast training must use a composite loss:
     $$\mathcal{L} = \text{MSE}(\hat{y}, y) + \lambda_{\text{hypo}} \cdot \text{AsymmetricPenalty}(\hat{y}, y)$$
     to penalize under-predicting dangerous crashes (false negatives in hypoglycemia are clinically life-threatening).

2. **Carb Feature Regularization**:
   * Utilize non-linear activation (or logarithmic / clipping transformations in the embedding layer) for `carbs_estimate_g` and `cob` so that occasional porridge-logging artifacts ($>300\text{g}$) do not cause runaway positive predictions.

3. **Subgroup Metric Stratification**:
   * All evaluation benchmarks must report RMSE, MAE, Hypoglycemia Sensitivity, and Clarke Error Grid Zone A+B separately for **T1DM** and **T2DM** sub-cohorts.

4. **Multi-Task Heads**:
   * Future neural models should predict both the continuous trajectory $\hat{Y} \in \mathbb{R}^{20}$ and the multi-horizon binary risk probabilities ($P(\text{Hypo}_{4\text{h}})$, $P(\text{Hyper}_{4\text{h}})$) using shared representations.

---

## 10. Audit Decision Summary

| Audit Dimension | Result | Notes |
| :--- | :--- | :--- |
| Tensor Integrity | **PASS** | 28,447 sequences verified. Zero NaNs, zero Infs. |
| Leakage Audit | **PASS** | Strict patient-wise disjointness. Scalers fit on train only. |
| Temporal Causality | **PASS** | 100% past-only feature construction. Future strictly preserved in target. |
| Data Lock Fingerprints | **PASS** | SHA256 checksums generated and recorded in lock manifest. |
| **OVERALL DECISION** | **CONDITIONAL PASS** | **Dataset is locked and certified for model architecture development.** |
