# GlucoShield Dataset Guide

---

## 1. What This Dataset Is

The **GlucoShield Dataset** is a high-resolution clinical time-series dataset designed to help patients and physicians manage diabetes proactively. 

Continuous Glucose Monitors (CGM) measure a patient's blood sugar every few minutes, creating a continuous stream of physiological data. However, knowing your *current* blood sugar is often not enough—by the time a glucose crash (hypoglycemia) or spike (hyperglycemia) happens, it is already difficult to correct.

* **What the dataset contains:** Continuous 15-minute physiological readings (glucose levels, meal carbohydrate intake, and insulin doses) from **112 real clinical patients** (12 with Type 1 Diabetes and 100 with Type 2 Diabetes), paired with their permanent clinical biomarkers (such as age, BMI, and lab test results).
* **What each data sample represents:** One continuous **24-hour observation window** (96 sequential 15-minute readings) of a patient's daily life.
* **The problem it solves:** Predicting unexpected glucose crashes and spikes hours in advance so proactive action can be taken safely.
* **What the model receives:** 24 hours of dynamic history (glucose, insulin, meals) + the patient's clinical profile.
* **What the model predicts:** A **5-hour continuous glucose trajectory** (20 future readings) + **5 acute clinical risk alerts** (1h/2h/4h hypoglycemia and 2h/4h hyperglycemia).

```
                      +-----------------------------+
                      |      Raw Patient Data       |
                      |   (CGM, Insulin, Meals, Lab)|
                      +-----------------------------+
                                     |
                                     v
                      +-----------------------------+
                      |   24-Hour History Window    |
                      |    (96 steps × 15 mins)     |
                      +-----------------------------+
                                     |
                                     v
                      +-----------------------------+
                      |   Dynamic + Static Inputs   |
                      |  (22 channels + 9 features) |
                      +-----------------------------+
                                     |
                                     v
                      +-----------------------------+
                      |      GlucoShield Models     |
                      | (Neural + ODE Digital Twin) |
                      +-----------------------------+
                                     |
                                     v
                      +-----------------------------+
                      |   5-Hour Future Forecast    |
                      | (20 Trajectory Points +     |
                      |  5 Acute Clinical Alerts)   |
                      +-----------------------------+
```

---

## 2. The Three Dataset Splits

To evaluate the system fairly, all data is partitioned strictly by **patient identity**. This ensures the model is tested on patients it has **never seen before**, proving that it truly learns physiological patterns rather than memorizing individual people.

| Dataset Split | Purpose | Unique Patients | Total Sequences | Used For |
|:---|:---|:---:|:---:|:---|
| **Training** | Model Parameter Learning | **78** (8 T1DM, 70 T2DM) | **19,749** | Fitting neural network weights, feature scalers, and baseline model parameters. |
| **Validation** | Model Selection & Tuning | **17** (2 T1DM, 15 T2DM) | **4,585** | Selecting optimal hyperparameters, tuning hybrid fusion gates, and early stopping. |
| **Test** | Final Scientific Evaluation | **17** (2 T1DM, 15 T2DM) | **4,113** | **One-time benchmark evaluation**. Never used during training or hyperparameter search. |
| **Total Cohort** | Full Clinical Dataset | **112 Patients** | **28,447 Sequences** | Complete locked clinical dataset v1.0. |

> **Patient Separation Guarantee:** Every patient belongs to exactly one split. A patient's data NEVER leaks across splits.

---

## 3. What Is One Sequence?

Each sample in the dataset is a **sliding 29-hour window** sliced from continuous patient monitoring:
* **First 24 Hours (96 timesteps):** Historical context given to the model as input.
* **Next 5 Hours (20 timesteps):** Future forecast target that the model attempts to predict.

```
|<------------------ Input History (24 Hours) ------------------>|<------- Future Forecast (5 Hours) ------->|
|                                                                 |                                           |
|  Step 1       Step 2       Step 3                  Step 96      |  Step 1       Step 2             Step 20  |
|  (t = 0m)    (t = 15m)    (t = 30m)  ...          (t = 24h)    |  (t = +15m)   (t = +30m)  ...    (t = +5h)|
+-----------------------------------------------------------------+-------------------------------------------+
|               96 timesteps × 15 minutes                         |         20 timesteps × 15 minutes         |
|               Model reads 22 dynamic features                   |         Model predicts glucose (mg/dL)    |
```

### Key Sequence Parameters
* **Timestep Duration:** Exactly **15 minutes** per step.
* **Historical Input Window:** **96 timesteps** = $96 \times 15\text{ min} = 24\text{ hours}$.
* **Future Forecast Horizon:** **20 timesteps** = $20 \times 15\text{ min} = 5\text{ hours}$.
* **Stride:** 4 steps (1 hour) between consecutive training sequence starts.

---

## 4. Input Data

Each training sample combines **22 dynamic time-series features** with **9 static patient features**.

### A. Dynamic Time-Series Inputs (22 Channels)
These features change every 15 minutes and describe the patient's continuous metabolic state:

| # | Input Feature | Meaning | Example Unit | Why It Matters |
|:---:|:---|:---|:---:|:---|
| **0** | `glucose` | Sensor glucose reading | $\text{mg/dL}$ | Primary metabolic state signal. |
| **1** | `glucose_velocity` | Rate of glucose change over 15 min | $\text{mg/dL / 15m}$ | Indicates upward momentum or downward crash. |
| **2** | `glucose_accel` | Rate of velocity change | $\text{mg/dL / 15m}^2$ | Detects turning points and inflections in glucose. |
| **3** | `glucose_roll_mean_1h` | 1-hour rolling average glucose | $\text{mg/dL}$ | Smooths short-term sensor noise. |
| **4** | `glucose_roll_std_1h` | 1-hour rolling standard deviation | $\text{mg/dL}$ | Measures short-term glucose volatility. |
| **5** | `glucose_roll_min_1h` | 1-hour rolling minimum glucose | $\text{mg/dL}$ | Captures recent dips. |
| **6** | `glucose_roll_max_1h` | 1-hour rolling maximum glucose | $\text{mg/dL}$ | Captures recent peaks. |
| **7** | `glucose_roll_mean_3h` | 3-hour rolling average glucose | $\text{mg/dL}$ | Medium-term postprandial trend. |
| **8** | `glucose_roll_std_3h` | 3-hour rolling standard deviation | $\text{mg/dL}$ | Medium-term glycemic instability. |
| **9** | `glucose_roll_mean_6h` | 6-hour rolling average glucose | $\text{mg/dL}$ | Long-term glycemic baseline. |
| **10** | `sin_hour` | Sine of hour-of-day | $[-1, 1]$ | Captures 24-hour circadian rhythms continuously. |
| **11** | `cos_hour` | Cosine of hour-of-day | $[-1, 1]$ | Distinguishes morning, evening, and night. |
| **12** | `is_night` | Night-time binary flag (23:00–06:00) | $0 \text{ or } 1$ | Flags nocturnal hypoglycemia vulnerability. |
| **13** | `insulin_basal` | Long-acting / background insulin dose | $\text{Units}$ | Models continuous metabolic baseline clearance. |
| **14** | `insulin_bolus` | Rapid-acting meal or correction insulin | $\text{Units}$ | Causes rapid glucose reduction. |
| **15** | `insulin_total` | Total insulin administered ($13 + 14$) | $\text{Units}$ | Total exogenous insulin influx. |
| **16** | `iob` | Insulin on Board | $\text{Units}$ | Remaining active circulating insulin. |
| **17** | `carbs_estimate_g` | Estimated meal carbohydrates | $\text{grams}$ | Causes postprandial glucose spike. |
| **18** | `meal_flag` | Binary meal intake indicator | $0 \text{ or } 1$ | Explicit indicator of an eating event. |
| **19** | `cob` | Carbs on Board | $\text{grams}$ | Remaining unabsorbed carbohydrates in gut. |
| **20** | `insulin_cum_2h` | Cumulative insulin past 2 hours | $\text{Units}$ | Measures short-term insulin stacking. |
| **21** | `carbs_cum_2h` | Cumulative carbs past 2 hours | $\text{grams}$ | Measures short-term carbohydrate load. |

**Total Dynamic Channels:** **22 features per timestep** ($96 \times 22 = 2,112$ values per 24-hour window).

---

### B. Static Patient Inputs (9 Clinical Features)
These features describe the patient's individual physiology and do not change from minute to minute:

| # | Static Feature | Meaning | Clinical Unit | Why It Is Used |
|:---:|:---|:---|:---:|:---|
| **0** | `age` | Patient chronological age | $\text{Years}$ | Age influences metabolic clearance and insulin sensitivity. |
| **1** | `bmi` | Body Mass Index ($\text{weight} / \text{height}^2$) | $\text{kg/m}^2$ | Correlates with insulin resistance and distribution volume. |
| **2** | `hba1c` | Glycated hemoglobin (long-term control) | $\text{mmol/mol}$ | Reflects 3-month average glucose control. |
| **3** | `glycated_albumin` | Glycated serum albumin | $\%$ | Reflects medium-term (2–3 week) glycemic control. |
| **4** | `fasting_glucose` | Morning baseline fasting blood glucose | $\text{mg/dL}$ | Personal baseline target ($G_b$) for the Digital Twin. |
| **5** | `fasting_c_peptide` | Fasting C-peptide hormone level | $\text{nmol/L}$ | Measures residual endogenous insulin production. |
| **6** | `macrovascular_comp_count` | Count of cardiovascular complications | $\text{Integer}$ | Clinical severity indicator. |
| **7** | `microvascular_comp_count` | Count of retinal/kidney/nerve complications| $\text{Integer}$ | Disease progression and metabolic dysfunction marker. |
| **8** | `is_t1dm` | Diabetes etiology ($1 = \text{T1DM}, 0 = \text{T2DM}$) | Binary | Distinguishes absolute insulin deficiency from resistance. |

**Total Static Features:** **9 clinical biomarkers per patient**.

---

## 5. How the Input Is Given to the Model

The inputs are fed into the deep learning and Digital Twin models as structured numerical tensors:

```
Dynamic Input Tensor:   [ Batch Size , 96 Timesteps , 22 Dynamic Channels ]
Static Input Tensor:    [ Batch Size , 9 Clinical Features ]
```

### What One Row Looks Like:
1. **Dynamic Tensor:** A $96 \times 22$ matrix representing 24 hours of 15-minute measurements.
2. **Static Tensor:** A 9-element vector describing that specific patient's clinical baseline.

### Robust Meal Carbohydrate Transformation
Clinical meal logs occasionally contain extreme entries (e.g. logging 660g when a patient weighs a 1200g bowl of seafood porridge including soup water). To prevent extreme outliers from destabilizing the neural networks, carbohydrate inputs are processed using a soft-clamped logarithmic transformation:

$$\text{carbs\_processed} = \log\left(1 + \min(\text{carbs}, 200)\right)$$

* **Why it is used:** For normal meals (10g to 80g), $\log(1 + x)$ is nearly linear, preserving accurate meal sizing. For extreme logging errors above 200g, the formula softly compresses the value, preventing model divergence while preserving the information that a very large meal occurred.

---

## 6. Output / Labels

The model performs two complementary tasks simultaneously (Multi-Task Learning):

### A. Future Glucose Forecasting (Trajectory)
The model forecasts continuous glucose values for the next **5 hours** at 15-minute intervals:

| Prediction Step ($k$) | Future Horizon Time | Prediction Meaning |
|:---:|:---:|:---|
| **$k = 1$** | **t + 15 minutes** | Immediate short-term trend |
| **$k = 2$** | **t + 30 minutes** | Rapid transient response |
| **$k = 3$** | **t + 45 minutes** | Peak insulin/meal onset |
| **$k = 4$** | **t + 1 Hour (60m)** | Primary clinical alert horizon |
| **$k = 8$** | **t + 2 Hours (120m)** | Standard postprandial peak |
| **$k = 12$** | **t + 3 Hours (180m)** | Digestion clearance phase |
| **$k = 16$** | **t + 4 Hours (240m)** | Late postprandial stability |
| **$k = 20$** | **t + 5 Hours (300m)** | Long-range basal equilibrium |

*All intermediate steps ($k=1 \dots 20$) are predicted simultaneously.*

### B. Risk Classification (5 Acute Clinical Alerts)
In addition to the continuous curve, the model outputs 5 calibrated probabilities for critical events:

| Risk Target | Prediction Horizon | Clinical Threshold | Meaning in Plain Language |
|:---|:---:|:---:|:---|
| `hypo_1h` | Next 1 Hour | $\min(G) < 70\text{ mg/dL}$ | Probability of a dangerous glucose crash within 60 minutes. |
| `hypo_2h` | Next 2 Hours | $\min(G) < 70\text{ mg/dL}$ | Probability of hypoglycemia within the next 2 hours. |
| `hypo_4h` | Next 4 Hours | $\min(G) < 70\text{ mg/dL}$ | Probability of hypoglycemia over the full postprandial window. |
| `hyper_2h` | Next 2 Hours | $\max(G) > 180\text{ mg/dL}$ | Probability of blood sugar spiking above safe range within 2 hours. |
| `hyper_4h` | Next 4 Hours | $\max(G) > 180\text{ mg/dL}$ | Probability of prolonged hyperglycemia over 4 hours. |

---

## 7. Dataset Design

The dataset architecture was chosen to reflect real-world clinical and engineering requirements:

1. **Sliding-Window Sequence Design:** Slicing continuous CGM records into overlapping 24-hour windows maximizes training sample efficiency while preserving realistic day-to-day transitions.
2. **24-Hour Context:** A full 24-hour lookback captures a patient's sleep-wake cycle, circadian insulin sensitivity shifts, and delayed digestion effects.
3. **15-Minute Resolution:** Matches the standard output frequency of commercial CGM sensors (Dexcom, Abbott Freestyle Libre).
4. **Multi-Horizon Outputs:** Predicting 15 minutes to 5 hours bridges the gap between immediate alerts (fast acting) and meal planning (long acting).
5. **Static Clinical Grounding:** Static features allow the model to adapt its predictions to an elderly T1DM patient vs. an overweight T2DM patient.
6. **Patient-Isolated Splitting:** Completely prevents data leakage and proves generalization to unseen individuals.
7. **Unified Trajectory & Risk Structure:** The same input sample trains both the regression forecaster and the classification alert heads.

---

## 8. Dataset Flow From Raw Data to Model

```
+--------------------------------------------------------------------------------+
|                        1. RAW PATIENT RECORDS                                  |
| Continuous CGM logs, insulin records, dietary diary entries, and lab assays.   |
+--------------------------------------------------------------------------------+
                                       |
                                       v
+--------------------------------------------------------------------------------+
|                      2. CLEANING & 15-MINUTE RESAMPLING                        |
| Interpolating minor dropouts (<30m) and resampling to regular 15-min intervals.|
+--------------------------------------------------------------------------------+
                                       |
                                       v
+--------------------------------------------------------------------------------+
|                       3. FEATURE & KINETICS ENGINEERING                        |
| Computing velocities, accelerations, rolling statistics, IOB, COB, and time sin|
+--------------------------------------------------------------------------------+
                                       |
                                       v
+--------------------------------------------------------------------------------+
|                         4. 24-HOUR SLIDING WINDOWS                             |
| Slicing into 96-step input sequences and 20-step future target sequences.       |
+--------------------------------------------------------------------------------+
                                       |
                                       v
+--------------------------------------------------------------------------------+
|                     5. LEAKAGE-FREE PATIENT-LEVEL SPLIT                        |
| 78 Training Patients (19,749 seqs) | 17 Val (4,585 seqs) | 17 Test (4,113 seqs)|
+--------------------------------------------------------------------------------+
                                       |
                                       v
+--------------------------------------------------------------------------------+
|                        6. TRAINING ROBUST SCALERS                              |
| Fitted EXCLUSIVELY on the Training split to prevent any forward data leakage.  |
+--------------------------------------------------------------------------------+
                                       |
                                       v
+--------------------------------------------------------------------------------+
|                         7. GLUCOSHIELD MODELS                                  |
| • Neural Forecaster V1 (GRU-128)                                               |
| • Mechanistic ODE Digital Twin (6-Compartment Physiology)                      |
| • Adaptive Gated Hybrid Fusion Engine                                          |
+--------------------------------------------------------------------------------+
                                       |
                                       v
+--------------------------------------------------------------------------------+
|                     8. DUAL-TASK CLINICAL PREDICTIONS                          |
| [ 20 Continuous Glucose Trajectory Points ] + [ 5 Calibrated Risk Probabilities ]|
+--------------------------------------------------------------------------------+
```

---

## 9. Diabetes Subgroup Distribution

The dataset spans both major forms of diabetes. The patient distribution across splits is strictly stratified:

| Cohort / Split | Total Patients | T1DM Patients | T2DM Patients | Total Sequences | T1DM Sequences | T2DM Sequences |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Train** | **78** | **8** ($10.3\%$) | **70** ($89.7\%$) | **19,749** | **2,514** ($12.7\%$) | **17,235** ($87.3\%$) |
| **Validation** | **17** | **2** ($11.8\%$) | **15** ($88.2\%$) | **4,585** | **449** ($9.8\%$) | **4,136** ($90.2\%$) |
| **Test** | **17** | **2** ($11.8\%$) | **15** ($88.2\%$) | **4,113** | **507** ($12.3\%$) | **3,606** ($87.7\%$) |
| **Total Cohort**| **112** | **12** ($10.7\%$) | **100** ($89.3\%$) | **28,447** | **3,470** ($12.2\%$) | **24,977** ($87.8\%$) |

### Exact Patient IDs by Split:
* **T1DM Patients ($N=12$):**
  * Train ($N=8$): `1001`, `1002`, `1003`, `1006`, `1009`, `1010`, `1011`, `1012`
  * Validation ($N=2$): `1005`, `1008`
  * Test ($N=2$): `1004`, `1007`
* **T2DM Patients ($N=100$):**
  * Train ($N=70$): `2000` through `2099` (70 patients)
  * Validation ($N=15$): `2014`, `2041`, `2046`, `2048`, `2050`, `2054`, `2058`, `2061`, `2076`, `2077`, `2079`, `2089`, `2090`, `2097`, `2098`
  * Test ($N=15$): `2001`, `2002`, `2020`, `2021`, `2023`, `2029`, `2032`, `2037`, `2052`, `2057`, `2059`, `2063`, `2075`, `2087`, `2095`

---

## 10. Data Leakage Protection

Data leakage occurs when information from the evaluation or future periods accidentally contaminates the training phase, giving falsely optimistic accuracy. GlucoShield enforces **three mathematical leakage barriers**:

### 1. Strict Patient Isolation (Zero Overlap)
$$\text{Train Patients} \cap \text{Validation Patients} = \emptyset$$
$$\text{Train Patients} \cap \text{Test Patients} = \emptyset$$
$$\text{Validation Patients} \cap \text{Test Patients} = \emptyset$$
* If Patient `1004` is in the Test set, **zero data** from Patient `1004` exists in Training or Validation.

### 2. Temporal Causality (No Peeking Forward)
* Every feature at timestep $t$ is computed using only data from $t$ and earlier ($\le t$). Rolling windows look strictly backward.

### 3. Scaler Fitting Isolation
* Feature normalization scalers (`RobustScaler`, `StandardScaler`) and static clinical medians were fitted **strictly on the 78 training patients**. Validation and Test sets were transformed using frozen training parameters.

---

## 11. Simple Example for Presentation

> **ILLUSTRATIVE EXAMPLE ONLY — NOT A REAL PATIENT**

Imagine a patient named **Alex** (Age: 58, BMI: 26.2, HbA1c: 7.2%, T2DM):

1. **What Alex did over the last 24 hours (Inputs):**
   * Woke up at 7:00 AM with fasting glucose of $115\text{ mg/dL}$.
   * Ate lunch at 1:00 PM ($65\text{g}$ carbohydrates) and took $4\text{ Units}$ of rapid insulin.
   * At 7:00 PM, ate dinner ($80\text{g}$ carbohydrates) with $6\text{ Units}$ of rapid insulin.
   * It is now 9:00 PM ($t = 0$), current glucose is $145\text{ mg/dL}$, with $1.8\text{ U}$ active insulin on board ($\text{IOB}$) and $22\text{g}$ active carbs on board ($\text{COB}$).

2. **What the model receives:**
   * Dynamic matrix: 96 rows of 15-minute readings $\times$ 22 dynamic measurements.
   * Static vector: `[Age=58, BMI=26.2, HbA1c=7.2, ..., is_t1dm=0]`.

3. **What GlucoShield predicts:**
   * **Future 5-Hour Curve:** Glucose will gently rise to a peak of $168\text{ mg/dL}$ at 10:15 PM ($t+75\text{min}$), then decline steadily to $108\text{ mg/dL}$ at 2:00 AM under active insulin action.
   * **Risk Assessment:**
     * `hypo_1h`: **$1.2\%$** (Safe)
     * `hypo_4h`: **$4.8\%$** (Low risk)
     * `hyper_2h`: **$18.5\%$** (Mild peak, stays below $180\text{ mg/dL}$ threshold)
   * **Status:** **STABLE & IN-RANGE (TIR = 100%)**. No emergency alert needed.

---

## 12. Dataset Summary at a Glance

```
========================================================================================
                          GLUCOSHIELD DATASET SUMMARY v1.0
========================================================================================
  Total Unique Patients:          112 Patients (12 Type 1 DM, 100 Type 2 DM)
  Total Sequences:                28,447 Windows (2,730,912 timesteps)
  Train Split:                    78 Patients (8 T1DM, 70 T2DM)  --> 19,749 Seqs (69.4%)
  Validation Split:               17 Patients (2 T1DM, 15 T2DM)  -->  4,585 Seqs (16.1%)
  Test Split (Held Out):          17 Patients (2 T1DM, 15 T2DM)  -->  4,113 Seqs (14.5%)
----------------------------------------------------------------------------------------
  Timestep Duration:              15 Minutes
  Input History Length:           96 Timesteps (24.0 Hours)
  Dynamic Input Features:         22 Channels per Timestep
  Static Patient Biomarkers:      9 Clinical Features
----------------------------------------------------------------------------------------
  Prediction Horizon:             20 Timesteps (5.0 Hours)
  Output Trajectory Points:       20 Continuous Glucose Values (mg/dL)
  Acute Risk Classification:      5 Multi-Horizon Probabilities (Hypo 1/2/4h, Hyper 2/4h)
----------------------------------------------------------------------------------------
  Data Leakage Protection:        Strict Patient-Level Disjointness (Zero Overlap)
  Missing Values / NaNs:          0 NaNs / 0 Infs across all 33 tensor files
  Status:                         PERMANENTLY LOCKED (v1.0.0-locked)
========================================================================================
```

---
*GlucoShield Clinical AI & Digital Twin Diabetes Companion.*
