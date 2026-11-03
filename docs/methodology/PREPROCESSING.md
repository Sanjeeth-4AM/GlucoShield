# GlucoShield Preprocessing & Feature Engineering Specification

**Module:** Preprocessing & Data Engineering  
**Implementation Source:** [`build_final_dataset.py`](file:///D:/ML%20PROJECT/build_final_dataset.py), [`api/preprocessor.py`](file:///D:/ML%20PROJECT/api/preprocessor.py)  
**Date:** November 3, 2026  

---

## 1. Zero-Leakage Pipeline Architecture

The GlucoShield preprocessing pipeline strictly prevents data leakage by:
1. **Partition Isolation:** Fitting all normalizers (`RobustScaler` for dynamic features and `StandardScaler`/`RobustScaler` for static covariates) strictly on the **Training partition only**. The validation and test partitions are transformed using the frozen training statistics.
2. **Strictly Causal Rolling Features:** All moving-average, rolling standard deviation, and extrema windows are computed over past timesteps ($t-k$ to $t$) with `min_periods=1`. No forward-looking centering is permitted.
3. **Sliding-Window Sequence Extraction:** Multi-horizon sliding windows use a 96-timestep (24-hour) input window and a 20-timestep (5-hour) future target window, advanced with a 4-timestep (1-hour) stride.

```
       +-------------------------------------------------------+
       |            Raw 15-Minute Continuous CGM Stream         |
       +-------------------------------------------------------+
                                   |
                                   v
       +-------------------------------------------------------+
       |   Stage 1: Timestamp Alignment & Physiological Bounds |
       |   - Verify 15-minute sampling cadence                 |
       |   - Clip values to physiological range [20, 600]      |
       +-------------------------------------------------------+
                                   |
                                   v
       +-------------------------------------------------------+
       |   Stage 2: Causal Dynamic Feature Derivation          |
       |   - Velocity & acceleration (1st/2nd derivatives)     |
       |   - Causal rolling metrics (1h, 3h, 6h)               |
       |   - Diurnal harmonic embeddings (sin_hour, cos_hour)  |
       |   - Exponential pharmacokinetic decay (IOB & COB)     |
       +-------------------------------------------------------+
                                   |
                                   v
       +-------------------------------------------------------+
       |   Stage 3: Frozen RobustScaler Transformation         |
       |   - Apply training-partition-fitted feature_scaler    |
       |   - Output standardized 22-channel dynamic matrix     |
       +-------------------------------------------------------+
                                   |
                                   v
       +-------------------------------------------------------+
       |   Stage 4: Phenotypic Covariate Normalization         |
       |   - Transform 9 static clinical features              |
       |   - Output standardized static context vector         |
       +-------------------------------------------------------+
```

---

## 2. 22 Dynamic Input Channels Specification

| Index | Feature Key | Units | Formulation / Logic | Physiological Rationale |
|:---:|:---|:---:|:---|:---|
| 0 | `glucose` | mg/dL | $G_t$ | Primary continuous glucose state |
| 1 | `glucose_velocity` | mg/dL/min | $(G_t - G_{t-1}) / 15.0$ | Instantaneous trajectory trend |
| 2 | `glucose_accel` | mg/dL/min² | $(V_t - V_{t-1}) / 15.0$ | Second derivative trajectory curve |
| 3 | `glucose_roll_mean_1h`| mg/dL | $\frac{1}{4} \sum_{i=0}^3 G_{t-i}$ | Short-term smoothed glucose |
| 4 | `glucose_roll_std_1h` | mg/dL | $\sigma(G_{t-3:t})$ | Short-term glycemic variability |
| 5 | `glucose_roll_min_1h` | mg/dL | $\min(G_{t-3:t})$ | Acute downside excursion nadir |
| 6 | `glucose_roll_max_1h` | mg/dL | $\max(G_{t-3:t})$ | Acute upside excursion peak |
| 7 | `glucose_roll_mean_3h`| mg/dL | $\frac{1}{12} \sum_{i=0}^{11} G_{t-i}$ | Postprandial trajectory window |
| 8 | `glucose_roll_std_3h` | mg/dL | $\sigma(G_{t-11:t})$ | Postprandial dispersion index |
| 9 | `glucose_roll_mean_6h`| mg/dL | $\frac{1}{24} \sum_{i=0}^{23} G_{t-i}$ | Extended diurnal baseline |
| 10 | `sin_hour` | — | $\sin(2\pi \cdot \text{hour} / 24)$ | Continuous cyclical hour embedding |
| 11 | `cos_hour` | — | $\cos(2\pi \cdot \text{hour} / 24)$ | Orthogonal cyclical hour embedding |
| 12 | `is_night` | binary | $\mathbb{I}(\text{hour} \ge 23 \lor \text{hour} < 6)$ | Dawn phenomenon / nocturnal risk |
| 13 | `insulin_basal` | U/epoch | $u_{\text{basal}} \times 0.25$ | Continuous background insulin |
| 14 | `insulin_bolus` | U | Exogenous acute meal/correction dose | Acute insulin challenge |
| 15 | `insulin_total` | U | $u_{\text{basal}} + u_{\text{bolus}}$ | Total exogenous insulin load |
| 16 | `iob` | U | $\text{EWM}(\text{halflife}=8\text{ steps})$ | Insulin On Board estimation |
| 17 | `carbs_estimate_g` | g | Ingested carbohydrate mass | Exogenous glycemic appearance |
| 18 | `meal_flag` | binary | $\mathbb{I}(\text{carbs} > 0)$ | Prandial event indicator |
| 19 | `cob` | g | $\text{EWM}(\text{halflife}=4\text{ steps})$ | Carbs On Board estimation |
| 20 | `insulin_cum_2h` | U | $\sum_{i=0}^7 \text{insulin}_{t-i}$ | Cumulative 2-hour insulin pressure |
| 21 | `carbs_cum_2h` | g | $\sum_{i=0}^7 \text{carbs}_{t-i}$ | Cumulative 2-hour carbohydrate pressure |

---

## 3. 9 Static Clinical Features

| Index | Feature Key | Units | Typical Range | Biological Meaning |
|:---:|:---|:---:|:---:|:---|
| 0 | `age` | years | 18.0 – 80.0 | Baseline age-related metabolic decline |
| 1 | `gender_male` | binary | 0.0 (F) / 1.0 (M) | Sex-specific distribution differences |
| 2 | `bmi` | kg/m² | 18.5 – 45.0 | Adiposity and baseline peripheral resistance |
| 3 | `is_t1dm` | binary | 0.0 (T2D) / 1.0 (T1D) | Absolute endogenous beta-cell failure flag |
| 4 | `hba1c` | % | 5.0 – 14.0 | 90-day glycemic equilibrium |
| 5 | `total_daily_insulin` | U/day | 15.0 – 120.0 | Total clinical daily insulin requirement |
| 6 | `insulin_sensitivity_factor` | mg/dL/U | 20.0 – 80.0 | Expected glucose drop per unit of insulin |
| 7 | `carb_to_insulin_ratio` | g/U | 5.0 – 25.0 | Carbohydrate mass balanced by 1 unit |
| 8 | `basal_rate` | U/hour | 0.2 – 2.5 | Nocturnal background infusion rate |
