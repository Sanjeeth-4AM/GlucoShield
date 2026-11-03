# GLUCOSHIELD CLINICAL COHORT DE-IDENTIFICATION AUDIT & PROVENANCE RECORD

**Document ID:** `GLUCOSHIELD-AUDIT-DEID-2026-V1`  
**Classification:** Confidential — Clinical Research & Academic Audit Access Only  
**Audit Date:** November 2, 2026  
**Auditor:** Autonomous Deep Learning & Systems Verification Agent  
**Repository Location:** `D:\ML PROJECT\academic_report_evidence\PATIENT_DEIDENTIFICATION_AUDIT.md`  

---

## 1. Compliance & De-Identification Protocol

In accordance with HIPAA Safe Harbor and GDPR pseudonymization principles for clinical research datasets, all patient-level continuous glucose monitoring (CGM) telemetry and demographic profiles displayed in the GlucoShield user interface, API responses, public demonstrations, and visual screenshots have undergone two-tier de-identification:

1. **Suppression of Primary Dataset Identifiers:** Internal database keys, hospital patient numbers, clinical subject identifiers, and row coordinates are completely suppressed in client-facing components.
2. **Clinical Synthetic Aliasing:** Demonstrators and evaluators interact exclusively with standardized clinical aliases:
   - **`Patient A`** — Representing an in-range, well-controlled euglycemic patient profile.
   - **`Patient B`** — Representing a chronically elevated, hyperglycemic patient profile.

---

## 2. Cryptographic Patient Mapping Key

The table below maintains the strictly private cross-reference mapping the public clinical presentation to the underlying immutable research dataset records:

| Presentation Alias | Cohort Role | Internal Dataset ID | Test Window Index | Source Dataset File | Cleaned Master Record Anchor | Window Extraction Slice |
|---|---|:---:|:---:|---|---|:---:|
| **Patient A** | Stable Euglycemic Profile | `2087` | `3574` | `data/final/meta_test.csv` | `clean_output/cleaned_master.csv` | Steps 0 to 95 (Historical), Steps 96 to 115 (Forecast Horizon) |
| **Patient B** | Chronic Hyperglycemic Profile | `2095` | `3826` | `data/final/meta_test.csv` | `clean_output/cleaned_master.csv` | Steps 0 to 95 (Historical), Steps 96 to 115 (Forecast Horizon) |

---

## 3. Patient Baseline Demographics & Clinical Attributes

Both patient records are drawn directly from the verified 112-patient cohort (`clean_output/cleaned_master.csv`) and validated against the Pydantic v2 `PatientStaticProfile` schema:

| Demographic / Clinical Parameter | Patient A (ID: 2087) | Patient B (ID: 2095) | Unit / Scale | Validation Schema Boundary |
|---|:---:|:---:|:---:|:---:|
| **Age** | 67.0 | 66.0 | Years | $18.0 \le \text{age} \le 100.0$ |
| **BMI** | 20.6 | 21.0 | $\text{kg/m}^2$ | $10.0 \le \text{BMI} \le 60.0$ |
| **Diagnosis** | T2DM (`is_t1dm = 0`) | T2DM (`is_t1dm = 0`) | Flag | $0.0$ or $1.0$ |
| **Diabetes Duration** | 0.5 | 7.0 | Years | $\ge 0.0$ |
| **HbA1c** | 59.6 | 73.8 | $\text{mmol/mol}$ | $20.0 \le \text{HbA1c} \le 150.0$ |
| **Glycated Albumin** | 22.6 | 22.6 | $\%$ | $5.0 \le \text{GA} \le 50.0$ |
| **Fasting Glucose** | 90.0 | 180.0 | $\text{mg/dL}$ | $40.0 \le \text{FPG} \le 500.0$ |
| **Fasting C-Peptide** | 0.37 | 0.37 | $\text{ng/mL}$ | $0.01 \le \text{FCP} \le 15.0$ |
| **Macrovascular Complications** | 0.0 | 0.0 | Count | $\ge 0.0$ |
| **Microvascular Complications** | 0.0 | 0.0 | Count | $\ge 0.0$ |

---

## 4. Retrospective 24-Hour CGM Telemetry Statistics

Derived from 96 consecutive 15-minute sensor readings ($24.0\text{ hours}$) extracted from the test cohort:

| Metric | Patient A (Window 3574) | Patient B (Window 3826) | Clinical Interpretation |
|---|:---:|:---:|---|
| **Origin Glucose (Current)** | $100.8\text{ mg/dL}$ | $199.8\text{ mg/dL}$ | Patient A is in tight euglycemia; Patient B starts in Stage 1 hyperglycemia. |
| **24-Hour Mean Glucose** | $103.6\text{ mg/dL}$ | $261.7\text{ mg/dL}$ | Difference of $+158.1\text{ mg/dL}$ between cohorts. |
| **Glucose Standard Deviation** | $13.8\text{ mg/dL}$ | $44.5\text{ mg/dL}$ | Low glycemic variability for Patient A; marked instability for Patient B. |
| **Minimum Glucose (24h)** | $75.6\text{ mg/dL}$ | $198.0\text{ mg/dL}$ | Patient A safely above $70\text{ mg/dL}$; Patient B never drops below $198\text{ mg/dL}$. |
| **Maximum Glucose (24h)** | $131.4\text{ mg/dL}$ | $392.4\text{ mg/dL}$ | Patient A stays within target; Patient B reaches severe hyperglycemic spikes. |
| **Time-in-Range (TIR 70–180 mg/dL)** | **$100.0\%$** | **$0.0\%$** | Perfect clinical target adherence vs. complete target excursion. |
| **Time-Below-Range (TBR < 70 mg/dL)** | **$0.0\%$** | **$0.0\%$** | Zero hypoglycemic exposure in both baseline windows. |
| **Time-Above-Range (TAR > 180 mg/dL)** | **$0.0\%$** | **$100.0\%$** | Complete absence of hyperglycemia vs. 100% chronic hyperglycemic exposure. |

---

## 5. Live Production Serving Inferences (Combination C)

Evaluated via live FastAPI backend serving adapter (`POST /api/v1/forecast`) using certified weights:

| Forecast Parameter | Patient A (ID: 2087) | Patient B (ID: 2095) | Divergence / Significance |
|---|:---:|:---:|---|
| **Trajectory Horizon** | 20 steps (5 hours @ 15m) | 20 steps (5 hours @ 15m) | Identical multi-horizon temporal contract |
| **Initial Forecast (Step 0)** | $108.8\text{ mg/dL}$ | $202.5\text{ mg/dL}$ | Aligned with recent sensor readings |
| **Terminal Forecast (+300m)** | $97.7\text{ mg/dL}$ | $215.1\text{ mg/dL}$ | Patient A trends to steady state; Patient B remains elevated |
| **Predicted Nadir (5h)** | $97.7\text{ mg/dL}$ | $199.2\text{ mg/dL}$ | Both nadirs remain above hypoglycemic threshold ($70\text{ mg/dL}$) |
| **Predicted Peak (5h)** | $108.8\text{ mg/dL}$ | $228.3\text{ mg/dL}$ | Patient B experiences postprandial crest at $+165\text{ min}$ |
| **Hypo Risk (1 Hour)** | $0.8\%$ ($0.0078$) | $0.0\%$ ($0.0000$) | Negligible acute hypoglycemia risk |
| **Hypo Risk (2 Hours)** | $2.6\%$ ($0.0260$) | $0.05\%$ ($0.0005$) | Minor downside drift in Patient A |
| **Hypo Risk (4 Hours)** | $9.4\%$ ($0.0944$) | $0.2\%$ ($0.0020$) | Downside uncertainty tail expands naturally |
| **Hyper Risk (2 Hours)** | $2.8\%$ ($0.0280$) | **$97.3\%$** ($0.9734$) | Patient B has near-certain acute hyperglycemia |
| **Hyper Risk (4 Hours)** | $4.0\%$ ($0.0402$) | **$98.7\%$** ($0.9871$) | Sustained hyperglycemia for Patient B |
| **Discrete Risk at 5 Hours** | **N/A (Not Evaluated)** | **N/A (Not Evaluated)** | Model architecture does not evaluate 5h discrete probability |

---

## 6. Verification and Boundary Invariants

1. **Non-Invention Guarantee:** No glucose telemetry point, covariate value, or model probability in this document was fabricated. All values were directly produced by the real data pipeline and certified model execution.
2. **Frontend Isolation:** Client applications only request `/api/v1/cohort/demo-patients` or `/api/v1/cohort/comparison`. At no point does the browser leak internal database IDs `2087` or `2095` to client displays or UI elements.
3. **Reproducibility Anchor:** Re-running `python scratch/select_and_evaluate_patients.py` will deterministically reproduce the identical window extractions, static profiles, and Combination C inference outputs.
