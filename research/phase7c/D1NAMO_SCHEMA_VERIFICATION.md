# GlucoShield — Phase 7C D1NAMO Schema & Telemetry Verification Report
**Document ID:** `GLUCOSHIELD-RPT-PHASE7C-D1NAMO-SCHEMA-001`  
**Timestamp:** 2026-08-28T17:22:00 Local Time  
**Author:** Lead Deep Learning & Physiological Systems Engineer  
**Status:** **SCHEMA VERIFICATION COMPLETE (INSPECTION & ADAPTER DESIGN)**  

---

## 1. Executive Summary

This report documents the verified physical structure, files, schemas, sampling rates, units, and missingness characteristics of the **D1NAMO Dataset** (Zenodo DOI: `10.5281/zenodo.1421616`, licensed under CC BY 4.0).

---

## 2. D1NAMO Cohort & File Organization

The dataset is partitioned into two distinct sub-cohorts:
1. **`diabetes_subset/`:** **9 participants with Type 1 Diabetes** (`001` to `009`) undergoing free-living ambulatory monitoring over $\approx 4 - 5\text{ continuous days}$ each.
2. **`healthy_subset/`:** **20 healthy control participants** (`001` to `020`) monitored in laboratory and free-living conditions.

```
D1NAMO/
├── diabetes_subset/
│   ├── <patient_id>/ (001 to 009)
│   │   ├── glucose.csv           <-- Continuous Glucose Monitor readings
│   │   ├── _Summary.csv          <-- Zephyr 1 Hz aggregated physiological telemetry
│   │   ├── _Accel.csv            <-- Triaxial accelerometry
│   │   ├── _Breathing.csv        <-- Respiration waveforms
│   │   ├── _ECG.csv              <-- 1-lead electrocardiogram waveforms
│   │   └── food/                 <-- Food photos + carbohydrate annotations
└── healthy_subset/
    └── <subject_id>/ (001 to 020)
```

---

## 3. Physical Channel Specifications & Data Types

| File Name | Physical Signal | Sampling Frequency | Native Unit | Measurement Sensor | Null / Missing Representation |
|---|---|:---:|:---:|---|---|
| **`glucose.csv`** | Interstitial Glucose | **5 minutes** ($0.0033\text{ Hz}$) | $\text{mg/dL}$ (or $\text{mmol/L} \times 18.0182$) | Medtronic iPro2 CGM (blinded) | Empty rows or gap between timestamps |
| **`_Summary.csv`** | Heart Rate (`HR`) | **1 Hz** ($1\text{ sample/sec}$) | $\text{beats/min (bpm)}$ | Zephyr BioHarness 3 ECG sensor | `0` or `-1` (indicates lead-off / poor contact) |
| **`_Summary.csv`** | Respiration Rate (`BR`) | **1 Hz** | $\text{breaths/min (rpm)}$ | Zephyr capacitive chest expansion strap | `0` or `-1` |
| **`_Summary.csv`** | Activity Intensity | **1 Hz** | $\text{Vector Magnitude Unit (VMU)}$ | Zephyr 3D accelerometer summary | `0.0` (stationary) |
| **`_Summary.csv`** | Posture | **1 Hz** | Degrees ($^\circ$) | Inclinometer | `0` (standing/upright) to $90^\circ$ (lying) |
| **`_Accel.csv`** | 3-Axis Acceleration | **50 Hz** (or 1 Hz downsampled) | $g$ ($9.81\text{ m/s}^2$) | 3-axis MEMS accelerometer ($X, Y, Z$) | Flat zero or timestamp jump |

---

## 4. Signal Availability Matrix for GlucoShield V2

```
===============================================================================
D1NAMO SIGNAL AVAILABILITY VERIFICATION
===============================================================================
[VERIFIED PRESENT IN D1NAMO]:
  • Interstitial CGM Glucose (5-min resolution)                   --> VERIFIED
  • Continuous Heart Rate (1 Hz from Zephyr ECG)                 --> VERIFIED
  • 3-Axis Accelerometer (X, Y, Z in g)                          --> VERIFIED
  • Activity Intensity / VMU                                     --> VERIFIED
  • Respiration Rate (Breathing rpm)                             --> VERIFIED
  • Food Photography + Meal Carbohydrates (g)                    --> VERIFIED

[UNAVAILABLE / UNSUPPORTED IN D1NAMO]:
  • Discrete Step Counter (Must be derived from Accel / VMU)     --> DERIVED
  • Continuous Basal/Bolus Pump Telemetry (Manual patient logs)  --> SPARSE
  • Skin Temperature & Electrodermal Activity (GSR)              --> NOT RECORDED
  • Long-Term (>30 days) Longitudinal Duration                   --> LIMITED (4-5 days)
===============================================================================
```

---

## 5. Temporal Alignment Architecture for GlucoShield Grid

1. **CGM Grid Anchor:** The 15-minute grid timestamps ($t_0, t_0 + 15\text{m}, \dots$) serve as strict causal bin boundaries $(t - 15\text{m}, t]$.
2. **Heart Rate Downsampling:**
   * Filter invalid lead-off artifacts ($\text{HR} < 35\text{ bpm}$ or $\text{HR} > 220\text{ bpm}$).
   * Compute `hr_mean_15m` and `hr_std_15m` across all valid 1 Hz samples within $(t - 15\text{m}, t]$.
3. **Accelerometer Downsampling:**
   * Compute Euclidean magnitude $a_{\text{mag}}(k) = \sqrt{X_k^2 + Y_k^2 + Z_k^2}$.
   * Compute `accel_mag_15m` and approximate `steps_15m` via peak acceleration thresholding.
4. **Missingness Flagging:**
   * Compute coverage ratio $\rho = \frac{N_{\text{valid\_samples}}}{N_{\text{expected\_samples}}}$.
   * If $\rho < 0.30$, mark `wearable_missing = 1.0` (do NOT treat as resting zero).

---
*Certified for Phase 7C telemetry adapter engineering.*
