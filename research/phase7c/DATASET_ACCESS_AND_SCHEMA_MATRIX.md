# GlucoShield — Phase 7C Dataset Access & Schema Feasibility Matrix
**Document ID:** `GLUCOSHIELD-RPT-PHASE7C-MATRIX-001`  
**Timestamp:** 2026-08-28T17:16:00 Local Time  
**Author:** Lead Deep Learning & Physiological Systems Engineer  
**Status:** **FEASIBILITY MATRIX CERTIFIED**  

---

## 1. Strict Feasibility Comparison Matrix

| Dataset | Access | Patients | CGM | Heart Rate | Accelerometer | Steps | Synchronized Same-Patient Telemetry | Timestamp Quality | Download Size | Scientific Suitability | Verdict |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **OhioT1DM (2018 + 2020)** | **Restricted Research DUA** (Free, email to PI) | **$12\text{ T1D}$** ($8\text{ weeks/pt}$, $>650\text{ days}$) | **YES (5 min)** (Medtronic / Dexcom) | **YES (2018)** / No (2020) | **YES (3D Accel)** | **YES (5-min Steps)** | **YES (100% Same Patients)** | **High (UTC ISO 8601 XML)** | **$\approx 50 - 100\text{ MB}$** | **Highest (Dense 8-week longitudinal wear)** | **PRIMARY TARGET (REQUEST DUA)** |
| **D1NAMO** | **Open Access** (Zenodo, CC BY 4.0) | **$9\text{ T1D} + 20\text{ Controls}$** ($4-5\text{ days/pt}$) | **YES (5 min)** (Medtronic iPro2) | **YES (1 Hz ECG)** | **YES (3D Accel)** | **Derivable from Accel** | **YES (100% Same Patients)** | **High (Synchronized CSV)** | **$\approx 15\text{ GB}$** | **Moderate-High (Shorter 4-5d wear)** | **SECONDARY OPEN BENCHMARK** |
| **ShanghaiT1D / T2D (V1 Core)** | **Open Access** (PhysioNet / Nature) | **$112\text{ Pts}$** (12 T1D, 100 T2D) | **YES (15 min)** | **NO** | **NO** | **NO** | **N/A (No wearables collected)** | **High (15m CSV)** | **$\approx 10\text{ MB}$** | **Unsuitable for Wearables (Base V1 only)** | **V1 BASELINE ONLY (NO WEARABLES)** |
| **OpenAPS / Nightscout** | **Open / Registration** (OpenHumans.org) | **$>150\text{ T1D}$** | **YES (5 min)** | **No (Sparse)** | **No (Sparse)** | **Sparse / Non-uniform** | **Partial (Many users lack watch sync)** | **Variable** | **$\approx 2 - 5\text{ GB}$** | **Low (Inconsistent activity logs)** | **REJECTED FOR ACTIVITY BENCHMARK** |
| **Tidepool Data Platform** | **Restricted** (IRB / Research DUA) | **$>500\text{ T1D}$** | **YES (5 min)** | **Sparse** | **Sparse** | **Sparse** | **Partial (Watch upload compliance $<20\%$)** | **Variable** | **$\approx 10\text{ GB}$** | **Low for continuous physical activity** | **REJECTED AS PRIMARY** |
| **MIMIC-IV / eICU** | **Restricted PhysioNet** (CITI Training) | **$>40,000\text{ ICU}$** | **NO (Fingerstick / IV)** | **YES (Bedside ECG)** | **NO** | **NO (Bedridden)** | **NO (ICU critical care, not free-living)** | **High** | **$>50\text{ GB}$** | **Scientifically Invalid (Bedridden)** | **REJECTED (INVALID DOMAIN)** |

---

## 2. Technical Schema Comparison: OhioT1DM vs. D1NAMO

### A. OhioT1DM XML Telemetry Schema:
```xml
<patient id="559" weight="84" bolus_type="novolog">
  <glucose_level ts="2021-10-14 12:00:00" value="142"/>
  <basal ts="2021-10-14 12:00:00" value="0.95"/>
  <bolus ts="2021-10-14 12:15:00" dose="3.5"/>
  <meal ts="2021-10-14 12:15:00" type="Lunch" carbs="45"/>
  <exercise ts="2021-10-14 14:30:00" duration="45" intensity="6"/>
  <heartrate ts="2021-10-14 12:00:00" value="74"/>
  <step ts="2021-10-14 12:00:00" value="128"/>
  <gsr ts="2021-10-14 12:00:00" value="0.45"/>
  <skin_temperature ts="2021-10-14 12:00:00" value="32.4"/>
  <acceleration ts="2021-10-14 12:00:00" value="0.12"/>
</patient>
```

### B. D1NAMO Multi-File CSV Schema:
* `sensor_data/<subject_id>/cgm.csv`: `[timestamp, glucose_mmol_l]`
* `sensor_data/<subject_id>/ecg.csv`: `[timestamp, ecg_microvolts]`
* `sensor_data/<subject_id>/acc.csv`: `[timestamp, acc_x, acc_y, acc_z]`
* `sensor_data/<subject_id>/breathing.csv`: `[timestamp, breathing_rate_rpm]`
* `sensor_data/<subject_id>/food.csv`: `[timestamp, image_id, carbs_g]`

---
*Certified for Phase 7C access and schema matrix.*
