# GlucoShield — Phase 7C Pre-Registered Multimodal Ablation Protocol (v2.0)
**Document ID:** `GLUCOSHIELD-RPT-PHASE7C-PROTOCOL-v2`  
**Timestamp:** 2026-08-28T18:00:00 Local Time  
**Author:** Lead Deep Learning & Physiological Systems Engineer  
**Status:** **6-FOLD CROSS-VALIDATION PROTOCOL CERTIFIED (V1 FROZEN)**  

---

## 1. Executive Summary & Clinical Domain Clarification

This document formalizes the **Version 2.0 Pre-Registered Protocol** for the GlucoShield Multimodal Physical Activity Ablation Benchmark.

> [!IMPORTANT]
> **CLINICAL DOMAIN & BENCHMARK CLARIFICATION:**  
> This benchmark evaluates whether continuous wearable physical activity telemetry (Steps, Heart Rate, Accelerometer) improves forecasting of **endogenous/free-living glucose dynamics**.  
> It is an isolated multimodal ablation experiment designed to establish the additive value of activity channels.  
> It is **NOT** a direct clinical reproduction or clinical extension of the original Type 1 Diabetes insulin-aware GlucoShield V1 hybrid ODE digital twin.  
> All GlucoShield V1 core models, checkpoints, and Phase 6 evaluation benchmarks remain bitwise locked and permanently preserved.

---

## 2. Mathematical Justification for 6-Fold Cross-Validation

In a static single split of a 12-subject cohort ($8\text{ Train} / 2\text{ Val} / 2\text{ Test}$), the test set contains only $N = 2$ patient-level error pairs. Under the paired two-sided Wilcoxon signed-rank test:
$$\text{Number of signed permutations} = 2^2 = 4 \implies p_{\text{min}} = \frac{2}{2^2} = 0.50$$
It is **mathematically impossible** to achieve the pre-registered significance threshold of $p < 0.05$ with $N = 2$.

### The Corrected 6-Fold Scheme ($N = 12$):
```
Cohort (12 Subjects: User1 to User12)
  │
  ├── Fold 0: Train (8), Val (2), Test [User1, User2]   ──> Out-of-fold Test Error
  ├── Fold 1: Train (8), Val (2), Test [User3, User4]   ──> Out-of-fold Test Error
  ├── Fold 2: Train (8), Val (2), Test [User5, User6]   ──> Out-of-fold Test Error
  ├── Fold 3: Train (8), Val (2), Test [User7, User8]   ──> Out-of-fold Test Error
  ├── Fold 4: Train (8), Val (2), Test [User9, User10]  ──> Out-of-fold Test Error
  └── Fold 5: Train (8), Val (2), Test [User11, User12] ──> Out-of-fold Test Error
                                                                     │
                                                                     ▼
                        [Pool 12 paired out-of-fold participant-level error observations,
                         where each participant appears exactly once as a held-out test participant]
                                                                     │
                                                                     ▼
                                [Paired Two-Sided Wilcoxon Signed-Rank Test: p_min ≈ 0.00049]
```

---

## 3. Strict Pre-Registered Evaluation Invariants

1. **Patient-Disjoint Partitions:** Within each fold, no participant appears in more than one partition ($\text{Train} \cap \text{Val} = \emptyset, \text{Train} \cap \text{Test} = \emptyset, \text{Val} \cap \text{Test} = \emptyset$).
2. **Complete Test Coverage:** Across all 6 folds, every single participant appears as a held-out test participant **EXACTLY ONCE**.
3. **Train-Only Scaler Fitting:** `RobustScaler` parameters (median and IQR) must be fit **strictly on the 8 training participants of that fold**. Parameters are applied unchanged to validation and test participants.
4. **Validation-Only Early Stopping:** Learning rate scheduling and early stopping must monitor only that fold's 2 validation participants.
5. **Exact Out-of-Fold Pairs:** Produce **12 paired out-of-fold participant-level error observations, where each participant appears exactly once as a held-out test participant across the complete cross-validation procedure**.
6. **Patient-Level Statistical Testing:** Statistical testing must be performed on the 12 participant-level paired out-of-fold errors, **NOT on pooled 15-minute sliding windows** (avoiding pseudo-replication). Cross-validation itself is not claimed to create statistically independent samples; rather, it pools out-of-fold evaluations so each participant is tested out-of-sample exactly once.

---

## 4. Pre-Registered Hypotheses & Rejection Thresholds

* **Primary Hypothesis $H_1$:** Multimodal Model B achieves statistically significant error reduction compared to unimodal Model A:
  $$\text{MAE}(\text{Model B}) < \text{MAE}(\text{Model A}) \quad \text{with } p < 0.05 \text{ (Wilcoxon signed-rank, } N=12)$$
* **Practically Meaningful Error Margins:**
  1. $\Delta\text{MAE} \ge 1.0\text{ mg/dL}$ across all out-of-fold test sequences.
  2. $\Delta\text{MAE} \ge 3.0\text{ mg/dL}$ during active exercise and $+0\text{ to }+3\text{h}$ recovery windows.
* **Rejection / Non-Additivity Rule:**
  Reject activity features if:
  $$\Delta\text{MAE} < 0.5\text{ mg/dL} \quad \lor \quad p \ge 0.05$$

---
*Certified under Phase 7C Protocol v2.0.*
