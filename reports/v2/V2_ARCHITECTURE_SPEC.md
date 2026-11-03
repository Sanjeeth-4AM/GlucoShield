# GlucoShield Phase 12 — V2 Architecture Specification
## Complete Mathematical Formulation, Architectural Contracts, Factor Encoders, Adaptive Fusion, and Uncertainty Design

**Date:** September 19, 2026  
**Status:** APPROVED ARCHITECTURAL SPECIFICATION  
**Target File:** `reports/v2/V2_ARCHITECTURE_SPEC.md`  
**Namespace:** `models/v2/`, `training/v2/`, `inference/v2/`, `tests/v2/`, `reports/v2/`  

---

## 1. Architectural Overview & Design Objectives

GlucoShield V2 is designed to overcome the four fundamental failure modes identified during the Phase 11 diagnostic audit:

1. **Neural Factor Blindness:** V1's neural GRU model received only 22 dynamic channels (CGM, insulin, carbs, derivatives). In V2, a dedicated **Physiological Context Encoder** maps multi-modal telemetry (exercise MET/heart rate, sleep duration/efficiency, menstrual cycle phase, circadian phase) into a dense context embedding $\mathbf{z}_{\text{context}}$, directly conditioning the neural representation.
2. **Extreme Fusion Attenuation:** In V1, the adaptive fusion gate was fixed to an empirical mean of $\approx 91.5\%$ neural weight, diluting physics ODE factor perturbations by $95.7\%$. In V2, the **Factor-Aware Fusion Gate** conditions on physiological activity and model confidence, allowing the physics ODE to contribute dynamically when physiological perturbation is active.
3. **Uncertainty Calibration Collapse:** V1 utilized a static linear heuristic ($\sigma_{\text{aleatoric}} = 6.0 + 0.65k$) that was completely detached from patient glycemic volatility, causing empirical $95\%$ coverage to collapse to $64.04\%$ on free-living outpatients (HUPA-UCM). In V2, a **Physics-Aware, Regime-Conditioned Uncertainty Estimator** dynamically modulates prediction intervals based on real-time glycemic volatility, rate-of-change, active factor state, and neural-physics disagreement.
4. **Missingness Safety:** Real-world deployments and diverse clinical cohorts rarely supply all physiological signals simultaneously. V2 incorporates explicit **Validity and Missingness Masking** ($m_{\text{factor}} \in \{0, 1\}$), guaranteeing that an absent or unmeasured factor gracefully reverts to an unperturbed baseline representation without numerical instability, imputation artifacts, or data leakage.

---

## 2. End-to-End System Architecture

```
                          [ MULTI-MODAL INPUTS AT TIME T0 ]
                                          │
       ┌──────────────────────────────────┼──────────────────────────────────┐
       │                                  │                                  │
[ Dynamic CGM/Ins/Carbs ]      [ Physiological Telemetry ]          [ Static Clinical ]
  Shape: (batch, 96, 22)         (Exercise, Sleep, Hormones)         Biomarkers (9-ch)
       │                                  │                                  │
       ▼                                  ▼                                  │
┌───────────────────────┐      ┌─────────────────────────┐                   │
│   TEMPORAL ENCODER    │      │  CONTEXT ENCODER V2     │                   │
│ • InputProj (22->128) │      │ • Exercise Net (MET/HR) │                   │
│ • 2-Layer GRU (128)   │      │ • Sleep Net (Dur/Eff/τ) │                   │
│ • Last hidden state   │      │ • Hormonal Net (Phase)  │                   │
│   h_temporal (128)    │      │ • Missingness Masks m   │                   │
└──────────┬────────────┘      └────────────┬────────────┘                   │
           │                                │                                │
           │                     z_context ∈ R^32                            │
           │                                │                                │
           └───────────────────────┬────────┴────────────────────────────────┤
                                   │                                         │
                                   ▼                                         ▼
                     ┌───────────────────────────┐             ┌───────────────────────────┐
                     │    CONTEXT FUSION LAYER   │             │   BIOMARKER PRIOR & MHE   │
                     │  Cat([h_temp, z_ctx, s])  │             │ • BiomarkerPriorNetwork   │
                     │  Linear(169 -> 128)       │             │ • 24h Moving Horizon MHE  │
                     │  LayerNorm + ReLU         │             │   (SI, Gb, k_empt, SG)    │
                     └─────────────┬─────────────┘             └─────────────┬─────────────┘
                                   │                                         │
                                   ▼                                         ▼
                     ┌───────────────────────────┐             ┌───────────────────────────┐
                     │     NEURAL HEADS V2       │             │  MECHANISTIC DIGITAL TWIN │
                     │ • Trajectory: y_neu (20)  │             │ • Factor-Modulated ODE    │
                     │ • Quantile 80%: q10, q90  │             │ • RK4 Forward Simulation  │
                     │ • Quantile 95%: q025, q975│             │ • Trajectory: y_ode (20)  │
                     │ • Acute Risk Logits (5)   │             │                           │
                     └─────────────┬─────────────┘             └─────────────┬─────────────┘
                                   │                                         │
                         y_neural (batch, 20)                       y_ode (batch, 20)
                                   │                                         │
                                   └────────────────────┬────────────────────┘
                                                        │
                                                        ▼
                                          ┌───────────────────────────┐
                                          │   FACTOR-AWARE FUSION     │
                                          │ • Dynamic Context Feature │
                                          │ • Factor Activity Energy  │
                                          │ • Model Disagreement      │
                                          │ • Gating alpha(k) in (0,1)│
                                          └─────────────┬─────────────┘
                                                        │
                                             y_fused = alpha * y_neu
                                                     + (1 - alpha) * y_ode
                                                        │
                                                        ▼
                                          ┌───────────────────────────┐
                                          │   REGIME UNCERTAINTY HEAD │
                                          │ • Heteroscedastic sigma(k)│
                                          │ • Volatility scaling      │
                                          │ • Calibrated 80% & 95% CIs│
                                          └─────────────┬─────────────┘
                                                        │
                                             Final Output Dictionary
                                       {trajectory, lower/upper_80,
                                        lower/upper_95, alpha, risks}
```

---

## 3. Explicit Physiological Factor Representation

### 3.1 Mathematical Specification of Factor Encoders
Each physiological domain $d \in \{\text{exercise}, \text{sleep}, \text{hormonal}\}$ is defined by a triplet:
$$(\mathbf{f}_d, m_d, \tau_d)$$
where:
- $\mathbf{f}_d \in \mathbb{R}^{K_d}$ is the continuous feature vector.
- $m_d \in \{0, 1\}$ is the validity/presence mask ($1 = \text{valid observation}, 0 = \text{absent/unmeasured}$).
- $\tau_d \ge 0$ is the elapsed causal time since factor occurrence.

#### Domain 1: Exercise / Physical Activity ($\mathbf{f}_{\text{ex}} \in \mathbb{R}^4$)
- Inputs:
  1. Trailing 1-hour mean MET (Metabolic Equivalent of Task): $\bar{M}_{1\text{h}} \ge 1.0$
  2. Trailing 1-hour peak heart rate reserve fraction: $\text{HRR} = (HR - HR_{\text{rest}}) / (HR_{\text{max}} - HR_{\text{rest}}) \in [0, 1]$
  3. Elapsed time since last exercise bout: $\tau_{\text{ex}} \ge 0\text{ hours}$
  4. Exercise intensity category: $\{0: \text{sedentary}, 1: \text{light}, 2: \text{moderate}, 3: \text{vigorous}\}$
- Feature Transformation:
  $$\mathbf{f}_{\text{ex}} = [\log(\bar{M}_{1\text{h}}), \text{HRR}, \exp(-\tau_{\text{ex}} / 3.0), \text{intensity} / 3.0]^T$$
- Encoder:
  $$\mathbf{e}_{\text{ex}} = m_{\text{ex}} \cdot \text{MLP}_{\text{ex}}(\mathbf{f}_{\text{ex}}) \in \mathbb{R}^{12}$$

#### Domain 2: Sleep Context ($\mathbf{f}_{\text{sl}} \in \mathbb{R}^5$)
- Inputs:
  1. Total Sleep Duration (hours): $D_{\text{sleep}} \in [0, 14]$
  2. Sleep Efficiency fraction: $E_{\text{sleep}} \in [0, 1]$
  3. Deep Sleep percentage: $P_{\text{deep}} \in [0, 1]$
  4. Cumulative 48-hour sleep debt: $\text{Debt} = \max(0, 7.5 - D_{\text{sleep}}) \in [0, 7.5]$
  5. Elapsed waking time: $\tau_{\text{wake}} \ge 0\text{ hours}$
- Causal Decay Modulation:
  $$\Psi_{\text{decay}} = \exp\left( - \frac{\ln(2) \cdot \tau_{\text{wake}}}{6.0} \right)$$
- Feature Transformation:
  $$\mathbf{f}_{\text{sl}} = [D_{\text{sleep}} / 8.0, E_{\text{sleep}}, P_{\text{deep}}, \text{Debt} / 4.0, \Psi_{\text{decay}}]^T$$
- Encoder:
  $$\mathbf{e}_{\text{sl}} = m_{\text{sl}} \cdot \text{MLP}_{\text{sl}}(\mathbf{f}_{\text{sl}}) \in \mathbb{R}^{12}$$

#### Domain 3: Hormonal / Menstrual Cycle Context ($\mathbf{f}_{\text{hm}} \in \mathbb{R}^3$)
- Inputs:
  1. Cycle phase one-hot: Follicular ($[1, 0]$), Luteal ($[0, 1]$), or Non-ovulating ($[0, 0]$)
  2. Estimated cycle day: $t_{\text{cycle}} / 28.0 \in [0, 1.5]$
  3. Progesterone surrogate proxy: $\Pi = \mathbb{I}(\text{Luteal}) \cdot \sin(\pi (t_{\text{cycle}} - 14) / 14)$
- Feature Transformation:
  $$\mathbf{f}_{\text{hm}} = [\mathbb{I}(\text{Follicular}), \mathbb{I}(\text{Luteal}), \Pi]^T$$
- Encoder:
  $$\mathbf{e}_{\text{hm}} = m_{\text{hm}} \cdot \text{MLP}_{\text{hm}}(\mathbf{f}_{\text{hm}}) \in \mathbb{R}^{8}$$

#### Domain 4: Circadian Phase Embedding ($\mathbf{f}_{\text{circ}} \in \mathbb{R}^4$)
- Continuous trigonometric harmonic basis:
  $$\mathbf{f}_{\text{circ}} = [\sin(2\pi t / 24), \cos(2\pi t / 24), \sin(4\pi t / 24), \cos(4\pi t / 24)]^T$$
- Encoder:
  $$\mathbf{e}_{\text{circ}} = \text{Linear}_{4 \to 8}(\mathbf{f}_{\text{circ}}) \in \mathbb{R}^{8}$$

### 3.2 Context Aggregation & Missingness Masking
The complete contextual representation is formed by concatenating all domain embeddings and projecting through a shared LayerNorm bottleneck:
$$\mathbf{z}_{\text{raw}} = [\mathbf{e}_{\text{ex}}, \mathbf{e}_{\text{sl}}, \mathbf{e}_{\text{hm}}, \mathbf{e}_{\text{circ}}, m_{\text{ex}}, m_{\text{sl}}, m_{\text{hm}}]^T \in \mathbb{R}^{43}$$
$$\mathbf{z}_{\text{context}} = \text{Sequential}\left( \text{Linear}_{43 \to 32}, \text{LayerNorm}(32), \text{GELU}(), \text{Dropout}(0.1) \right)(\mathbf{z}_{\text{raw}}) \in \mathbb{R}^{32}$$

**Guaranteed Invariant:** When a factor is unobserved ($m_d = 0$), its corresponding embedding $\mathbf{e}_d \equiv \mathbf{0}$. The inclusion of the binary masks $m_d$ explicitly informs downstream layers that the factor is unknown rather than zero.

---

## 4. Factor-Aware Temporal Neural Architecture

### 4.1 Temporal Sequence Encoder
The dynamic history sequence $\mathbf{X}_{\text{dynamic}} \in \mathbb{R}^{\text{batch} \times 96 \times 22}$ is projected and encoded:
$$\mathbf{H}_0 = \text{Dropout}\left( \text{ReLU}\left( \text{LayerNorm}\left( \text{Linear}_{22 \to 128}(\mathbf{X}_{\text{dynamic}}) \right) \right), p=0.1 \right)$$
$$\mathbf{h}_{\text{seq}}, \mathbf{h}_{\text{last}} = \text{GRU}_{\text{2-layer}}\left( \mathbf{H}_0 \right), \quad \mathbf{h}_{\text{temporal}} = \mathbf{h}_{\text{last}}[-1] \in \mathbb{R}^{\text{batch} \times 128}$$

### 4.2 Multi-Modal Context Fusion
Static clinical biomarkers are encoded: $\mathbf{s}_{\text{embed}} = \text{MLP}_{9 \to 16}(\mathbf{x}_{\text{static}})$.  
The fused latent patient state at forecast origin $T_0$ is:
$$\mathbf{v}_{\text{fused}} = [\mathbf{h}_{\text{temporal}}, \mathbf{z}_{\text{context}}, \mathbf{s}_{\text{embed}}]^T \in \mathbb{R}^{128 + 32 + 16 = 176}$$
$$\mathbf{z}_{\text{patient}} = \text{Sequential}\left( \text{Linear}_{176 \to 128}, \text{LayerNorm}(128), \text{GELU}(), \text{Dropout}(0.15) \right)(\mathbf{v}_{\text{fused}}) \in \mathbb{R}^{128}$$

### 4.3 Neural Multi-Task Heads
1. **Trajectory Point Head:**
   $$y_{\text{neural}}(k) = \text{Linear}_{64 \to 1}\left( \text{ReLU}\left( \text{Linear}_{128 \to 64}(\mathbf{z}_{\text{patient}}) \right) \right) \in \mathbb{R}^{20}$$
2. **Quantile Heads (for 80% and 95% Confidence Bounds):**
   - $q_{0.025}, q_{0.100}, q_{0.900}, q_{0.975} \in \mathbb{R}^{20}$
   $$\mathbf{q}_{\text{neural}} = \text{Linear}_{128 \to 4 \times 20}(\mathbf{z}_{\text{patient}})$$
3. **Clinical Risk Heads (5 Logits):**
   $$\mathbf{r}_{\text{logits}} = \text{Linear}_{64 \to 5}\left( \text{ReLU}\left( \text{Linear}_{128 \to 64}(\mathbf{z}_{\text{patient}}) \right) \right)$$

---

## 5. Factor-Aware Adaptive Physics Fusion

### 5.1 Formulation of Context-Aware Gating
The fusion gate $\boldsymbol{\alpha} \in (0, 1)^{20}$ must not remain stuck at a static $\approx 91.5\%$ neural allocation. It must dynamically respond to physiological perturbation and model confidence:

$$\boldsymbol{\alpha}(k) = \sigma\left( \mathbf{w}_{\text{base}}(k) + \mathbf{W}_{\text{context}} \boldsymbol{\phi}_{\text{gate}} + \mathbf{b}_{\text{gate}} \right)$$

where the gating context feature $\boldsymbol{\phi}_{\text{gate}} \in \mathbb{R}^{10}$ comprises:
1. Glycemic velocity: $|v(T_0)| \cdot 0.1$
2. Glycemic acceleration: $|a(T_0)| \cdot 0.1$
3. Trailing 1-hour glycemic volatility: $\sigma_{1\text{h}} \cdot 0.05$
4. Active Carbs on Board: $\text{COB} \cdot 0.01$
5. Active Insulin on Board: $\text{IOB} \cdot 0.1$
6. Active factor energy: $\|\mathbf{z}_{\text{context}}\|_2 \cdot 0.1$
7. Neural epistemic uncertainty: $\sigma_{\text{neural}}(k) \cdot 0.05$
8. Instantaneous neural-ODE disagreement: $|y_{\text{neural}}(k) - y_{\text{ode}}(k)| \cdot 0.05$
9. Exercise activity indicator: $m_{\text{ex}} \cdot \bar{M}_{1\text{h}} \cdot 0.1$
10. Sleep debt indicator: $m_{\text{sl}} \cdot \Psi_{\text{decay}} \cdot 0.5$

### 5.2 Conditional Gating Properties
- **Euglycemic, Steady-State Regime:** $\boldsymbol{\phi}_{\text{gate}} \approx \mathbf{0} \implies \boldsymbol{\alpha}(k)$ smoothly follows $\sigma(\mathbf{w}_{\text{base}})$, prioritizing the data-driven neural representation.
- **Active Physiological Perturbation (Post-Wake / Exercise):** Factor energy and disagreement rise, shifting $\boldsymbol{\alpha}(k)$ downward toward physics ODE where physiological constraints hold.
- **Extreme Disagreement:** When neural model uncertainty spikes during rapid swings, gate allocates greater weight to the bounded mechanistic Digital Twin.

### 5.3 Hybrid Trajectory Formulation
$$y_{\text{hybrid}}(k) = \boldsymbol{\alpha}(k) \odot y_{\text{neural}}(k) + (1.0 - \boldsymbol{\alpha}(k)) \odot y_{\text{ode}}(k)$$
$$y_{\text{final}}(k) = y_{\text{hybrid}}(k) + \text{ResidualHead}\left( [y_{\text{hybrid}}, \mathbf{z}_{\text{context}}, \mathbf{s}_{\text{embed}}] \right)$$

---

## 6. Physics-Aware, Regime-Conditioned Uncertainty Architecture

To solve the uncertainty calibration collapse on high-variance cohorts ($64.04\%$ on HUPA-UCM), V2 replaces the hardcoded linear heuristic with a multi-source **Regime-Conditioned Uncertainty Model**:

$$\sigma_{\text{total}}^2(k) = \sigma_{\text{epistemic}}^2(k) + \sigma_{\text{disagreement}}^2(k) + \sigma_{\text{regime}}^2(k, \boldsymbol{\theta})$$

where:
1. **Epistemic Uncertainty ($\sigma_{\text{epistemic}}$):**
   Derived directly from the neural quantile spread:
   $$\sigma_{\text{epistemic}}(k) = \frac{q_{0.90}(k) - q_{0.10}(k)}{2 \cdot 1.282}$$
2. **Mechanistic Disagreement ($\sigma_{\text{disagreement}}$):**
   $$\sigma_{\text{disagreement}}(k) = \beta_{\text{dis}} \cdot |y_{\text{neural}}(k) - y_{\text{ode}}(k)|$$
3. **Regime-Conditioned Aleatoric Volatility ($\sigma_{\text{regime}}$):**
   $$\sigma_{\text{regime}}(k) = \left( \sigma_{\text{base}} + \gamma_1 \cdot \sigma_{1\text{h}} + \gamma_2 \cdot |v(T_0)| + \gamma_3 \cdot \|\mathbf{z}_{\text{context}}\|_2 \right) \cdot \left( 1.0 + \kappa \cdot \frac{k}{20} \right)$$

### 6.1 Prediction Interval Construction
Calibrated intervals are computed across horizons $k \in \{1, \dots, 20\}$:
$$\text{Interval}_{80\%}(k) = \left[ \max\left(20.0, \; y_{\text{final}}(k) - 1.282 \cdot \sigma_{\text{total}}(k)\right), \; \min\left(500.0, \; y_{\text{final}}(k) + 1.282 \cdot \sigma_{\text{total}}(k)\right) \right]$$
$$\text{Interval}_{95\%}(k) = \left[ \max\left(20.0, \; y_{\text{final}}(k) - 1.960 \cdot \sigma_{\text{total}}(k)\right), \; \min\left(500.0, \; y_{\text{final}}(k) + 1.960 \cdot \sigma_{\text{total}}(k)\right) \right]$$

**Result:** During high-volatility T1D excursions ($\sigma_{1\text{h}} > 40\text{ mg/dL}$, $|v| > 3.0\text{ mg/dL/min}$), $\sigma_{\text{regime}}$ expands dynamically to $\pm 60\text{--}90\text{ mg/dL}$, preserving true $95\%$ empirical coverage without bloating intervals during quiet euglycemic periods.

---

## 7. Multi-Task Training Objective & Controlled Ablation Design

### 7.1 Loss Formulation
The V2 objective function is a structured linear combination of four focused terms:
$$\mathcal{L}_{\text{total}} = \lambda_{\text{traj}} \mathcal{L}_{\text{traj}} + \lambda_{\text{risk}} \mathcal{L}_{\text{risk}} + \lambda_{\text{quant}} \mathcal{L}_{\text{quant}} + \lambda_{\text{phys}} \mathcal{L}_{\text{phys}}$$

1. **Trajectory Loss ($\mathcal{L}_{\text{traj}}$):** Smooth Huber Loss ($\beta = 5.0\text{ mg/dL}$) on continuous 20-step glucose trajectories.
2. **Clinical Risk Loss ($\mathcal{L}_{\text{risk}}$):** Weighted binary cross-entropy across 5 acute risk categories.
3. **Pinball Quantile Loss ($\mathcal{L}_{\text{quant}}$):**
   $$\mathcal{L}_{\text{pinball}}(y, q_\tau) = \max\left( \tau (y - q_\tau), \; (1 - \tau)(q_\tau - y) \right), \quad \tau \in \{0.025, 0.100, 0.900, 0.975\}$$
4. **Physics Consistency Loss ($\mathcal{L}_{\text{phys}}$):** Penalizes unphysical deviations when the physics model is highly confident.

### 7.2 Pre-Registered Ablation Configurations

| Configuration | Trajectory Loss ($\mathcal{L}_{\text{traj}}$) | Explicit Factors ($\mathbf{z}_{\text{context}}$) | Factor Fusion Gate ($\boldsymbol{\alpha}$) | Quantile / Uncertainty ($\mathcal{L}_{\text{quant}}$) | Physics Consistency ($\mathcal{L}_{\text{phys}}$) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **$E_0$ (Frozen V1)** | Huber ($\beta=5.0$) | None | Static Heuristic | Heuristic Linear | None |
| **$E_1$ (Neural Base)** | Huber ($\beta=5.0$) | None | Static Heuristic | None | None |
| **$E_2$ (+ Factors)** | Huber ($\beta=5.0$) | **Active** | Static Heuristic | None | None |
| **$E_3$ (+ Dynamic Gate)**| Huber ($\beta=5.0$) | **Active** | **Active** | None | None |
| **$E_4$ (+ Uncertainty)** | Huber ($\beta=5.0$) | **Active** | **Active** | **Active** | None |
| **$E_5$ (+ Physics Cons)**| Huber ($\beta=5.0$) | **Active** | **Active** | **Active** | **Active** |
| **$E_6$ (Full V2)** | Huber ($\beta=5.0$) | **Active** | **Active** | **Active** | **Active** |

---

## 8. Causal Temporal Boundaries & Leakage Safety

1. **Strict Temporal Cutoff ($T_0$):** All features, telemetry measurements, and historical rolling windows must be indexed strictly at or before prediction origin $t \le T_0$.
2. **Forbidden Signals:**
   - Future CGM measurements: $y(t) \quad \forall t > T_0$.
   - Future insulin or carbohydrate administrations (unless explicitly testing hypothetical counterfactual scenarios).
   - Sleep telemetry from the waking period subsequent to $T_0$.
   - Post-exercise biometric responses that occur after $T_0$.
3. **Automated Leakage Rejection:** Automated tests will introduce artificial future perturbations ($\delta y(T_0 + k) \ne 0$) and verify that $\nabla_{\mathbf{X}_{\text{future}}} \hat{y} \equiv \mathbf{0}$.

---

## 9. Validation, Testing & Statistical Evaluation Protocol

1. **Participant-Level Paired Testing:** All cohort-level comparisons between $E_0$ (Frozen V1) and $E_i$ (V2 variants) must be evaluated via paired Wilcoxon signed-rank tests computed on participant means ($N=24$ for CGMacros, $N=37$ for mcPHASES, $N=23$ for HUPA-UCM).
2. **Domain Generalization:** No dataset pooling to hide poor performance. Metrics must be reported separately for:
   - Healthy / Prediabetes meal test domain (CGMacros)
   - Premenopausal Type 1 Diabetes domain (mcPHASES)
   - Free-living outpatient Type 1 Diabetes domain (HUPA-UCM)
3. **Uncertainty Metrics:** Evaluate empirical coverage, mean interval width, and Volatility-Conditioned Coverage across 3 volatility tertiles (low, medium, high $\sigma_{1\text{h}}$).
