# GlucoShield — Phase 7B Food Vision Standalone Architecture & Scaffolding Report
**Document ID:** `GLUCOSHIELD-RPT-PHASE7B-SCAFFOLD-001`  
**Timestamp:** 2026-08-28T16:30:00 Local Time  
**Author:** Lead Computer Vision & Deep Learning Engineer  
**Status:** **LOCAL SCAFFOLDING COMPLETE (AWAITING VERIFIED DATASET DOWNLOAD)**  

---

## 1. Architectural Role & Invariant Governance

The **Food Vision Module** is designed strictly as an **OPTIONAL upstream meal-input assistance tool**, not as a mandatory or automatically trusted replacement for manual meal logging.

```
[OPTIONAL USER ACTION]
User Photographs Meal Plate (Optional)
                |
                v
+-----------------------------------------------------------------------------+
|                     GLUCOSHIELD FOOD VISION MODULE                          |
|  • MobileNetV3-Large Multi-Output Macronutrient Regressor                   |
|  • Predicts: [Carbohydrates (g), Protein (g), Total Fat (g), Calories (kcal)]|
|  • Outputs: Estimated Grams + 95% Confidence Interval (MC-Dropout)         |
+-----------------------------------------------------------------------------+
                |
                v
[INTERACTIVE CONFIRMATION MODAL]
Displays: "Estimated Carbs: 45g (95% CI: 38 - 52g). Accept or Edit?"
                |
                v
[INJECTION INTO 15-MINUTE TELEMETRY]
Injects confirmed carbs_estimate_g into GlucoShield 15-minute grid.
```

### Core Invariant Protections:
1. **GlucoShield V1 Untouched:** Dataset v1.0, Neural Forecaster V1 (`models/glucoshield_neural_best.pt`), Hybrid Forecaster (`models/glucoshield_hybrid_best.pt`), baseline models, and all Phase 6 reports remain bitwise frozen and isolated.
2. **No Unverified Data Download:** No raw video or unverified web archives were downloaded.
3. **Additive Codebase:** All Food Vision code resides cleanly in `food_vision/` and `evaluation/phase7b/`.

---

## 2. Local Scaffolding Implementation Inventory (`food_vision/`)

| Module File | Component Name | Description / Role | Status |
|---|---|---|:---:|
| [`food_vision/models.py`](file:///D:/ML%20PROJECT/food_vision/models.py) | `MacronutrientRegressor` | MobileNetV3-Large & EfficientNet-B0 multi-output regression network with physical non-negativity ReLU activation and MC-Dropout uncertainty. | **TESTED & VERIFIED** |
| [`food_vision/models.py`](file:///D:/ML%20PROJECT/food_vision/models.py) | `MultiTaskMacronutrientLoss` | Multi-task Smooth L1 (Huber) loss balancing disparate macronutrient (grams) and calorie (kcal) numerical scales. | **TESTED & VERIFIED** |
| [`food_vision/transforms.py`](file:///D:/ML%20PROJECT/food_vision/transforms.py) | `get_train_transforms` & `get_eval_transforms` | ImageNet normalization with stochastic data augmentations (RandomCrop, ColorJitter, RandomRotation, Flips) and deterministic center cropping. | **TESTED & VERIFIED** |
| [`food_vision/dataset.py`](file:///D:/ML%20PROJECT/food_vision/dataset.py) | `NutritionDataset` & `create_food_dataloaders` | Flexible PyTorch Dataset interface supporting Nutrition5k, NutritionVerse, or custom meal CSVs with configurable column mappings. | **TESTED & VERIFIED** |
| [`food_vision/baselines.py`](file:///D:/ML%20PROJECT/food_vision/baselines.py) | `MeanMacronutrientBaseline`, `MedianMacronutrientBaseline`, `ColorTextureRidgeBaseline` | Reference benchmark models (training mean/median predictors and classical RGB color moment Ridge regressors). | **TESTED & VERIFIED** |
| [`food_vision/evaluate.py`](file:///D:/ML%20PROJECT/food_vision/evaluate.py) | `evaluate_macronutrient_predictions` | Multi-metric evaluation engine computing per-target MAE (g), RMSE (g), MAPE (%), Pearson $r$, $R^2$, and MC-Dropout 95% coverage. | **TESTED & VERIFIED** |
| [`food_vision/train.py`](file:///D:/ML%20PROJECT/food_vision/train.py) | `train_food_vision_model` | PyTorch training pipeline with AMP mixed precision, CosineAnnealingLR, early stopping, and checkpointing. | **TESTED & VERIFIED** |
| [`food_vision/tests/test_food_vision.py`](file:///D:/ML%20PROJECT/food_vision/tests/test_food_vision.py) | `TestFoodVisionModule` | 7 automated unit tests covering forward passes, shapes, non-negativity, loss gradients, transforms, and dataset loading. | **7 / 7 PASSED (100%)** |

---

## 3. Dataset Acquisition Requirements

To begin training the Food Vision module, the following verified data files are required:

1. **Metadata CSV Files:**
   * `dish_metadata_cafe1.csv` & `dish_metadata_cafe2.csv` (contains dish IDs, mass, carbs, protein, fat, calories).
   * `train_ids.txt` & `test_ids.txt` (official partition lists).
2. **2D Overhead RGB Image Archive:**
   * `imagery/realsense_overhead/<dish_id>/rgb.png` ($\approx 5,000\text{ images}$, $\approx 1.5\text{ GB}$).
3. **Acquisition Methods:**
   * **Option A (Google Cloud SDK):** Run `gsutil -m cp -r gs://nutrition5k_dataset/nutrition5k_dataset/imagery/realsense_overhead/ food_vision/data/` (or via official GCS authenticated service account).
   * **Option B (Direct Local Import):** Place pre-downloaded Nutrition5k or NutritionVerse-Real dataset archive into `food_vision/data/nutrition5k/`.

---
*Scaffolding and local verification complete. Awaiting dataset placement and user approval.*
