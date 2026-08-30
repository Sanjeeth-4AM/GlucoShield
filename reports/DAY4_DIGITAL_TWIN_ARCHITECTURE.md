# GlucoShield — Day 4 Mechanistic Digital Twin Architecture & Physiology Engine Specification
**Document ID:** `GLUCOSHIELD-SPEC-DAY4-TWIN-001`  
**Status:** ARCHITECTURE DESIGN & SPECIFICATION LOCKED  
**Phase:** Hybrid Digital Twin & Physiology Engine Design  
**Companion Neural Model:** `GLUCOSHIELD_NEURAL_FORECASTER_V1` (Locked)  
**Target Sampling Compatibility:** 15-Minute Sampled Continuous Glucose, Insulin, and Meal Regimens  

---

## 1. Digital Twin Definition & Architectural Vision

In GlucoShield, the **Digital Twin** is defined as an **explicit, state-space computational model of human metabolic physiology** that simulates the dynamic interactions between plasma glucose, interstitial glucose, subcutaneous insulin kinetics, and gastrointestinal carbohydrate absorption for an individual patient.

Unlike a purely data-driven black-box neural network, the GlucoShield Digital Twin:
1. **Enforces First-Principles Metabolic Conservation**: Glucose cannot appear without meal ingestion or hepatic production; glucose cannot drop without metabolic clearance, renal excretion, or insulin-mediated cellular uptake.
2. **Maintains Explicit Physical State Variables**: Tracks physiologically interpretable states ($\text{Plasma Glucose } G(t)$, $\text{Interstitial Glucose } G_{\text{CGM}}(t)$, $\text{Active Remote Insulin Action } X(t)$, $\text{Insulin-on-Board } \text{IOB}(t)$, $\text{Stomach Carb Pool } Q_1(t)$, $\text{Gut Carb Pool } Q_2(t)$, $\text{Carbs-on-Board } \text{COB}(t)$).
3. **Enables Counterfactual "What-If" Interventions**: Simulates hypothetical scenarios (e.g., *"What happens if the patient takes 4 units vs 6 units of insulin bolus before a 60g meal?"* or *"What happens if the meal is delayed by 45 minutes?"*).
4. **Fuses Mechanistic Long-Horizon Stability with Deep Sequence Pattern Recognition**: Couples the locked `GLUCOSHIELD_NEURAL_FORECASTER_V1` (which excels at short-term non-linear sequence modeling) with the ODE Physiology Engine (which maintains asymptotic stability over 2 to 5 hours).

---

## 2. Complete State-Space Compartmental Architecture

```
                       MEAL INTAKE D(t) [grams]
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │ Stomach Compartment   │ Q1(t) [mg]
                     │ (Gastric Emptying k_e)│
                     └───────────┬───────────┘
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │ Intestinal Pool       │ Q2(t) [mg]
                     │ (Absorption Rate k_a) │
                     └───────────┬───────────┘
                                 │
                                 ▼ Rate of Appearance Ra(t) [mg/dL/min]
                     ┌───────────────────────────────────────┐
                     │                                       │
INSULIN INPUT u(t) ──┼──► [Subcutaneous Absorption: S1 -> S2]│
  [Units/min]        │                  │                    │
                     │                  ▼                    │
                     │        Plasma Insulin: I(t)           │
                     │                  │                    │
                     │                  ▼                    │
                     │       Remote Insulin Action: X(t)     │
                     │                  │                    │
                     │                  ▼ (Insulin-Mediated  │
                     │                     Uptake: -X(t)*G)  │
                     │                                       │
                     │       PLASMA GLUCOSE: G(t) [mg/dL]    │
                     │  dG/dt = -p1(G-Gb) - X*G + Ra - EGP   │
                     └──────────────────┬────────────────────┘
                                        │
                                        ▼ Physiological Diffusion Lag (tau_d)
                             ┌───────────────────────┐
                             │ Interstitial Glucose  │
                             │ G_CGM(t) [mg/dL]      │ ◄── OBSERVED CGM SENSOR
                             └───────────────────────┘
```

---

## 3. Mathematical Formulation (Continuous-Time Differential Equations)

The metabolic physiology engine is formulated as a 6-dimensional continuous-time nonlinear state-space system $\mathbf{\dot{x}}(t) = \mathbf{f}(\mathbf{x}(t), \mathbf{u}(t); \boldsymbol{\theta}_p)$.

### 3.1. Subsystem 1: Gastrointestinal Carbohydrate Kinetics (2-Compartment Gut Model)
Let $D(t)$ be carbohydrate ingestion rate ($\text{g/min}$).
$$\frac{dQ_1(t)}{dt} = -k_{\text{empt}} \cdot Q_1(t) + 1000 \cdot D(t)$$
$$\frac{dQ_2(t)}{dt} = k_{\text{empt}} \cdot Q_1(t) - k_{\text{abs}} \cdot Q_2(t)$$
$$\text{Carbs-on-Board: } \text{COB}(t) = \frac{Q_1(t) + Q_2(t)}{1000} \quad [\text{grams}]$$
$$\text{Rate of Glucose Appearance: } R_a(t) = \frac{f \cdot k_{\text{abs}} \cdot Q_2(t)}{V_g \cdot \text{BW}} \quad [\text{mg/dL/min}]$$
* $Q_1(t)$: Solid/un-emptied carbohydrate pool in the stomach ($\text{mg}$).
* $Q_2(t)$: Soluble/digestible carbohydrate pool in the small intestine ($\text{mg}$).
* $k_{\text{empt}}$: Gastric emptying rate constant ($\text{min}^{-1}$).
* $k_{\text{abs}}$: Intestinal mucosal absorption rate constant ($\text{min}^{-1}$).
* $f$: Fraction of ingested carbohydrates reaching systemic circulation ($0.85-0.90$).
* $V_g$: Glucose distribution volume ($\approx 1.7-2.2\text{ dL/kg}$).
* $\text{BW}$: Patient body weight ($\text{kg}$, derived from $\text{BMI} \times \text{Height}^2$).

### 3.2. Subsystem 2: Subcutaneous Insulin Pharmacokinetics (2-Compartment Absorption)
Let $u_{\text{ins}}(t) = u_{\text{basal}}(t) + u_{\text{bolus}}(t)$ be total delivered insulin rate ($\text{mU/min} = 1000 \cdot \text{Units/min}$).
$$\frac{dS_1(t)}{dt} = u_{\text{ins}}(t) - \frac{S_1(t)}{\tau_s}$$
$$\frac{dS_2(t)}{dt} = \frac{S_1(t) - S_2(t)}{\tau_s}$$
$$\text{Insulin-on-Board: } \text{IOB}(t) = \frac{S_1(t) + S_2(t)}{1000} \quad [\text{Units}]$$
$$\text{Systemic Insulin Appearance Rate: } U_I(t) = \frac{S_2(t)}{\tau_s} \quad [\text{mU/min}]$$
* $S_1(t), S_2(t)$: Non-monomeric and monomeric subcutaneous insulin pools ($\text{mU}$).
* $\tau_s$: Time constant of subcutaneous insulin absorption ($\approx 45-65\text{ min}$).

### 3.3. Subsystem 3: Plasma Insulin & Remote Action (Modified Bergman Minimal Model)
$$\frac{dI(t)}{dt} = \frac{U_I(t)}{V_I \cdot \text{BW}} - k_e \left(I(t) - I_b\right) + \text{Endog}_{\text{insulin}}(t)$$
$$\frac{dX(t)}{dt} = -p_2 X(t) + p_3 \left(I(t) - I_b\right)$$
* $I(t)$: Plasma insulin concentration above basal ($\mu\text{U/mL}$).
* $I_b$: Fasting basal plasma insulin ($\mu\text{U/mL}$).
* $V_I$: Insulin distribution volume ($\approx 0.12-0.16\text{ L/kg}$).
* $k_e$: Fractional elimination rate of insulin from plasma ($\approx 0.10-0.15\text{ min}^{-1}$).
* $X(t)$: Remote/interstitial insulin action accelerating glucose disposal and suppressing hepatic glucose output ($\text{min}^{-1}$).
* $p_2$: Deactivation rate of remote insulin action ($\approx 0.015-0.030\text{ min}^{-1}$).
* $p_3$: Action rate parameter ($\approx 10^{-5}-10^{-4}\text{ min}^{-2}/(\mu\text{U/mL})$).
* $\text{Insulin Sensitivity: } S_I = \frac{p_3}{p_2} \quad [(\mu\text{U/mL})^{-1}\text{min}^{-1}]$.
* $\text{Endog}_{\text{insulin}}(t)$: Endogenous insulin secretion rate parameterized by patient fasting C-peptide:
  $$\text{Endog}_{\text{insulin}}(t) = (1 - \text{is\_t1dm}) \cdot \beta_{\text{cell}} \cdot \max(0, G(t) - G_{\text{target}})$$

### 3.4. Subsystem 4: Plasma Glucose Dynamics & Hepatic Flux
$$\frac{dG(t)}{dt} = - \left[ p_1 + X(t) \right] G(t) + p_1 G_b + R_a(t) - \Delta\text{EGP}(X(t))$$
$$\Delta\text{EGP}(X(t)) = \text{EGP}_0 \cdot \frac{X(t)}{\kappa_{\text{egp}} + X(t)}$$
* $G(t)$: Plasma glucose concentration ($\text{mg/dL}$).
* $p_1 = S_G$: Glucose effectiveness at basal insulin (fractional glucose clearance per min, $\approx 0.010-0.025\text{ min}^{-1}$).
* $G_b$: Basal plasma glucose level ($\text{mg/dL}$, parameterized from patient fasting glucose).
* $\Delta\text{EGP}$: Suppression of Endogenous (Hepatic) Glucose Production by active insulin action $X(t)$.

### 3.5. Subsystem 5: Subcutaneous Interstitial Glucose & Sensor Delay
CGM sensors measure interstitial subcutaneous glucose $G_{\text{CGM}}(t)$, not intravenous plasma glucose:
$$\frac{dG_{\text{CGM}}(t)}{dt} = \frac{1}{\tau_d} \left( G(t) - G_{\text{CGM}}(t) \right)$$
* $G_{\text{CGM}}(t)$: Interstitial glucose level measured by CGM ($\text{mg/dL}$).
* $\tau_d$: Physiological diffusion time lag between vascular and interstitial fluid ($\approx 8-15\text{ min}$).

---

## 4. Observed vs. Latent Variables Mapping (Dataset v1.0 Compatibility)

| Variable Symbol | Physical Meaning | Status in Dataset v1.0 | Units | Handling Strategy |
|---|---|:---:|:---:|---|
| $G_{\text{CGM}}(t)$ | Interstitial CGM Glucose | **Directly Observed** | $\text{mg/dL}$ | Primary state observation (Channel 0) |
| $D(t)$ | Carbohydrate Meal Inflow | **Directly Observed** | $\text{g}$ | Pulse/step input (Channel 17 `carbs_estimate_g`) |
| $u_{\text{ins}}(t)$ | Basal + Bolus Insulin Inflow | **Directly Observed** | $\text{Units}$ | Pulse/step input (Channels 13, 14, 15) |
| $\text{IOB}_{\text{obs}}(t)$ | Empirical Insulin on Board | **Observed Feature** | $\text{Units}$ | Boundary constraint & cross-check (Channel 16) |
| $\text{COB}_{\text{obs}}(t)$ | Empirical Carbs on Board | **Observed Feature** | $\text{grams}$ | Boundary constraint & cross-check (Channel 19) |
| $G(t)$ | Plasma Glucose Concentration | **Latent State** | $\text{mg/dL}$ | Reconstructed via EKF inversion through sensor lag $\tau_d$ |
| $X(t)$ | Remote Interstitial Insulin Action | **Latent State** | $\text{min}^{-1}$ | Estimated via ODE integration from insulin inputs |
| $I(t)$ | Plasma Insulin Above Basal | **Latent State** | $\mu\text{U/mL}$ | Reconstructed from subcutaneous compartments $(S_1, S_2)$ |
| $S_1(t), S_2(t)$ | Subcutaneous Insulin Pools | **Latent State** | $\text{mU}$ | Integrated from logged insulin delivery |
| $Q_1(t), Q_2(t)$ | Stomach & Intestinal Carb Pools | **Latent State** | $\text{mg}$ | Integrated from logged meal intake events |

---

## 5. Physiological Parameter Stratification & Clinical Constraints

All parameters are bound to clinically validated physiological ranges to prevent non-physical simulation divergence:

| Parameter | Description | Physiological Bounds | Population Default | Static Biomarker Prior Formulation |
|---|---|:---:|:---:|---|
| $S_I$ | Insulin Sensitivity | $[1.0 \times 10^{-5}, 5.0 \times 10^{-3}]$ | $1.2 \times 10^{-4}$ | $\propto \frac{1}{\text{BMI} \cdot \text{HbA1c}} \cdot \text{C-peptide}^{0.5}$ |
| $S_G$ ($p_1$) | Glucose Effectiveness | $[0.005, 0.040]\text{ min}^{-1}$ | $0.015\text{ min}^{-1}$ | Baseline metabolic glucose clearance |
| $p_2$ | Insulin Action Deactivation | $[0.010, 0.050]\text{ min}^{-1}$ | $0.025\text{ min}^{-1}$ | Inverse of insulin action half-life ($\approx 28\text{ min}$) |
| $\tau_s$ | Insulin Subcutaneous Lag | $[30.0, 90.0]\text{ min}$ | $55.0\text{ min}$ | Fast-acting insulin analog absorption lag |
| $k_{\text{empt}}$ | Gastric Emptying Rate | $[0.008, 0.040]\text{ min}^{-1}$ | $0.018\text{ min}^{-1}$ | Gastric half-time $\approx 35-45\text{ min}$ |
| $k_{\text{abs}}$ | Intestinal Absorption Rate | $[0.010, 0.050]\text{ min}^{-1}$ | $0.025\text{ min}^{-1}$ | Postprandial absorption rate |
| $\tau_d$ | Sensor Diffusion Lag | $[5.0, 18.0]\text{ min}$ | $10.0\text{ min}$ | Interstitial-plasma transport lag |
| $G_b$ | Basal Glucose Equilibrium | $[70.0, 220.0]\text{ mg/dL}$ | $110.0\text{ mg/dL}$ | Initialized from patient `fasting_glucose` |
| $V_g$ | Glucose Distribution Volume | $[1.4, 2.6]\text{ dL/kg}$ | $1.9\text{ dL/kg}$ | Scaled with patient body mass |
| $\beta_{\text{cell}}$ | Endogenous Secretion Gain | $[0.0, 0.05]\text{ mU/dL/mg}$ | $0.01\text{ (T2DM)}, 0.0\text{ (T1DM)}$ | Set strictly to $0$ if $\text{is\_t1dm} = 1$ |

---

## 6. Numerical Integration & 15-Minute Discrete-Time Formulation

Because CGM and intervention inputs in Dataset v1.0 are sampled at discrete $\Delta T = 15\text{ minutes}$, running a single-step discrete update would introduce excessive truncation error for fast dynamics (such as rapid bolus delivery).

### Integration Protocol:
1. **Sub-Stepping**: For each 15-minute macro interval $[t_k, t_{k+1}]$, the continuous ODE system is integrated using **Explicit Runge-Kutta 4th-Order (RK4)** with micro-step size $h = 1.0\text{ minute}$ ($15$ steps per CGM observation).
2. **Impulse Input Spreading**: Meal and insulin bolus events occurring at step $t_k$ are treated as zero-order hold rectangular pulses over the micro-steps or instantaneous state increments:
   $$Q_1(t_k^+) = Q_1(t_k^-) + 1000 \cdot \text{carbs}(t_k)$$
   $$S_1(t_k^+) = S_1(t_k^-) + 1000 \cdot \text{bolus}(t_k)$$
3. **State Bounds Enforcement**: After each micro-step, non-negativity is strictly projected:
   $$\mathbf{x}(t) \leftarrow \max\left( \mathbf{0}, \mathbf{x}(t) \right)$$
   $$G(t) \leftarrow \max\left( 20.0, G(t) \right) \quad [\text{prevents negative glucose}]$$

---

## 7. Online Patient Personalization & Calibration Strategy

Each patient exhibits unique insulin sensitivity, meal absorption rates, and basal production. Calibration proceeds in a **Two-Tier Strategy**:

```
Static Biomarkers (Age, BMI, HbA1c, C-peptide, T1D)
                      │
                      ▼
       [Tier 1: Prior Parameter Estimator]
         Maps static vector s -> theta_prior
                      │
                      ▼
     24-Hour History Window (96 timesteps CGM + Meals + Insulin)
                      │
                      ▼
       [Tier 2: Moving Horizon Estimator (MHE) / EKF Calibration]
         Minimizes || G_CGM_sim(t) - G_CGM_true(t) ||^2 + R_reg || theta - theta_prior ||^2
         over past 24 hours (t in [-24h, 0])
                      │
                      ▼
       Personalized Parameter Vector theta_p*
                      │
                      ▼
       Forward ODE Simulation for [t=0 to +5 hours]
```

### Tier 1: Biomarker Prior Parameter Estimator
An MLP prior network $\boldsymbol{\theta}_{\text{prior}} = \mathcal{M}_{\text{prior}}(\mathbf{s})$ initializes the patient's physiological parameters using the 9 static clinical biomarkers.

### Tier 2: 24-Hour Moving Horizon Calibration (Differentiable ODE)
Using the preceding 96 timesteps (24 hours) of CGM, insulin, and carb records:
$$\boldsymbol{\theta}_p^* = \arg\min_{\boldsymbol{\theta}} \sum_{j=-95}^{0} \mathcal{L}_{\text{Huber}}\left( \hat{G}_{\text{CGM}}(t_j; \boldsymbol{\theta}), G_{\text{CGM}}^{\text{obs}}(t_j) \right) + \lambda_{\text{reg}} \left\| \boldsymbol{\theta} - \boldsymbol{\theta}_{\text{prior}} \right\|_{\boldsymbol{\Sigma}^{-1}}^2$$
Subject to $\boldsymbol{\theta}_{\text{min}} \le \boldsymbol{\theta} \le \boldsymbol{\theta}_{\text{max}}$.
Because the RK4 integrator is fully differentiable in PyTorch, this calibration is solved in **$<50\text{ ms}$ on GPU** via projected gradient descent (L-BFGS or AdamW).

---

## 8. Counterfactual "What-If" Simulation Engine

The core clinical utility of the Digital Twin is evaluating hypothetical patient decisions before execution:

$$\mathbf{Scenario: } \quad \tilde{\mathbf{u}}_{\text{future}} = \left\{ \left( \tilde{D}(t), \tilde{u}_{\text{ins}}(t) \right) \mid t \in [t_{\text{now}}, t_{\text{now}} + 5\text{h}] \right\}$$

### Supported Counterfactual Queries:
1. **Meal Dose Advisory**: *"If I eat 75g of carbs now instead of 40g, what is my projected glucose curve with my current 5U bolus?"*
2. **Insulin Timing Adjustment**: *"What happens if I take my bolus 20 minutes before the meal vs 15 minutes after the meal?"*
3. **Hypoglycemia Prevention / Rescue Carbs**: *"If my glucose is dropping and I consume 15g fast-acting glucose at $t+30\text{min}$, does it prevent the 2-hour crash?"*
4. **Correction Bolus Simulation**: *"What is the safest correction bolus to bring current $240\text{ mg/dL}$ down to $120\text{ mg/dL}$ without inducing hypoglycemia ($<70\text{ mg/dL}$)?"*

The Digital Twin simulates forward trajectories $\hat{G}_{\text{scenario}}(t)$ under each scenario and reports:
* **Projected Nadir (Lowest Glucose)** and **Time-to-Nadir**
* **Projected Peak (Highest Glucose)** and **Time-to-Peak**
* **Probability of Hypoglycemia ($<70\text{ mg/dL}$)** and **Time in Range ($70-180\text{ mg/dL}$)**

---

## 9. Hybrid Fusion Architecture (Neural Forecaster + ODE Digital Twin)

We formulate an **Adaptive Gated Uncertainty-Aware Hybrid Fusion Framework**:

```
                       Input History (96x22) + Future Interventions (20x3)
                                               │
                       ┌───────────────────────┴───────────────────────┐
                       │                                               │
                       ▼                                               ▼
         [GLUCOSHIELD_NEURAL_V1]                           [ODE DIGITAL TWIN]
         • Fast pattern recognition                        • First-principles conservation
         • Non-linear momentum                             • Mechanistic insulin/carb action
         • Trajectory: y_neural (20)                       • Trajectory: y_ode (20)
         • Uncertainty estimate: sigma_neural (20)         • Dynamic variance: sigma_ode (20)
                       │                                               │
                       └───────────────────────┬───────────────────────┘
                                               │
                                               ▼
                                 [HYBRID FUSION GATE ENGINE]
                                   Computes Dynamic Weight
                                   alpha(k, sigma_neural, Delta_metabolic)
                                               │
                                               ▼
                             y_hybrid(k) = alpha(k) * y_neural(k)
                                         + (1 - alpha(k)) * y_ode(k)
                                         + Residual_Correction(k)
```

### Fusion Weight Formulation $\alpha(k)$
The fusion weight $\alpha(k) \in [0, 1]$ allocated to the neural forecaster at horizon step $k \in \{1, \dots, 20\}$ is dynamically governed by:
$$\alpha(k) = \sigma\left( w_0 - w_k \cdot k - w_u \cdot \sigma_{\text{neural}}(k) + w_m \cdot M_{\text{active}}(k) \right)$$
* **Horizon Decay ($w_k \cdot k$)**: As horizon increases ($15\text{m} \to 5\text{h}$), $\alpha(k)$ naturally shifts weight toward the ODE model ($1-\alpha$) to prevent neural long-horizon drift.
* **Metabolic Activity Factor ($M_{\text{active}}$)**: When large unannounced meals or boluses occur, ODE physics governs metabolic response.
* **Neural Confidence ($\sigma_{\text{neural}}$)**: High uncertainty in deep network triggers fallback to the physiological ODE model.

---

## 10. Evaluation Protocol & Scientific Baselines

To rigorously prove the value of the Digital Twin, it will be benchmarked against:
1. **Multi-Output Ridge Baseline** (Day 2 locked baseline: Test RMSE = $35.80\text{ mg/dL}$).
2. **GLUCOSHIELD_NEURAL_FORECASTER_V1** (Day 3 locked model: Test RMSE = $34.90\text{ mg/dL}$).
3. **Pure Uncalibrated Population ODE** (Zero-shot minimal model with population parameters).
4. **Calibrated Standalone ODE Digital Twin** (MHE-calibrated without neural network).
5. **Full Hybrid Model (Neural + Calibrated ODE)**.

### Target Validation Criteria:
* **Horizon 2h to 5h RMSE Improvement**: Hybrid must beat standalone neural at long horizons ($k \ge 8$).
* **Clarke Error Grid Zone A+B**: Target $>95.5\%$ on test set.
* **Counterfactual Realism**: Plausibility check on simulated insulin/carb responses (e.g., higher bolus $\to$ monotonic glucose reduction).

---

## 11. Planned Codebase Implementation Structure

```
D:\ML PROJECT\
├── physiology/
│   ├── __init__.py
│   ├── compartments.py          # ODE equations (Gut, Subcut Insulin, Plasma, Remote Action, Sensor)
│   ├── integrator.py            # Differentiable RK4 micro-stepper with state clipping
│   ├── priors.py                # Static biomarker to physiological parameter prior network
│   ├── calibrator.py            # 24-hour MHE/EKF online parameter calibration engine
│   ├── simulator.py             # Forward simulator & What-If counterfactual intervention API
│   └── hybrid_fusion.py         # Adaptive Gated Fusion Layer combining GRU V1 + Digital Twin
├── experiments/
│   ├── run_digital_twin_eval.py # Comprehensive evaluation runner across test cohort
│   └── test_what_if_cases.py    # Unit & clinical verification tests for counterfactuals
└── reports/
    ├── DAY4_DIGITAL_TWIN_ARCHITECTURE.md
    └── DIGITAL_TWIN_IMPLEMENTATION_PLAN.md
```
