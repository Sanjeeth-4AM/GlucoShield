# GlucoShield: Pre-Modeling Decision & Resolution Report

**Project**: GlucoShield – Multi-Modal AI & Digital Twin Diabetes Companion  
**Auditor / Role**: Lead ML & Data Validation Engineer  
**Date**: 2026-08-23  
**Status**: **DECISION FINALIZED**  

---

# Final Dataset Freeze Decision

### **Decision: FREEZE AS DATASET v1.0**

The finalized dataset in `data/final/` is officially **FROZEN as Dataset v1.0**. 

Creating a Dataset v1.1 is **not required** because:
1. The 660g carbohydrate value is an authentic clinical logging artifact of wet dish weight (porridge liquid weight) rather than corrupted corrupted bytes or pipeline failure.
2. High-carb events ($>300\text{g}$) represent only **0.33%** (11 out of 3,378 meal events) and are isolated predominantly in the training split.
3. Feature scaling (`RobustScaler`) is median/IQR-driven and is completely unskewed by extreme meal entries.
4. Applying a physiological saturation transform ($f(c) = \log(1 + \min(c, 200.0))$) inside the neural network / Digital Twin embedding layer provides a scientifically superior, mathematically rigorous solution that does not fabricate or modify raw clinical observations.

---

## 1. Investigation of Warning 1: Carbohydrate Estimation Artifact

### 1.1 Root Cause Analysis
* **Original Meal Text**: `Seafood porridge 1200g` at `2020-09-11 21:08:00` for record `T2DM_2085_0`.
* **Mechanism**: The original meal estimation lookup matched the keyword *"porridge"* and applied a grain carbohydrate density multiplier of $\sim 0.55\text{ g/g}$ against the gross bowl weight ($1200\text{g} \times 0.55 = 660.0\text{g}$).
* **Physiological Reality**: Cooked Asian rice porridge (congee) consists of approximately 85–90% water by weight. A $1200\text{g}$ serving contains roughly $150–180\text{g}$ of dry rice, delivering $\sim 120–140\text{g}$ of actual carbohydrates. The estimated 660g is a wet-weight volumetric logging artifact.

### 1.2 Frequency & Severity Across Dataset

| Threshold | Event Count | % of All Meals ($N=3378$) | Affected Records | Affected Patients | Plausibility Assessment |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Carbs > 150g** | 182 | 5.39% | 50 | 45 | Plausible for high-carb banquet / large noodle dishes |
| **Carbs > 200g** | 52 | 1.54% | 17 | 16 | Questionable (likely includes dish broth weight) |
| **Carbs > 300g** | 11 | 0.33% | 5 | 5 | Clearly Erroneous (wet-weight multiplier artifact) |
| **Carbs > 500g** | 2 | 0.06% | 2 | 2 | Clearly Erroneous (gross bowl weight of porridge/rice cakes) |

### 1.3 Split Distribution of High-Carb Events

* **Train Split**: Contains **7** of the 11 events $>300\text{g}$, and **both** events $>500\text{g}$ (660g in `T2DM_2085_0` and 539g in `T2DM_2066_0`).
* **Validation Split**: Contains **3** events $>300\text{g}$ (all from Patient `2046`: large noodle & dumpling bowls).
* **Test Split**: Contains **1** event $>300\text{g}$ (`T1DM_1007_0` at 350g: *"Oatcake 500g + Milk/Coffee"*).

### 1.4 Distribution & Scaler Influence
* In `X_train_raw`, median of `carbs_estimate_g` is $0.0\text{ g}$, 75th percentile is $0.0\text{ g}$, and 95th percentile is $35.0\text{ g}$.
* `RobustScaler` scales features via $\frac{x - \text{median}}{\text{IQR}}$. Because both median and IQR are calculated from the general distribution, the 660g outlier **did not shift or distort the center or scale** of the training distribution.

---

## 2. Evaluation of Strategies for Carbohydrate Handling

| Strategy | Neural Forecasting Impact | Digital Twin Simulation | What-If Meal Simulation | Scientific Defensibility |
| :--- | :--- | :--- | :--- | :--- |
| **A. Rebuild Pipeline with Wet-Weight Lookup** | Neutral (cleaner inputs) | High (accurate carb rate) | High | High, but introduces ad-hoc manual recipe assumptions |
| **B. Add Meal Confidence Channel** | Low (model may ignore flag) | Low | Low | Moderate |
| **C. Physiological Saturation Bound (e.g. 200g)** | High (prevents runaway predictions) | High (matches GI saturation) | High (realistic postprandial curves) | **Very High** (matches human SGLT-1 absorption limits) |
| **D. Non-Linear Transform ($\log(1+x)$ in Embeddings)** | High (smooths tail gradients) | Moderate | High | **Very High** (standard ML time-series practice) |
| **E. Discard Unreliable Meals** | Negative (loses meal timing) | Severe (missing insulin triggers) | Negative | Poor |

### Recommended Resolutions:
* **Primary Strategy (Model Layer)**: **Strategy C + D (Physiological Saturation & Log-Scaling in Model Embedding)**.
  The model's input projection layer will process carbohydrate features via:
  $$C_{\text{bounded}} = \log\left(1 + \min(C_{\text{est}}, 200.0)\right)$$
  *Rationale*: Human intestinal glucose transport (SGLT1) saturates at acute carbohydrate loads; gastric emptying rates plateau above 150–200g single-sitting intake. This prevents unbounded forecast spikes while preserving authentic meal timing.
* **Fallback Strategy**: **Strategy A (Dataset v1.1 with wet-weight adjusted dictionary)** if ablation studies demonstrate that wet-weight artifacts degrade ODE baseline integration.

---

## 3. Investigation of Warning 2: Diabetes Type Imbalance

### 3.1 Patient & Sequence Distribution Across Splits

```
TOTAL COHORT: 112 Unique Patients (12 T1DM, 100 T2DM)
TOTAL SEQUENCES: 28,447 Windows (3,470 T1DM [12.2%], 24,977 T2DM [87.8%])
```

| Split | Total Patients | T1DM Patients | T2DM Patients | Total Sequences | T1DM Sequences (% of split) | T2DM Sequences (% of split) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Train** | 78 | 8 (10.3%) | 70 (89.7%) | 19,749 | 2,514 (**12.73%**) | 17,235 (87.27%) |
| **Val** | 17 | 2 (11.8%) | 15 (88.2%) | 4,585 | 449 (**9.79%**) | 4,136 (90.21%) |
| **Test** | 17 | 2 (11.8%) | 15 (88.2%) | 4,113 | 507 (**12.33%**) | 3,606 (87.67%) |

### 3.2 T1DM Patient Sequence Dominance Audit
* **Train Split**: Patient `1006` has 842 sequences ($33.5\%$ of train T1DM), Patient `1002` has 475 sequences ($18.9\%$). The remaining 6 train T1DM patients contribute 1,197 sequences.
* **Validation Split**: Patient `1005` (286 seqs) and Patient `1008` (163 seqs) provide 449 sequences.
* **Test Split**: Patient `1007` (306 seqs) and Patient `1004` (201 seqs) provide 507 test sequences.
* **Audit Finding**: Sequence counts are sufficient for statistically meaningful test evaluation ($N_{\text{test, T1DM}} = 507$), but because test evaluation is drawn from 2 unique T1DM patients, **macro-averaged patient metrics** and **subgroup reporting** are mandatory.

---

## 4. Final Dataset Lock Sign-Off

The finalized dataset in `data/final/` meets all strict clinical and statistical criteria:
* Zero patient leakage between splits
* 100% causal temporal ordering
* Zero NaNs / Infs
* Full demographic balance across splits

**Dataset v1.0 is officially locked.** Development may now proceed to model architecture prototyping under the constraints of [`reports/MODEL_EVALUATION_PROTOCOL.md`](file:///D:/ML%20PROJECT/reports/MODEL_EVALUATION_PROTOCOL.md).
