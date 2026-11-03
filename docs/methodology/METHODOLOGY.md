# GlucoShield Machine Learning & Physiological Modeling Methodology

**Module:** Methodology & Scientific Foundation  
**Framework:** PyTorch 2.13, SciPy RK4, Scikit-Learn RobustScaler  
**Training Cohort:** Shanghai Continuous Glucose Monitoring Cohort (112 Patients)  
**Date:** November 3, 2026  

---

## 1. Multi-Task Recurrent Neural Architecture (`MultiTaskGlucoNet`)

The core continuous forecaster uses a custom Gated Recurrent Unit (GRU) with Layer Normalization, residual skip projections, and static phenotypic covariate fusion:

$$\mathbf{h}_t = \text{GRU}(\mathbf{x}_t, \mathbf{h}_{t-1})$$

where:
- $\mathbf{x}_t \in \mathbb{R}^{22}$: 22 dynamic features at timestep $t$ (15-min cadence).
- $\mathbf{h}_t \in \mathbb{R}^{128}$: 128-dimensional hidden recurrent state.

### Static Context Fusion
Nine static patient features ($Age, Gender, BMI, is\_T1D, HbA1c, TDI, ISF, CIR, Basal$) are normalized via `RobustScaler` and embedded through a two-layer multi-layer perceptron:

$$\mathbf{e}_{\text{static}} = \text{GELU}(\mathbf{W}_2 \cdot \text{GELU}(\mathbf{W}_1 \mathbf{s} + \mathbf{b}_1) + \mathbf{b}_2) \in \mathbb{R}^{32}$$

The static embedding is fused with the final recurrent state $\mathbf{h}_{96}$:

$$\mathbf{z}_{\text{fused}} = \text{Linear}_{160 \to 128}([\mathbf{h}_{96} \,\|\, \mathbf{e}_{\text{static}}])$$

### Dual Multi-Task Output Heads
1. **Continuous Multi-Horizon Trajectory Head:**  
   $$\hat{\mathbf{y}}_{\text{traj}} = \text{Linear}_{128 \to 20}(\mathbf{z}_{\text{fused}}) \in \mathbb{R}^{20} \quad (5\text{ hours ahead})$$
2. **Acute Glycemic Event Classification Head:**  
   $$\hat{\mathbf{p}}_{\text{events}} = \sigma(\text{Linear}_{128 \to 5}(\mathbf{z}_{\text{fused}})) \in [0, 1]^5$$  
   Predicting discrete probabilities for:
   - Hypoglycemia ($<70\text{ mg/dL}$): 1-hour, 2-hour, 4-hour horizons.
   - Hyperglycemia ($>180\text{ mg/dL}$): 2-hour, 4-hour horizons.

---

## 2. Physiological ODE Digital Twin (Hovorka 8-Compartment Model)

To ground forecasts in human metabolic conservation laws, GlucoShield integrates the non-linear Hovorka differential equation model solved with Runge-Kutta 4th Order ($dt=1\text{ min}$, aggregated to 15-min epochs):

### 1. Carbohydrate Ingestion & Gut Absorption
$$\frac{dQ_1}{dt} = -k_{\text{empt}} Q_1 + D(t), \quad \frac{dQ_2}{dt} = k_{\text{empt}} Q_1 - k_{\text{abs}} Q_2$$
$$R_a(t) = \frac{f \cdot k_{\text{abs}} \cdot Q_2(t)}{V_G \cdot BW}$$

### 2. Subcutaneous Insulin Absorption & Plasma Kinetics
$$\frac{dS_1}{dt} = u_{\text{ins}}(t) - \frac{S_1}{\tau_s}, \quad \frac{dS_2}{dt} = \frac{S_1 - S_2}{\tau_s}$$
$$U_I(t) = \frac{S_2(t)}{\tau_s}$$
$$\frac{dI_p}{dt} = \frac{U_I(t)}{V_I \cdot BW} - k_e I_p(t)$$

### 3. Remote Insulin Action & Glucose Kinetics
$$\frac{dX}{dt} = -k_a X(t) + k_b I_p(t)$$
$$\frac{dG_p}{dt} = R_a(t) - (EGP_0 - X(t)) G_p(t) - F_{01}^c - \frac{F_R}{V_G \cdot BW}$$
$$\frac{dG_{\text{cgm}}}{dt} = \frac{G_p(t) - G_{\text{cgm}}(t)}{\tau_{\text{sensor}}}$$

---

## 3. Dynamic Feature Contract (22 Causal Channels)

All features are constructed strictly without future data leakage:

| Channel # | Feature Name | Computation Formula / Source | Clinical Rationale |
|:---:|:---|:---|:---|
| 0 | `glucose` | Raw sensor reading (mg/dL) | Primary glycemic variable |
| 1 | `glucose_velocity` | $(G_t - G_{t-1}) / 15.0$ (mg/dL/min) | Directional trend |
| 2 | `glucose_accel` | $(V_t - V_{t-1}) / 15.0$ | Second-derivative inflection |
| 3–6 | `glucose_roll_*_1h` | Mean, std, min, max over 4 steps (1h) | Short-term volatility |
| 7–8 | `glucose_roll_*_3h` | Mean, std over 12 steps (3h) | Medium-term baseline |
| 9 | `glucose_roll_mean_6h`| Mean over 24 steps (6h) | Long-term circadian drift |
| 10–11| `sin_hour`, `cos_hour`| $\sin(2\pi \cdot h / 24), \cos(2\pi \cdot h / 24)$ | Cyclical diurnal embedding |
| 12 | `is_night` | $1.0$ if hour $\ge 23$ or $<6$, else $0.0$ | Nocturnal sensitivity shift |
| 13–15| `insulin_*` | Basal rate, bolus units, total insulin | Exogenous pharmacokinetics |
| 16 | `iob` | Exponential decay ($\tau_{1/2} = 2\text{ hours}$) | Insulin On Board estimation |
| 17–18| `carbs_estimate_g`, `meal_flag` | Carbohydrate mass, binary meal marker | Exogenous gut appearance |
| 19 | `cob` | Exponential decay ($\tau_{1/2} = 1\text{ hour}$) | Carbs On Board estimation |
| 20–21| `insulin_cum_2h`, `carbs_cum_2h` | Sum of insulin and carbs over 8 steps | Cumulative prandial pressure |
