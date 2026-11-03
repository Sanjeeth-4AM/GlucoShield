# GlucoShield V1 — Repository Forensic Architecture Audit
## Comprehensive Forensic Analysis of V1 Implementation, Contracts, Pipelines, and Dependencies Prior to Phase 12 V2 Architecture Upgrade

**Audit Date:** September 19, 2026  
**Auditor:** Lead Deep Learning Research Engineer & Physiological Modeler  
**Target File:** `reports/v2/repository_architecture_audit.md`  
**Status:** PHASE A COMPLETE — Full Repository Topology Mapped  

---

## 1. System Environment & Execution Context

- **Operating System:** Windows 11 Enterprise (10.0.26200-SP0)
- **Python Runtime:** Python 3.12.3 (64-bit AMD64)
- **Deep Learning Framework:** PyTorch 2.13.0+cu126
- **Compute Hardware:** NVIDIA GeForce RTX 4050 Laptop GPU (6,141 MiB VRAM, Compute Capability 8.9)
- **CUDA Runtime:** Active and verified (`torch.cuda.is_available() == True`)
- **Key Scientific Libraries:** NumPy 2.x, SciPy, Pandas, Scikit-Learn, Joblib

---

## 2. Current V1 Architecture Decomposition

The GlucoShield V1 system is a dual-branch hybrid predictive engine combining a deep recurrent neural forecaster with a mechanistic physiological Digital Twin via an adaptive gating layer and a non-linear residual head.

```
                                  [ PATIENT INPUTS ]
                                          │
        ┌─────────────────────────────────┴─────────────────────────────────┐
        │                                                                   │
 [ Dynamic 96x22 Scaled ]                                         [ Dynamic 96x22 Raw ]
 [ Static 9-ch Scaled   ]                                         [ Static 9-ch Raw   ]
        │                                                                   │
        ▼                                                                   ▼
┌───────────────────────────┐                                     ┌───────────────────────────┐
│   NEURAL FORECASTER V1    │                                     │  MECHANISTIC DIGITAL TWIN │
│ (GlucoShieldMultiTaskRNN) │                                     │ (Biomarker Prior Network) │
├───────────────────────────┤                                     ├───────────────────────────┤
│ • MealTransformLayer      │                                     │ • BiomarkerPriorNetwork   │
│ • InputProj (22 -> 128)   │                                     │   (9 static -> 8 params)  │
│ • 2-Layer GRU (Hidden 128)│                                     │ • Moving Horizon Calibrator│
│ • StaticPatientEncoder    │                                     │   (24h CGM Adam MHE)      │
│   (9 static -> 32 embed)  │                                     │ • RK4Integrator           │
│ • Shared Fusion (160->128)│                                     │   (Hovorka 2-compartment) │
│ • TrajectoryHead (20-step)│                                     │ • Forward ODE Unrolling   │
│ • RiskHead (5 logits)     │                                     │   (5h horizon, 20 steps)  │
└─────────────┬─────────────┘                                     └─────────────┬─────────────┘
              │                                                                 │
      y_neural (batch, 20)                                              y_ode (batch, 20)
              │                                                                 │
              └─────────────────────────────┬───────────────────────────────────┘
                                            │
                                            ▼
                              ┌───────────────────────────┐
                              │    ADAPTIVE FUSION GATE   │
                              │   (AdaptiveFusionGate)    │
                              ├───────────────────────────┤
                              │ • 5-dim Context:          │
                              │   [v, a, std_1h, ins, crb]│
                              │ • Linspace Base Logits    │
                              │ • Blending alpha(k) in 0..1│
                              └─────────────┬─────────────┘
                                            │
                                 y_hyb = alpha * y_neural
                                         + (1 - alpha) * y_ode
                                            │
                                            ▼
                              ┌───────────────────────────┐
                              │       RESIDUAL HEAD       │
                              │ (Linear 29->32 -> ReLU    │
                              │  -> Linear 32->20)        │
                              └─────────────┬─────────────┘
                                            │
                                      Final Forecast
                                   y_final (batch, 20)
```

---

## 3. V1 Data Flow & Temporal Sequence Mapping

1. **Temporal Dimensions:**
   - History Window: $T_{\text{past}} = 96$ time-steps at $15$-minute resolution ($24$ historical hours).
   - Forecast Horizon: $T_{\text{future}} = 20$ time-steps at $15$-minute resolution ($5$ future hours).
   - Stride: $4$ steps ($1$ hour shift between consecutive evaluation windows).
2. **Data Pipeline Execution:**
   - Raw data files are ingested and preprocessed via `scratch/cgmacros_preprocessor.py` or `dataset.py`.
   - Continuous dynamic sequences are normalized using `feature_scaler.joblib` (StandardScaler fitted on V1 training set).
   - Static clinical biomarkers are normalized using `static_scaler.joblib` (StandardScaler fitted on V1 training set).
   - Scaled inputs feed the neural network; raw physical inputs feed the MHE calibrator and RK4 ODE simulator.

---

## 4. V1 Feature Contracts

### 4.1 Dynamic Input Contract (Strictly 22 Channels)
| Channel Index | Feature Name | Description | Physical Unit |
| :---: | :--- | :--- | :--- |
| `0` | `glucose` | Interstitial continuous glucose monitor reading | $\text{mg/dL}$ |
| `1` | `glucose_velocity` | First temporal derivative ($\Delta G / \Delta t$) | $\text{mg/dL} / 15\text{min}$ |
| `2` | `glucose_accel` | Second temporal derivative ($\Delta^2 G / \Delta t^2$) | $\text{mg/dL} / (15\text{min})^2$ |
| `3` | `glucose_roll_mean_1h` | Trailing 1-hour moving average (4 steps) | $\text{mg/dL}$ |
| `4` | `glucose_roll_std_1h` | Trailing 1-hour glycemic standard deviation | $\text{mg/dL}$ |
| `5` | `glucose_roll_min_1h` | Trailing 1-hour minimum glucose | $\text{mg/dL}$ |
| `6` | `glucose_roll_max_1h` | Trailing 1-hour maximum glucose | $\text{mg/dL}$ |
| `7` | `glucose_roll_mean_3h` | Trailing 3-hour moving average (12 steps) | $\text{mg/dL}$ |
| `8` | `glucose_roll_std_3h` | Trailing 3-hour glycemic standard deviation | $\text{mg/dL}$ |
| `9` | `glucose_roll_mean_6h` | Trailing 6-hour moving average (24 steps) | $\text{mg/dL}$ |
| `10` | `sin_hour` | Circadian sine projection ($\sin(2\pi \cdot \text{hour} / 24)$) | $[-1, 1]$ |
| `11` | `cos_hour` | Circadian cosine projection ($\cos(2\pi \cdot \text{hour} / 24)$) | $[-1, 1]$ |
| `12` | `is_night` | Binary indicator for nocturnal period ($23:00\text{--}06:00$) | $\{0, 1\}$ |
| `13` | `insulin_basal` | Basal insulin delivery rate | $\text{Units} / 15\text{min}$ |
| `14` | `insulin_bolus` | Bolus insulin administration | $\text{Units} / 15\text{min}$ |
| `15` | `insulin_total` | Total insulin administered (`insulin_basal` + `insulin_bolus`) | $\text{Units} / 15\text{min}$ |
| `16` | `iob` | Active Insulin on Board via exponential decay curve | $\text{Units}$ |
| `17` | `carbs_estimate_g` | Carbohydrate intake estimate | $\text{grams} / 15\text{min}$ |
| `18` | `meal_flag` | Binary meal occurrence flag | $\{0, 1\}$ |
| `19` | `cob` | Active Carbs on Board via dual-exponential gastric curve | $\text{grams}$ |
| `20` | `insulin_cum_2h` | Cumulative insulin delivered over trailing 2 hours | $\text{Units}$ |
| `21` | `carbs_cum_2h` | Cumulative carbohydrates ingested over trailing 2 hours | $\text{grams}$ |

### 4.2 Static Input Contract (Strictly 9 Channels)
| Index | Biomarker Name | Description | Default Population Median |
| :---: | :--- | :--- | :---: |
| `0` | `age` | Chronological age | $61.0\text{ years}$ |
| `1` | `bmi` | Body Mass Index | $23.56\text{ kg/m}^2$ |
| `2` | `hba1c` | Glycated hemoglobin | $73.78\text{ mmol/mol}$ |
| `3` | `glycated_albumin`| Glycated albumin percentage | $22.6\%$ |
| `4` | `fasting_glucose` | Laboratory fasting plasma glucose | $160.2\text{ mg/dL}$ |
| `5` | `fasting_c_peptide`| Laboratory fasting C-peptide | $0.365\text{ nmol/L}$ |
| `6` | `macrovascular_comp_count` | Macrovascular complication burden | $0.0$ |
| `7` | `microvascular_comp_count` | Microvascular complication burden | $0.0$ |
| `8` | `is_t1dm` | Type 1 Diabetes diagnostic indicator | $0.0$ |

---

## 5. V1 Physics & Moving Horizon Estimation Pipeline

1. **Biomarker Prior Network (`physiology/priors.py`):**
   - Ingests raw 9-channel static biomarkers $\mathbf{x}_{\text{static}}$.
   - Multi-layer perceptron (Linear 9 $\rightarrow$ 32 $\rightarrow$ LayerNorm $\rightarrow$ ReLU $\rightarrow$ Linear 32 $\rightarrow$ 8 parameters).
   - Maps patient biomarkers to initial physiological parameter set:
     $$[S_I, S_G, p_2, \tau_s, k_{\text{empt}}, k_{\text{abs}}, \tau_d, G_b]$$
     strictly clamped to physiological bounds via sigmoid transformations (`physiology/constraints.py`).
2. **Moving Horizon Calibrator (`physiology/calibrator.py`):**
   - Optimizes trailing 24 hours of CGM trajectory.
   - Adjusts 4 parameters: $\delta = [\log S_{I,\text{mult}}, \log k_{\text{empt},\text{mult}}, \log S_{G,\text{mult}}, \Delta G_b]$ using Adam optimizer on CPU.
   - Pinned to CPU to eliminate sequential CUDA micro-kernel launch overhead.
3. **Forward Mechanistic Integrator (`physiology/integrator.py`):**
   - 4th-order Runge-Kutta (RK4) integrator unrolling Hovorka 2-compartment metabolic equations:
     - Plasma and tissue glucose kinetics: $dG_p/dt, dG_t/dt$
     - Insulin pharmacokinetics: $dI_l/dt, dI_p/dt$
     - Remote insulin action: $dX/dt$
     - Two-stage gut absorption kinetics: $dQ_1/dt, dQ_2/dt$
   - 5 microsteps per 15-minute macro interval ($dt = 3.0\text{ min}$).

---

## 6. V1 Fusion Mechanism & Demonstrated Failure Mode

### 6.1 Gating Equation
The V1 `AdaptiveFusionGate` calculates step-wise blending weights $\alpha(k) \in [0, 1]$ across horizon steps $k \in \{1, \dots, 20\}$:
$$\text{context} = [0.1 \cdot v_{\text{recent}}, 0.1 \cdot a_{\text{recent}}, 0.05 \cdot \sigma_{\text{1h}}, 0.1 \cdot \sum u_{\text{future}}, 0.01 \cdot \sum c_{\text{future}}] \in \mathbb{R}^5$$
$$\alpha(k) = \sigma\left( \text{horizon\_base\_logits}(k) + \text{Linear}_{5 \to 32 \to 20}(\text{context}) \right)$$
where $\text{horizon\_base\_logits} = \text{linspace}(2.2, -0.2, 20)$.

### 6.2 The Demonstrated Bottleneck
1. **Neural Domination:** During V1 hybrid training, the network learned that the neural model had lower empirical training loss than the physics ODE. The gate parameters adapted to assign a mean of **$91.47\%$** weight to the neural GRU ($\bar{\alpha} = 0.9147$) and only **$8.53\%$** to the physics ODE.
2. **Complete Factor Blindness in Neural Branch:** The neural GRU receives only the 22-channel dynamic contract. It has zero inputs for sleep duration, sleep efficiency, exercise intensity, or menstrual cycle phase.
3. **Severe Attenuation:** When an external factor modifies physics ODE parameters (e.g. sleep shifting ODE trajectory by $24.12\text{ mg/dL}$), the shift is multiplied by $(1 - \alpha) = 0.0853$, reducing it to $2.06\text{ mg/dL}$, and the residual head further shrinks it to $1.04\text{ mg/dL}$ ($95.71\%$ dilution).

---

## 7. V1 Uncertainty Quantification Mechanism

Implemented in `decision_engine/uncertainty.py`:
$$\sigma_{\text{disagree}} = 0.35 \cdot |y_{\text{neural}} - y_{\text{ode}}|$$
$$\sigma_{\text{aleatoric}}(k) = 6.0 + 0.65 \cdot k \quad (\text{heuristic linear growth from } 6.65 \text{ to } 19.0\text{ mg/dL})$$
$$\sigma_{\text{total}}(k) = \sqrt{\sigma_{\text{mc}}(k)^2 + \sigma_{\text{disagree}}(k)^2 + \sigma_{\text{aleatoric}}(k)^2}$$
$$\text{Interval}_{95\%}(k) = [y_{\text{hyb}}(k) - 1.96 \cdot \sigma_{\text{total}}(k), \; y_{\text{hyb}}(k) + 1.96 \cdot \sigma_{\text{total}}(k)]$$

### Demonstrated Limitation
Because $\sigma_{\text{aleatoric}}$ is hardcoded to a fixed linear ramp and independent of patient glycemic volatility, glucose rate-of-change, or physiological state, the nominal $95\%$ interval width averages $\pm 35.8\text{ mg/dL}$. In free-living T1D outpatients on HUPA-UCM, where empirical errors regularly reach $60\text{--}120\text{ mg/dL}$, empirical coverage collapses to **$64.04\%$**.

---

## 8. Verified Frozen V1 Artifacts

All four production artifacts have been verified via SHA-256 cryptographic hashing and remain strictly bitwise locked:

| Artifact Path | SHA-256 Hash Digest | Verification Status |
| :--- | :--- | :---: |
| `models/glucoshield_neural_best.pt` | `026af3341a91064136c38b0172f2aa6af34806913640a02270c7d82a28ea13fb` | **LOCKED & VERIFIED** |
| `models/glucoshield_hybrid_best.pt` | `89a67710aa4931246f9097674332cbfd9d1af3d20c722c04d806ef66e47298d1` | **LOCKED & VERIFIED** |
| `data/metadata/feature_scaler.joblib`| `757f5c99e294dc8c5698a42cee1843853e8506df5203508aa71a1462d545972b` | **LOCKED & VERIFIED** |
| `data/metadata/static_scaler.joblib` | `fedc25f67dbcefd2c19ff38375568f3f2bc83ac1fa7c29840e5c81d33b479576` | **LOCKED & VERIFIED** |

---

## 9. Existing Test Infrastructure Audit

- `physiology/tests/test_physiology_engine.py`: 20 unit & scientific tests verifying RK4 integration, metabolic derivatives, parameter bounds, MHE causality, and CPU/GPU consistency (All 20 Passing).
- `decision_engine/tests/test_decision_engine.py`: Tests uncertainty interval properties, clinical risk categorization, and explanation generation.
- `scratch/phase11_sleep/test_sleep_invariant.py`: 3 unit tests verifying bitwise reproduction of $E_0$ when sleep modulation is inactive (All 3 Passing).
- `api/tests/`: Endpoints, authentication, and persistence tests.

---

## 10. Architectural File Boundary & V2 Implementation Plan

To guarantee absolute preservation of V1 while enabling unconstrained innovation in V2, the repository architecture will enforce strict namespace isolation:

### 10.1 Untouched Frozen V1 Production Files (DO NOT MODIFY)
- `models/glucoshield_neural_best.pt`
- `models/glucoshield_hybrid_best.pt`
- `data/metadata/feature_scaler.joblib`
- `data/metadata/static_scaler.joblib`
- `data/metadata/dataset_manifest.json`
- `neural/models.py`
- `neural/dataset.py`
- `neural/train.py`
- `physiology/calibrator.py`
- `physiology/compartments.py`
- `physiology/constraints.py`
- `physiology/hybrid_fusion.py`
- `physiology/integrator.py`
- `physiology/parameters.py`
- `physiology/priors.py`
- `physiology/state.py`
- `decision_engine/uncertainty.py`
- `scratch/phase11_*/` (all Phase 11 experimental reports and data archives)

### 10.2 New V2 Module Architecture (To Be Added)
- `models/v2/`:
  - `models/v2/__init__.py`
  - `models/v2/context_encoder.py` (Explicit physiological factor representation: Exercise, Sleep, Hormonal, Circadian)
  - `models/v2/neural_forecaster.py` (Factor-aware temporal GRU with context fusion)
  - `models/v2/factor_fusion_gate.py` (Regime-aware, factor-conditioned fusion gate)
  - `models/v2/uncertainty_head.py` (Physics-aware, regime-conditioned heteroscedastic/quantile uncertainty head)
  - `models/v2/hybrid_forecaster_v2.py` (End-to-end V2 Hybrid Forecaster)
- `training/v2/`:
  - `training/v2/__init__.py`
  - `training/v2/dataset_v2.py` (Multi-modal dataset loader supporting factor channels & missingness masks)
  - `training/v2/loss_v2.py` (Multi-task loss: trajectory Huber + risk BCE + pinball quantile + physics consistency)
  - `training/v2/train_v2.py` (V2 modular training & ablation runner)
- `inference/v2/`:
  - `inference/v2/__init__.py`
  - `inference/v2/pipeline_v2.py` (V2 end-to-end inference and prediction interval generation)
- `tests/v2/`:
  - `tests/v2/__init__.py`
  - `tests/v2/test_architecture.py` (Forward pass, dimension preservation, checkpoint reproducibility)
  - `tests/v2/test_factors.py` (Missingness masking, factor perturbation response, validity)
  - `tests/v2/test_causality.py` (Future feature/target leakage rejection)
  - `tests/v2/test_fusion.py` (Alpha boundedness, factor-conditioned responsiveness, counterfactual tests)
  - `tests/v2/test_uncertainty.py` (Quantile monotonicity, interval calibration, regime conditioning)
- `experiments/v2/`:
  - `experiments/v2/run_v2_ablations.py` (Ablation suite: E0 through E6)
  - `experiments/v2/evaluate_v2_domains.py` (Domain generalization on CGMacros, mcPHASES, HUPA-UCM)
- `reports/v2/`:
  - `reports/v2/repository_architecture_audit.md` (This document)
  - `reports/v2/V2_ARCHITECTURE_SPEC.md`
  - `reports/v2/V2_IMPLEMENTATION_REPORT.md`
  - `reports/v2/V2_VALIDATION_REPORT.md`
  - `reports/v2/V2_ABLATION_REPORT.md`
  - `reports/v2/V2_DOMAIN_SHIFT_REPORT.md`
  - `reports/v2/V2_UNCERTAINTY_REPORT.md`
  - `reports/v2/V2_FINAL_REPORT.md`

---

## 11. Potential Compatibility Risks & Mitigation Strategies

1. **Risk:** Contaminating V1 import paths or namespace collision.  
   **Mitigation:** Complete directory and module separation under `models/v2/`, `training/v2/`, and `tests/v2/`. V1 classes remain intact in `neural/` and `physiology/`.
2. **Risk:** Silent data leakage in multi-dataset factor integration.  
   **Mitigation:** Strict causality boundaries enforced by automated unit tests that inject future perturbations and verify zero gradient or output response.
3. **Risk:** Forcing physics artificially to mask neural superiority.  
   **Mitigation:** Gate learning is fully data-driven; alpha distributions are audited across volatility, factor activity, and horizons.
4. **Risk:** Overfitting small factor cohorts.  
   **Mitigation:** Explicit validity/missingness masking ($m_{\text{factor}} \in \{0, 1\}$) allowing V2 to train on pooled cohorts without hallucinating absent factors.
