# GlucoShield — Phase 7C Wearable Physical Activity Telemetry & Dataset Audit
**Document ID:** `GLUCOSHIELD-RPT-PHASE7C-AUDIT-001`  
**Timestamp:** 2026-08-28T17:15:00 Local Time  
**Author:** Lead Deep Learning & Physiological Systems Engineer  
**Status:** **RESEARCH & FEASIBILITY AUDIT COMPLETE (V1 FROZEN)**  

---

## 1. Executive Summary & Audit Objectives

Phase 7C Step 1 performs a comprehensive research audit to determine whether there is a scientifically valid, accessible dataset containing **synchronized continuous glucose monitoring (CGM)** and **wearable physical activity telemetry (Steps, Heart Rate, Accelerometer)** recorded from the **SAME human participants** over contiguous longitudinal periods.

### Core Scientific Invariants:
* **GlucoShield V1 is Bitwise Locked:** Dataset v1.0, GRU Neural Forecaster V1, 6-compartment ODE Digital Twin, Hybrid Forecaster, and Phase 6 evaluation benchmarks remain untouched and frozen.
* **Zero Synthetic/Chimera Patient Data:** Under no circumstances will activity signals from one dataset be stitched to glucose telemetry from another unrelated patient.
* **Planning Only:** Zero models are retrained, zero data is downloaded, and no model integration is executed in this step.

---

## 2. In-Depth Audit of Candidate Datasets

### A. OhioT1DM Dataset (Ohio University / KBR)
* **Primary Publication:** Marling & Bunescu, *"The OhioT1DM Dataset for Blood Glucose Level Prediction"*, CEUR Workshop Proceedings (2018 & 2020 editions).
* **Cohort Profile:** **12 individuals with Type 1 Diabetes** (Cohort 1: 6 patients in 2018; Cohort 2: 6 patients in 2020).
* **Recording Duration:** **8 continuous weeks per participant** ($\approx 56\text{ days/patient}$, totaling over $650\text{ days}$ of dense longitudinal telemetry).
* **CGM Telemetry:** 5-minute sampling interval (Medtronic Enlite / Dexcom G6).
* **Wearable Hardware & Signals:**
  * **2018 Cohort (Basis Peak Wristband):** Continuous 5-minute aggregations of **Heart Rate (bpm)**, **Step Count / Accelerometer**, **Skin Temperature ($^\circ\text{C}$)**, and **Galvanic Skin Response (GSR / $\mu\text{S}$)**.
  * **2020 Cohort (Empatica Embrace Wristband):** Continuous 1-minute aggregations of **Acceleration Magnitude**, **Skin Temperature**, and **GSR** *(Heart rate was omitted in the 2020 Empatica release)*.
* **Contextual Events:** Continuous basal insulin infusion rates, discrete bolus insulin injections, meal announcements with carbohydrate grams, self-reported exercise bouts, sleep logs, work times, and perceived stress annotations.
* **Temporal Synchronization:** All signals are co-recorded on identical patients with synchronized UTC ISO 8601 timestamps formatted in structured XML.
* **Access & Licensing:** **Restricted Academic Research Access**. Requires submitting a free Data Use Agreement (DUA) request with an institutional email to Prof. Razvan Bunescu (`rbunescu@charlotte.edu`).
* **Download Footprint:** $\approx 50 - 100\text{ MB}$ (compressed XML text files).
* **Evaluation Suitability:** Fully supports patient-disjoint train/validation/test evaluation (e.g. 8 Train / 2 Val / 2 Test patients, or 12-fold Leave-One-Patient-Out Cross-Validation).
* **Verdict:** **GOLD STANDARD BENCHMARK FOR WEARABLE ACTIVITY INTEGRATION (RESTRICTED ACCESS)**.

---

### B. D1NAMO Dataset (Hes-so Valais-Wallis, Switzerland)
* **Primary Publication:** Fraz et al., *"D1NAMO: A Multi-Modal Dataset for Non-Invasive Type 1 Diabetes Management"*, Informatics in Medicine Unlocked (2018).
* **Cohort Profile:** **29 participants** (9 patients with Type 1 Diabetes + 20 healthy control subjects).
* **Recording Duration:** $\approx 4 - 5\text{ days per diabetic patient}$ (substantially shorter duration than OhioT1DM).
* **CGM Telemetry:** 5-minute sampling interval via Medtronic iPro2 (blinded retrospective CGM for diabetic subjects; fingerstick meter for healthy controls).
* **Wearable Hardware & Signals:** **Zephyr BioHarness 3 Chest Strap** providing:
  * Continuous 1-lead ECG & Heart Rate (1 Hz)
  * Respiration / Breathing rate (1 Hz)
  * 3-axis Accelerometer (50 Hz raw, 1 Hz summary)
  * Food photographs with manual carbohydrate annotations.
* **Temporal Synchronization:** Co-recorded on identical subjects with synchronized timestamps in CSV format.
* **Access & Licensing:** **100% OPEN ACCESS** on Zenodo (`https://zenodo.org/records/1421616`) under Creative Commons Attribution 4.0 (CC BY 4.0).
* **Download Footprint:** $\approx 15\text{ GB}$ (contains full high-frequency raw ECG and sensor arrays).
* **Limitations:**
  * Only 9 diabetic patients with short 4-5 day recording windows.
  * Chest strap sensor compliance drops significantly during sleep compared to wristbands.
  * Small total sequence volume for deep neural network training.
* **Verdict:** **VERIFIED OPEN ACCESS BENCHMARK (EXCELLENT FOR EXPLORATORY MULTIMODAL BENCHMARKING)**.

---

### C. OpenAPS / Nightscout Data Commons
* **Cohort Profile:** $>150\text{ T1D individuals}$ using automated insulin delivery (AID) algorithms.
* **Signals:** Continuous 5-minute CGM (Dexcom G6), automated micro-boluses, basal delivery, meal announcements.
* **Wearable Signals:** Intermittent and non-standardized (many users do not log Apple Watch or Fitbit steps to Nightscout).
* **Verdict:** **EXCELLENT FOR ADVANCED AID/IOB CONTROL, BUT LACKS UNIFORM WEARABLE ACTIVITY DATA**.

---

### D. ShanghaiT1D / ShanghaiT2D (Current GlucoShield V1 Base)
* **Cohort Profile:** 112 patients (12 T1D, 100 T2D), 15-minute CGM, insulin, meals, 38 lab biomarkers.
* **Wearable Signals:** **ZERO wearable accelerometer, step, or heart rate signals** were collected in the Shanghai clinical protocol.

---
*Certified for Phase 7C dataset auditing.*
