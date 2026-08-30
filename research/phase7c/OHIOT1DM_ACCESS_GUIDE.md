# GlucoShield — OhioT1DM Dataset Access Guide & Provenance Protocol
**Document ID:** `GLUCOSHIELD-RPT-PHASE7C-OHIO-GUIDE-001`  
**Timestamp:** 2026-08-28T17:40:00 Local Time  
**Author:** Lead Deep Learning & Physiological Systems Engineer  
**Status:** **AWAITING USER DATA ACQUISITION (PRE-ABLATION LOCKDOWN)**  

---

## 1. Dataset Overview & Intended Research Purpose

The **OhioT1DM Dataset** is an internationally benchmarked research dataset developed by Ohio University and KBR for blood glucose level prediction in Type 1 Diabetes.

* **Research Purpose in GlucoShield:** To evaluate whether adding continuous wearable physical activity telemetry (Steps, Heart Rate, Accelerometry) to GlucoShield's core physiological inputs (CGM, Insulin, Meals) improves 5-hour continuous glucose forecasting accuracy without destabilizing clinical safety.
* **Access Status:** **RESTRICTED ACADEMIC RESEARCH ACCESS**. Requires a signed Data Use Agreement (DUA).

---

## 2. Required Physiological Signals for Phase 7C Multimodal Ablation

To participate in the pre-registered Phase 7C ablation experiment, the acquired dataset must contain the following co-recorded channels:

| Signal Category | Specific Required Field | Sampling Resolution | Purpose in GlucoShield V2 |
|---|---|:---:|---|
| **Continuous Glucose** | Interstitial CGM Glucose | **5-minute intervals** | Primary prediction target and autoregressive history |
| **Insulin Telemetry** | Basal infusion rates & Bolus doses | Continuous & discrete events | Pharmacodynamic active insulin (IOB) tracking |
| **Dietary Intake** | Meal announcements & Carb grams ($g$) | Timestamped events | Pharmacodynamic gut absorption (COB) tracking |
| **Heart Rate** | Continuous Heart Rate (bpm) | 1-min or 5-min intervals | Cardiovascular exertion & sympathetic metabolic demand |
| **Physical Locomotion** | Accelerometer magnitude & Steps | 1-min or 5-min intervals | Mechanical exertion driving GLUT-4 glucose clearance |
| **Temporal Context** | ISO 8601 UTC Timestamps | Continuous | Strict causal 15-minute grid alignment |
| **Participant Identity** | Unique Participant ID | Longitudinal ($8\text{ weeks}$) | Patient-disjoint train/validation/test isolation |

---

## 3. Strict Requirement for Co-Recorded Same-Patient Telemetry

> [!IMPORTANT]
> **PROHIBITION OF SYNTHETIC OR CHIMERA PATIENT STITCHING:**  
> GlucoShield strictly prohibits taking physical activity signals from one patient (e.g., Apple Watch steps from Patient A) and aligning them with glucose readings from an unrelated patient (e.g., CGM from Patient B).  
> Glucose dynamics are governed by non-linear individual insulin sensitivity, carbohydrate ratios, and muscular glycogen clearance kinetics. Cross-patient signal stitching destroys physiological causality and constitutes research misconduct.

---

## 4. Manual Data Access Procedure (For the User)

Because the OhioT1DM dataset is distributed under an institutional Data Use Agreement, the **USER must manually submit the access request**. Antigravity and automated agents cannot submit requests on your behalf.

### Step-by-Step Instructions for the User:

1. **Prepare Email Request:**
   * **To:** Prof. Razvan Bunescu (`rbunescu@charlotte.edu`)
   * **Subject:** `OhioT1DM Request`
   * **Sender Address:** Must use an **institutional / academic email address** (e.g. `.edu`, `.ac.uk`, `.org`, or university/hospital affiliate). Personal webmail addresses (Gmail, Yahoo, Hotmail) are automatically rejected.
2. **Include Required Researcher & Institution Information:**
   * Full Name & Official Academic/Research Title
   * Department & Institution Name
   * Official Street Address, City, State/Province, Postal Code, Country
   * Brief Statement of Research Purpose: *"Evaluating physiological glucose forecasting and physical activity telemetry within an academic diabetes digital twin research framework."*
3. **Execute Data Use Agreement (DUA):**
   * Review and countersign the DUA returned by Ohio University.
4. **Receive Encrypted Archive & Password:**
   * Upon approval, you will receive a secure download link and decryption passphrase.

---

## 5. Post-Access User Checklist

Once you receive access to the dataset files, please provide the following details:

- [ ] Exact filename of the downloaded archive (e.g., `OhioT1DM_2018.zip`, `OhioT1DM_2020.zip`).
- [ ] List of participant IDs present in the extracted archive (e.g., `559`, `563`, `570`, `575`, `588`, `591`).
- [ ] File extension and format of individual records (e.g., `.xml` or `.csv`).
- [ ] Confirm whether continuous Heart Rate is present in your acquired cohort.

---

## 6. Expected Local Dataset Placement Convention

Place the decrypted, extracted dataset files into the designated local directory:

```
D:\ML PROJECT\data\raw\OhioT1DM\
├── 2018\
│   ├── train\
│   │   ├── 559-ws-training.xml
│   │   ├── 563-ws-training.xml
│   │   └── ...
│   └── test\
│       ├── 559-ws-testing.xml
│       └── ...
└── 2020\
    ├── train\
    └── test\
```

---

## 7. Git Security & Data Protection Rules

* **Restricted Data Must NEVER Be Committed to Git:**
  The OhioT1DM dataset is governed by strict privacy agreements and must never be pushed to public or private version control repositories.
* **Enforced `.gitignore` Rules:**
  The root [`.gitignore`](file:///D:/ML%20PROJECT/.gitignore) has been updated with the following protective rules:
  ```gitignore
  # Restricted Raw Telemetry Data (OhioT1DM & D1NAMO Raw Archives)
  data/raw/OhioT1DM/
  data/raw/D1NAMO/
  data/raw/*.tgz
  data/raw/*.tar.gz
  data/raw/*.zip
  data/raw/*.xml
  data/raw/*.csv
  !data/raw/.gitkeep
  ```

---

## 8. Data Provenance & Access Manifest Template

When the dataset is placed locally, the automated provenance tool (`activity_telemetry/experiments/data_provenance.py`) will generate a non-sensitive provenance record following this schema:

```json
{
  "dataset_name": "OhioT1DM",
  "access_protocol": "Ohio University DUA",
  "acquisition_date": "YYYY-MM-DD",
  "local_root": "data/raw/OhioT1DM/",
  "participant_count": 12,
  "cohort_breakdown": {
    "2018_cohort": 6,
    "2020_cohort": 6
  },
  "file_inventory": [
    {
      "filename": "559-ws-training.xml",
      "size_bytes": 1048576,
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    }
  ],
  "schema_version": "1.0.0",
  "provenance_status": "PENDING_LOCAL_ACQUISITION"
}
```

---
*Certified under Phase 7C Step 3 Governance Protocol.*
