# GlucoShield — Phase 7A Scientific Prioritization & Roadmap
**Document ID:** `GLUCOSHIELD-RPT-PHASE7A-ROADMAP-001`  
**Timestamp:** 2026-08-28T16:00:00 Local Time  
**Author:** Lead Deep Learning & Physiological Systems Engineer  
**Status:** **PRIORITIZATION & ROADMAP DEFINED**  

---

## 1. Scientific Prioritization of Candidate Features

Candidate modalities are ranked from highest to lowest priority based on:
1. Expected quantitative impact on continuous glucose forecasting.
2. Direct relevance to resolving Phase 6 failure modes (e.g., $+51.2\%$ unlogged meal error spike).
3. Availability of verified, high-quality, co-recorded clinical datasets.
4. Mathematical and physiological validity.

---

### Master Scientific Priority Ranking:

```
[RANK 1: HIGHEST]  Food Vision (Carbohydrate & Macronutrient Estimation from Photos)
                   └── Directly solves #1 Phase 6 Failure Mode (Missed / Misestimated Meals).
                       Trained on Nutrition5k / NutritionVerse.

[RANK 2: HIGH]     Physical Activity & Step Telemetry (Steps / METs / Duration)
                   └── 2nd largest driver of acute glucose drops via GLUT-4 muscle uptake.
                       Supported by OhioT1DM / D1NAMO co-recorded datasets.

[RANK 3: HIGH]     Continuous Heart Rate & Heart Rate Reserve (HR / HRR)
                   └── Proxy for physical exertion and acute sympathetic arousal.
                       Supported by OhioT1DM / D1NAMO / Smartwatch PPG.

[RANK 4: MEDIUM]   Expanded Macronutrients (Total Fat & Protein)
                   └── Total Fat slows gastric emptying (delays peak); Protein causes slow 4h gluconeogenesis.
                       Extracted via Food Vision & Nutrition5k USDA lookup.

[RANK 5: MEDIUM]   Dietary Fiber (g) & Glycemic Index Modifiers
                   └── Soluble fiber slows glucose absorption rate (k_abs) in gut.

[RANK 6: LOW-MED]  Circadian Staging & Sleep Metrics (Sleep Duration & Stages)
                   └── Modulates morning hepatic insulin resistance (Dawn Phenomenon).
                       Partially captured by existing V1 circadian channels (sin_hour, cos_hour, is_night).

[RANK 7: LOW]      Autonomic Stress Proxies (HRV / Electrodermal Activity)
                   └── High measurement noise without clinical-grade EDA/GSR hardware.

[RANK 8: REJECTED] Saturated Fat & Trans Fat (Separate Acute Tracking)
                   └── SCIENTIFICALLY WEAK FOR 5-HOUR ACUTE FORECASTING.
                       Trans fats do not have distinct 15-minute acute glycemic absorption kinetics
                       compared to total lipids. Saturated/trans fats are chronic cardiovascular markers.
```

---

## 2. Estimated Phased Implementation Roadmap

```
+-----------------------------------------------------------------------------+
| PHASE 7B: MULTI-MODAL FOOD VISION MODULE (UPSTREAM MEAL INJECTOR)           |
| • Dataset Ingestion: Nutrition5k (5,000 lab-measured dishes) + NutritionVerse|
| • Model Architecture: Lightweight MobileNetV3 / EfficientNet Backbone       |
| • Targets: [Carbohydrates (g), Protein (g), Total Fat (g)]                  |
| • Output: Automated meal event injector replacing manual carbohydrate logs  |
+-----------------------------------------------------------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------------+
| PHASE 7C: WEARABLE PHYSICAL ACTIVITY & EXERCISE INTEGRATION                 |
| • Dataset Ingestion: OhioT1DM (12 pts, 8 weeks) / D1NAMO (29 pts)           |
| • Signals: 15-minute resampled Steps, Heart Rate, and Accelerometer METs    |
| • ODE Expansion: Adding muscle GLUT-4 non-insulin glucose clearance term    |
| • Multimodal Hybrid Forecaster V2 training and benchmark evaluation         |
+-----------------------------------------------------------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------------+
| PHASE 8: COMPANION REST API & INTERACTIVE DECISION DASHBOARD                |
| • Backend: FastAPI REST service wrapping decision_engine/pipeline.py       |
| • Features: Real-time CGM telemetry stream, 80%/95% bounded intervals,     |
|   5 acute event alert badges, food photo upload, and What-If simulator UI   |
+-----------------------------------------------------------------------------+
```

---
*Certified for Phase 7A planning completion.*
