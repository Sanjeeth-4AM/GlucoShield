# GlucoShield — Phase 7A V2 Architecture Options
**Document ID:** `GLUCOSHIELD-RPT-PHASE7A-ARCH-001`  
**Timestamp:** 2026-08-28T15:59:00 Local Time  
**Author:** Lead Deep Learning & Physiological Systems Engineer  
**Status:** **ARCHITECTURE PROPOSALS COMPLETE**  

---

## 1. Executive Summary & Design Principles

Based strictly on the data feasibility audit, we propose **three distinct architectural pathways** for **GlucoShield V2**.

All three options adhere to core scientific invariants:
1. **Zero Retraining of V1:** GlucoShield V1 remains permanently frozen as the reference baseline.
2. **Strict Causal Real-Time Processing:** No future information leakage during temporal aggregation or vision inference.
3. **Graceful Multimodal Degradation:** If any new modality (e.g. food photo or watch steps) is missing at runtime, the model gracefully falls back to core CGM dynamics without crashing.

---

## 2. Option A — Minimal Research Extension (Food Vision + Expanded Nutrition)

```
[Food Photo] ---> [Lightweight MobileNetV3/ViT] ---> [Carbs, Protein, Fat]
                                                              |
                                                              v
[24h CGM + Insulin + Static Biomarkers] ---------> [Expanded GRU V2 + ODE V2]
```

### A. Architectural Overview:
* **Focus:** Resolving the single largest failure boundary identified in Phase 6 ($+51.2\%$ error spike on unlogged meals) by developing a dedicated **Upstream Food Vision Module**.
* **Required Datasets:**
  * Dataset v1.0 (ShanghaiT1D/T2D) for continuous glucose forecasting.
  * **Nutrition5k / NutritionVerse** for training the Food Vision model.
* **New Components:**
  1. `FoodVisionEncoder`: MobileNetV3 / EfficientNet-B0 trained on Nutrition5k to output estimated `[carbs_g, protein_g, fat_g]`.
  2. `MultiMacronutrientGastricModel`: Expanding the ODE gut compartment ($S_1, S_2$) with total fat inhibition ($k_{\text{delay}}(\text{fat})$) and slow protein gluconeogenesis.
  3. `ExpandedNeuralInputs`: Dynamic channels expanded from 22 to 25 (`carbs`, `protein`, `fat`, `cob_total`).
* **Temporal Alignment:** The vision model runs on-demand when a photo is taken, outputting a meal event vector injected into the 15-minute sequence grid at timestamp $t$.
* **Missing-Data Strategy:** If no photo is taken, defaults to manual carb log or zero meal input.
* **ODE Integration:** Fat modulates gastric emptying rate parameter $k_{\text{empty}} = k_{\text{empty}, 0} / (1 + \beta \cdot \text{fat})$; protein enters plasma glucose pool via slow hepatic conversion $k_{\text{prot}} \cdot \text{protein}$.
* **Key Advantages:**
  * $100\%$ feasible using existing open datasets.
  * Direct targeted fix for unlogged and misestimated meal dynamics.
  * Zero reliance on external smartwatch hardware.

---

## 3. Option B — Strong Multimodal Digital Twin (Vision + Co-Recorded Wearables)

```
[Food Photo] ---------> [Food Vision Module] ---------> [Carbs / Macros]
                                                               |
[OhioT1DM / D1NAMO] --> [15m Resampling & Alignment] -> [Steps + HR + Temp]
                                                               |
                                                               v
[Unified Dynamic State: 28 Channels] -----------------> [Multimodal Hybrid Forecaster]
                                                         ├── Spatio-Temporal GRU
                                                         ├── 8-Compartment Exercise ODE
                                                         └── Multi-Gate Adaptive Fusion
```

### A. Architectural Overview:
* **Focus:** Building a comprehensive multimodal digital twin combining Food Vision with co-recorded wearable physiological telemetry (Steps, Heart Rate, Skin Temp, EDA).
* **Required Datasets:**
  * **OhioT1DM Dataset** (12 patients over 8 weeks, with 5-minute CGM, insulin, meals, and Empatica E4 wristband telemetry).
  * **D1NAMO Dataset** (29 patients with CGM, food photos, and Zephyr BioHarness ECG/accelerometer).
  * **Nutrition5k** for Food Vision.
* **New Components:**
  1. `WearableFeatureExtractor`: 15-minute aggregations of steps ($\text{step\_sum}$), mean heart rate ($\text{hr\_mean}$), heart rate reserve ($\text{hr\_reserve}$), and electrodermal volatility.
  2. `ExercisePhysiologyODE`: 8-compartment differential system adding:
     * Non-insulin-mediated glucose clearance $G_{\text{uptake}}(\text{steps}, \text{HR})$.
     * Acute exercise-induced hepatic glycogenolysis $E_{\text{glycogen}}(\text{high\_intensity})$.
  3. `HierarchicalAdaptiveFusionGate`: Blending weights $\alpha(k)$ modulated by exercise intensity, meal absorption phase, and neural uncertainty.
* **Missing-Data Strategy:** Wearable channels use a learned `modality_present` binary mask and causal forward-backward decay.
* **Key Advantages:**
  * Clinically comprehensive: Captures physical activity, which is the 2nd largest driver of acute glucose drops after insulin.
  * Fully defensible on peer-reviewed, co-recorded clinical datasets (OhioT1DM / D1NAMO).

---

## 4. Option C — Full Future Research Platform (Universal Sensor Suite)

```
+-----------------------------------------------------------------------------+
|                      UNIVERSAL MULTIMODAL INGESTION LAYER                   |
|  • Continuous Glucose Monitor (Dexcom / Freestyle Libre / Medtronic)        |
|  • Smart Insulin Pens & Automated Insulin Delivery (AID / OpenAPS)          |
|  • Real-Time Food Vision & Meal Log (RGB / RGB-D Image Telemetry)           |
|  • Smartwatch Wearables (Apple HealthKit / Garmin Health / Fitbit Web API)  |
|  • Sleep Staging & Circadian Biomarkers (Deep / REM / Wake Staging)         |
|  • Continuous Autonomic Stress Monitor (EDA / GSR / HRV RMSSD)              |
+-----------------------------------------------------------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------------+
|                       CROSS-ATTENTION MULTIMODAL TRANSFORMER                |
|  • Dynamic Modality Drop-Path (handles arbitrary missing sensors at runtime)|
|  • Physics-Constrained Cross-Modal Attention Layers                         |
+-----------------------------------------------------------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------------+
|                     10-COMPARTMENT WHOLE-BODY DIGITAL TWIN                  |
|  • Multi-Organ Mass Balance (Gut, Liver, Muscle, Interstitial, Adipose)     |
|  • Differentiable Sympathoadrenal & Exercise Dynamics                       |
+-----------------------------------------------------------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------------+
|                     CLINICAL DECISION & UNCERTAINTY ENGINE                  |
|  • Real-Time Trajectory, 80%/95% Bounded Intervals, 5 Acute Event Heads     |
|  • Counterfactual Multi-Action Simulator (Food + Insulin + Workout What-Ifs)|
+-----------------------------------------------------------------------------+
```

### A. Architectural Overview:
* **Focus:** The ultimate long-term clinical research platform uniting all known metabolic, nutritional, autonomic, and behavioral inputs into a cross-attentive multimodal transformer and 10-compartment whole-body digital twin.
* **Required Datasets:** Multi-center clinical trial data (requires prospective clinical data collection with synchronized CGM + Smartwatch + Food Camera + Smart Pen).
* **Key Features:**
  * Dynamic cross-attention mechanism that naturally handles arbitrary missing sensors (e.g. if the user takes off their watch or skips meal photos).
  * 10-compartment physiological simulator modeling liver glycogen stores, muscle GLUT-4 translocation, and stress-induced cortisol/epinephrine hepatic output.
* **Key Limitations:** Requires custom prospective clinical data collection and substantial engineering overhead.

---

## 5. Architectural Comparison Matrix

| Architectural Dimension | Option A (Minimal Vision Extension) | Option B (Strong Multimodal Digital Twin) | Option C (Full Universal Platform) |
|---|:---:|:---:|:---:|
| **Primary Focus** | Food Vision + Meal Macros | Vision + OhioT1DM / D1NAMO Wearables | Comprehensive Multi-Sensor Suite |
| **New Datasets Required** | Nutrition5k / NutritionVerse | OhioT1DM + D1NAMO + Nutrition5k | Multi-Center Prospective Clinical Trial |
| **Dynamic Feature Count** | 25 Channels | 28 Channels | 36+ Channels |
| **ODE Compartments** | 6 (Expanded Gut Kinetics) | 8 (Adds Exercise / Muscle Clearance) | 10 (Whole-Body Multi-Organ) |
| **Implementation Complexity** | **Low-Medium (Fastest)** | **Medium (Recommended)** | **Very High (Long-Term)** |
| **Scientific Validity** | **Very High (Clean Separations)** | **Highest (Real Co-Recorded Telemetry)** | **High (Requires Prospective Data)** |
| **Hardware Dependence** | Camera Phone Only | Camera Phone + Wristband | Full Suite of Wearables & Sensors |

---
*Certified for Phase 7A architecture planning.*
