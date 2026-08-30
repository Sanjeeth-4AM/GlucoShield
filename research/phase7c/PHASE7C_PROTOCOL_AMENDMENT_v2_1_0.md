# GlucoShield — Phase 7C Protocol Amendment v2.1.0 (Locked Protocol)
**Document ID:** `GLUCOSHIELD-RPT-PHASE7C-PROTOCOL-v2-1-0`  
**Timestamp:** 2026-08-28T19:25:00 Local Time  
**Author:** Lead Deep Learning & Physiological Systems Engineer  
**Status:** **OFFICIAL PROTOCOL AMENDMENT v2.1.0 CERTIFIED (V1 FROZEN)**  

---

## 1. Executive Summary & Protocol Versioning

This document establishes **Protocol Version 2.1.0** as the final, certified pre-registered research protocol for the **GlucoShield Multimodal Physical Activity Ablation Benchmark**.

### Strict Governance Compliance:
* **GlucoShield V1 Core is Bitwise Locked:** Neural Forecaster V1 (`models/glucoshield_neural_best.pt`), Hybrid Forecaster (`models/glucoshield_hybrid_best.pt`), Dataset v1.0, ODE Digital Twin, Decision Engine, and Phase 6 evaluation benchmarks remain untouched and permanently frozen.
* **Domain Clarification:** This benchmark evaluates whether wearable physical activity telemetry (PPG Heart Rate, Hardware Steps, 3D Accelerometer) improves forecasting of **endogenous/free-living glucose dynamics**. It is an isolated multimodal ablation experiment, **NOT a direct clinical reproduction or extension** of the original Type 1 Diabetes insulin-aware GlucoShield V1 model.

---

## 2. Locked Participant Cohort Definition ($N = 13$)

* **Eligible Completed Cohort:** Exactly **13 participants** verified in the published Figshare archive:
  `['User1', 'User3', 'User4', 'User5', 'User6', 'User7', 'User8', 'User9', 'User10', 'User12', 'User13', 'User14', 'User15']`.
* **Absent Identifiers:** `User2` and `User11` are absent from the published Figshare repository archive.
* **Recording Duration Profile ($N = 13$):**
  * Minimum Overlap: $6.38\text{ days}$ ($153.2\text{ hours}$, User15)
  * Maximum Overlap: $9.91\text{ days}$ ($237.9\text{ hours}$)
  * Median Overlap: $\mathbf{9.91\text{ days}}$
  * Mean Overlap: $\mathbf{9.54\text{ days}}$
  * Total Usable 15-Minute Windows: $\mathbf{11,903\text{ windows}}$

---

## 3. Pre-Registered 13-Fold Leave-One-Patient-Out Cross-Validation Scheme

```
Cohort (13 Subjects: User1, User3, User4, ..., User15)
  │
  ├── Fold 00: Train (11 pts) | Val (1 pt: User6 ) | Test (1 pt: User8 )
  ├── Fold 01: Train (11 pts) | Val (1 pt: User1 ) | Test (1 pt: User6 )
  ├── Fold 02: Train (11 pts) | Val (1 pt: User5 ) | Test (1 pt: User1 )
  ├── Fold 03: Train (11 pts) | Val (1 pt: User15) | Test (1 pt: User5 )
  ├── Fold 04: Train (11 pts) | Val (1 pt: User12) | Test (1 pt: User15)
  ├── Fold 05: Train (11 pts) | Val (1 pt: User10) | Test (1 pt: User12)
  ├── Fold 06: Train (11 pts) | Val (1 pt: User9 ) | Test (1 pt: User10)
  ├── Fold 07: Train (11 pts) | Val (1 pt: User14) | Test (1 pt: User9 )
  ├── Fold 08: Train (11 pts) | Val (1 pt: User4 ) | Test (1 pt: User14)
  ├── Fold 09: Train (11 pts) | Val (1 pt: User7 ) | Test (1 pt: User4 )
  ├── Fold 10: Train (11 pts) | Val (1 pt: User13) | Test (1 pt: User7 )
  ├── Fold 11: Train (11 pts) | Val (1 pt: User3 ) | Test (1 pt: User13)
  └── Fold 12: Train (11 pts) | Val (1 pt: User8 ) | Test (1 pt: User3 )
```

### Strict Fold Isolation Invariants:
1. **Partition Disjointness:** In each fold, $\text{Train} \cap \text{Val} = \emptyset$, $\text{Train} \cap \text{Test} = \emptyset$, and $\text{Val} \cap \text{Test} = \emptyset$.
2. **Train-Only Scaler Fitting:** `RobustScaler` (median & IQR) is fit strictly on the **11 training participants of that fold**. Parameters are applied frozen to validation and test participants.
3. **Validation Source:** Validation monitoring and early stopping evaluate ONLY on that fold's 1 validation participant.
4. **Complete Test Coverage:** Every participant appears as a held-out test participant **EXACTLY ONCE** across the 13 folds ($13/13$).

---

## 4. Explicit Input Channel Contracts & Missingness Handling

```
================================================================================
PRE-REGISTERED 22 BASELINE CHANNELS (MODEL A CONTROL)
================================================================================
Channels 1–15:  Directly derived from Dexcom G6 5-minute CGM (glucose, velocity,
                acceleration, rolling mean/std/min/max over 1h, 2h, 4h).
Channels 16–17: Circadian diurnal sine and cosine encoding from UTC timestamps.
Channel 18:     bolus_dose = CONSTANT 0.0 (Biological reality: Non-diabetic cohort).
Channel 19:     iob = CONSTANT 0.0 (Biological reality: Zero exogenous IOB).
Channel 20:     meal_carbs = UNOBSERVED / MISSING (Raw data logs discrete activity
                timestamps without gram weights; explicitly tracked as unobserved,
                NOT biological 0.0g meals).
Channel 21:     cob = UNOBSERVED / NOT COMPUTABLE (Carbohydrate absorption curve
                cannot be computed without gram mass).
Channel 22:     day_of_week calendar feature.
================================================================================
PRE-REGISTERED 6 MULTIMODAL ACTIVITY CHANNELS (MODEL B TREATMENT)
================================================================================
Channel 23: steps_15m      --> 15-minute cumulative hardware step detector counts (Sensor 18).
Channel 24: hr_mean_15m    --> 15-minute mean optical PPG heart rate (Sensor 21).
Channel 25: hr_std_15m     --> 15-minute heart rate standard deviation (Sensor 21).
Channel 26: accel_mag_15m  --> 15-minute mean 3D acceleration norm sqrt(x^2+y^2+z^2) (Sensor 1).
Channel 27: active_load_60m--> Causal backward exponential memory (gamma=0.75) on steps_15m.
Channel 28: sensor_missing --> Binary coverage indicator (1 if valid coverage < 30%).
================================================================================
```

---

## 5. Statistical Governance & Wilcoxon Test Specifications

* **Official Statistical Language:**
  > **"13 paired out-of-fold participant-level error observations, where each participant appears exactly once as a held-out test participant across the complete cross-validation procedure."**
* **Statistical Independence Clarification:** Cross-validation itself is **not claimed to create statistically independent samples**. Rather, it pools out-of-fold evaluations such that every participant in the cohort is tested out-of-sample exactly once, yielding 13 paired patient-level observations.
* **Exact Statistical Software & Parameters:**
  * Library: `scipy.stats.wilcoxon` (scipy version `1.18.1`).
  * Parameters: `zero_method='wilcox'`, `alternative='two-sided'`.
  * Significance Level: $\alpha = 0.05$.
  * Minimum Attainable p-value: $p_{\text{min}} = \frac{2}{2^{13}} = \frac{2}{8192} \approx 0.000244$.

---
*Certified under Phase 7C Protocol Amendment v2.1.0.*
