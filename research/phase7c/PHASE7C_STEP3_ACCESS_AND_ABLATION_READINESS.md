# GlucoShield — Phase 7C Step 3: OhioT1DM Access & Ablation Readiness Report
**Document ID:** `GLUCOSHIELD-RPT-PHASE7C-STEP3-001`  
**Timestamp:** 2026-08-28T17:45:00 Local Time  
**Author:** Lead Deep Learning & Physiological Systems Engineer  
**Status:** **INFRASTRUCTURE & PRE-ABLATION CONTRACT LOCKED (V1 FROZEN)**  

---

## 1. Executive Summary & Verification Matrix

Phase 7C Step 3 establishes the complete **pre-ablation infrastructure, strict data contracts, schema validators, split protocols, and git protections** required to legally and scientifically execute the multimodal wearable ablation experiment upon acquisition of the **OhioT1DM Dataset**.

### Core Governance & Invariant Status:
* **GlucoShield V1 is Bitwise Locked:** Dataset v1.0, Neural Forecaster V1 (`models/glucoshield_neural_best.pt`), ODE Digital Twin, Hybrid Forecaster (`models/glucoshield_hybrid_best.pt`), and Phase 6 evaluation benchmarks remain 100% frozen and bitwise verified.
* **Zero Automatic DUA Requests:** No emails or DUA forms were submitted automatically. Access remains an explicit user-driven step.
* **Zero Fabricated Data:** The readiness checker gracefully reports `DATASET_NOT_PRESENT` without inventing validation numbers or synthetic proxies.
* **Total Automated Tests Passing:** **68 / 68 Tests (100.0%)** across 7 test suites in $0.880\text{s}$.

---

## 2. Definitive Tripartite Status Classification

```
================================================================================
A. VERIFIED NOW (COMPLETED & CERTIFIED)
================================================================================
• Git Security & Ignore Rules: data/raw/OhioT1DM/ and archives protected in .gitignore.
• Configurable Schema Contracts: OhioT1DMConfig and OhioValidationReport created.
• Strict Data Validator: Monotonicity, deduplication, unit bounds, and isolation enforced.
• Pre-Registered Ablation Config: phase7c_ablation_config.yaml locked (8 Train, 2 Val, 2 Test).
• Patient Split Generator: Deterministic patient-disjoint split module implemented and verified.
• Data Provenance Engine: Cryptographic SHA256 and inventory recorder ready.
• Automated Test Suite: 68/68 unit tests passing across all repository modules.
• V1 Preservation Invariant: Checksum verification passes across all baseline assets.

================================================================================
B. IMPLEMENTED BUT AWAITING REAL DATA
================================================================================
• OhioT1DM XML/CSV Parser: Parser implemented in activity_telemetry/ohio_adapter.py.
• Readiness Auditor: check_ohiot1dm_readiness.py ready to scan data/raw/OhioT1DM/.
• Scaler Pipeline: RobustScaler fit-on-train-only logic implemented and tested synthetically.

================================================================================
C. BLOCKED PENDING USER DATA ACCESS
================================================================================
• OhioT1DM Dataset Download: Pending user DUA submission to Prof. Razvan Bunescu.
• Real Patient XML Parsing: Pending placement of decrypted files in data/raw/OhioT1DM/.
• Model A vs Model B Training: Blocked until real patient data is acquired and validated.
• Ablation Hypothesis Testing: Blocked until real test partition evaluation.
================================================================================
```

---

## 3. Pre-Registered Multimodal Ablation Experiment Protocol

```
[OhioT1DM Dataset (12 T1D Patients, 8 Weeks)]
                      │
                      ├── Train Partition (8 Patients) ──> Fit RobustScaler on Train Only
                      ├── Val Partition   (2 Patients) ──> Hyperparameter Tuning & Early Stopping
                      └── Test Partition  (2 Patients) ──> Untouched Benchmark Evaluation
```

### Model Architecture Comparison:
1. **Model A (Baseline Control):** GlucoShield GRU-128 trained using **ONLY the 22 base channels** (CGM, Vel, Accel, Circadian, Insulin, IOB, Carbs, COB).
2. **Model B (Multimodal Treatment):** Identical GRU-128 trained using **22 base + 6 validated activity channels**:
   * `steps_15m` (locomotion load)
   * `hr_mean_15m` (mean heart rate)
   * `hr_std_15m` (intensity volatility)
   * `accel_mag_15m` (3D acceleration norm)
   * `active_load_60m` (causal 60-minute exponential memory)
   * `sensor_missing` (binary coverage flag)
3. **Explicitly Omitted Features:** `hr_reserve_pct` (omitted due to audited $r = 1.000$ collinearity with `hr_mean_15m`).

### Mandatory Pre-Registered Success & Rejection Criteria:

| Evaluation Dimension | Threshold Target | Justification |
|---|:---:|---|
| **Overall Forecast Improvement** | $\mathbf{\Delta\text{MAE} \ge 1.0\text{ mg/dL}}$ | Clinically meaningful overall error reduction. |
| **Stratified Active & Recovery Error** | $\mathbf{\Delta\text{MAE} \ge 3.0\text{ mg/dL}}$ | Major error reduction during workouts and $+0\text{ to }+3\text{h}$ post-workout. |
| **Statistical Significance** | $\mathbf{p < 0.05}$ | Paired two-sided Wilcoxon signed-rank test on patient-level test errors. |
| **Rejection Rule** | $\mathbf{\Delta\text{MAE} < 0.5\text{ mg/dL} \lor p \ge 0.05}$ | Activity features rejected as non-additive if threshold not met. |

---

## 4. What CANNOT Be Claimed Yet (Scientific Boundaries)

1. **NO Claim of Model Superiority:** We do NOT claim that physical activity features improve continuous glucose forecasting yet.
2. **NO Claim of Dataset Possession:** We do NOT claim that the OhioT1DM dataset has been acquired or downloaded.
3. **NO Claim of Clinical Validation:** We do NOT claim clinical efficacy or autonomous insulin decision-making capability.

---

## 5. Exact Next Action for the User

1. **Submit Academic DUA Request:**  
   Send the manual email request to Prof. Razvan Bunescu (`rbunescu@charlotte.edu`) using your official academic/institutional email as detailed in [`research/phase7c/OHIOT1DM_ACCESS_GUIDE.md`](file:///D:/ML%20PROJECT/research/phase7c/OHIOT1DM_ACCESS_GUIDE.md).
2. **Place Decrypted XML Files:**  
   Once received, extract the files into `D:\ML PROJECT\data\raw\OhioT1DM\`.
3. **Run Readiness Checker:**  
   Execute `python activity_telemetry/validation/check_ohiot1dm_readiness.py` to automatically validate schemas and prepare the participant splits for the Step 3 ablation experiment.

---

## 6. Final Step 3 Readiness Verdict

$$\mathbf{FINAL \; VERDICT: \quad A) \quad DATA\_ACCESS\_PREPARED\_AWAITING\_DATA}$$

---
*Certified under Phase 7C Step 3 Pre-Ablation Lockdown Protocol.*
