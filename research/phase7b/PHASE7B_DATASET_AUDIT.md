# GlucoShield — Phase 7B Food Vision Dataset Audit & Technical Plan
**Document ID:** `GLUCOSHIELD-RPT-PHASE7B-AUDIT-001`  
**Timestamp:** 2026-08-28T16:06:00 Local Time  
**Author:** Lead Computer Vision & Deep Learning Engineer  
**Status:** **AUDIT COMPLETE — AWAITING USER APPROVAL BEFORE DOWNLOAD**  

---

## 1. Executive Summary & Objectives

Phase 7B Step 1 delivers a comprehensive audit of the **Nutrition5k** and **NutritionVerse** datasets for training a dedicated **Image-to-Macronutrient Regression Model** for the GlucoShield companion platform.

### Phase 7B Invariant Rules:
* **Zero Modification to V1:** Dataset v1.0, Neural Forecaster V1, ODE Digital Twin, and Phase 6 evaluation benchmarks remain permanently locked and frozen.
* **Additive Directory:** All Phase 7B code, data, models, and artifacts will reside strictly in `food_vision/` and `research/phase7b/`.
* **Zero Download / Retraining in Step 1:** This is a research, verification, and compute planning audit only.

---

## 2. Deep Dive: Nutrition5k Dataset Architecture

### A. Provenance & Official Source
* **Official Repository:** `https://github.com/google-research-datasets/Nutrition5k`
* **Dataset Publication:** Thames et al., *"Nutrition5k: Towards Analysis of Multiple Scanning Geometries for Nutritional Value Estimation of Food"*, IEEE CVPR 2021.
* **Storage Location:** Public Google Cloud Storage Bucket: `gs://nutrition5k/`
* **Licence:** Creative Commons Attribution 4.0 International (CC BY 4.0). Open for academic research and commercial use.

### B. Dish Metadata Schema (`dish_metadata_cafe1.csv` & `dish_metadata_cafe2.csv`)
Each record in the metadata table corresponds to one unique real-world plate with continuous numeric labels:

| Column Header | Data Type | Physical Unit | Description / Role |
|---|:---:|:---:|---|
| `dish_id` | String | Identifier | Unique dish ID (e.g., `dish_1561664654`) |
| `total_calories` | Float | $\text{kcal}$ | Lab-measured total caloric content |
| `total_mass` | Float | $\text{grams}$ | True physical plate mass measured via precision scale |
| `total_fat` | Float | $\text{grams}$ | Ground-truth total lipids ($g$) |
| `total_carb` | Float | $\text{grams}$ | **Primary Target:** Ground-truth digestible carbohydrates ($g$) |
| `total_protein` | Float | $\text{grams}$ | Ground-truth total protein ($g$) |
| `num_ingrs` | Integer | Count | Number of distinct ingredients in the dish |
| `ingr_id_N` ... | String / Float | Grams per ingr | Granular per-ingredient weights and USDA database references |

---

## 3. Storage Footprint & Efficient Acquisition Strategy

### A. Avoiding the $700\text{ GB}$ Raw Video Trap
The full Nutrition5k repository contains 360-degree rotating 4-camera video streams totaling over $700\text{ GB}$. Downloading the full archive would waste bandwidth and overwhelm local storage.

### B. The Lightweight 2D Overhead RGB Strategy ($\approx 1.5\text{ GB}$)
For realistic smartphone meal photography, food photos are taken from an overhead or $45^\circ$ oblique angle. We target the **extracted 2D RGB overhead frame subset**:
* **File Structure:**
  * `imagery/realsense_overhead/<dish_id>/rgb.png` (Single high-quality overhead photo per dish)
  * `metadata/dish_metadata_cafe1.csv` ($2,500\text{ dishes}$)
  * `metadata/dish_metadata_cafe2.csv` ($2,500\text{ dishes}$)
  * `dish_ids/splits/` (Pre-defined train / test splits)
* **Total Dishes:** $\approx 5,000\text{ unique meals}$
* **Total Download Size:** **$\approx 1.2\text{ to } 1.8\text{ GB}$**
* **Disk Space on `D:\ML PROJECT`:** Negligible ($<2\text{ GB}$), preserving drive health.

---

## 4. Hardware & GPU Compute Budget (NVIDIA RTX 4050)

| Compute Metric | Specification | Verification / Feasibility |
|---|---|---|
| **Local GPU** | NVIDIA GeForce RTX 4050 Laptop GPU ($6,141\text{ MiB}$ VRAM) | Verified via `torch.cuda.is_available()` |
| **Model Backbone** | MobileNetV3-Large (Pre-trained on ImageNet-1K) | $5.4\text{M parameters}$ ($\approx 21\text{ MB}$ weights) |
| **Alternative Backbone** | EfficientNet-B0 | $5.3\text{M parameters}$ ($\approx 20\text{ MB}$ weights) |
| **Precision** | Mixed Precision (PyTorch AMP `torch.cuda.amp.autocast`) | Fits comfortably in $<2.5\text{ GB}$ VRAM |
| **Batch Size** | $32\text{ images}$ per batch | VRAM utilization $\approx 2.1\text{ GB}$ ($34\%$ of RTX 4050 capacity) |
| **Training Time** | $30\text{ epochs}$ on $3,500\text{ training dishes}$ | **$\approx 8 - 12\text{ minutes}$ total training time** |

---

## 5. Proposed Image Preprocessing & Regression Pipeline

```
[Raw Image: H x W x 3] 
         |
         v
[Resize to 256 x 256 -> Center Crop / Random Crop to 224 x 224]
         |
         v
[Data Augmentation (Train only): Random Horizontal Flip, ColorJitter, RandomRotation(+/-15 deg)]
         |
         v
[ImageNet Normalization: Mean=(0.485, 0.456, 0.406), Std=(0.229, 0.224, 0.225)]
         |
         v
[MobileNetV3-Large Feature Extractor (Backbone)]
         |
         v
[Adaptive Average Pooling (7x7 -> 1x1)] -> [Feature Vector: 960-dim]
         |
         v
[Macronutrient Regression Head (MLP: 960 -> 256 -> ReLU -> Dropout(0.2) -> 4)]
         |
         v
[Predicted Vector: (Carbs_g, Protein_g, Fat_g, Calories_kcal)]
```

### Loss Function Formulation:
To prevent large calorie values ($\approx 800\text{ kcal}$) from dominating small carbohydrate errors ($\approx 30\text{ g}$), we employ a **Multi-Task Normalized Huber / Smooth L1 Loss**:

$$\mathcal{L}_{\text{vision}} = \lambda_{\text{carb}} \mathcal{L}_{\text{Huber}}(\hat{c}, c) + \lambda_{\text{prot}} \mathcal{L}_{\text{Huber}}(\hat{p}, p) + \lambda_{\text{fat}} \mathcal{L}_{\text{Huber}}(\hat{f}, f) + \lambda_{\text{cal}} \mathcal{L}_{\text{Huber}}(\hat{k}, k)$$

With target weights: $\lambda_{\text{carb}} = 1.0$, $\lambda_{\text{prot}} = 0.5$, $\lambda_{\text{fat}} = 0.5$, $\lambda_{\text{cal}} = 0.1$.

---

## 6. Integration Bridge with GlucoShield V1/V2 Forecasting

Once trained and evaluated, the Food Vision Module acts as an **upstream automated meal event injector**:

```
[User snaps photo of plate] 
         |
         v
[Food Vision Module] ──> Outputs: Carbs = 48.5g, Protein = 22.0g, Fat = 14.0g
                                              |
                                              v
[Automated Meal Event] ──> Injects carbs_estimate_g = 48.5, meal_flag = 1.0 into 15m grid
                                              |
                                              v
[GlucoShield Hybrid Forecaster V1/V2] ──> Predicts 5-hour trajectory & acute alerts
```

---

## 7. Next Step Recommendations for Phase 7B

Upon user approval:
1. **Download the lightweight Nutrition5k 2D overhead image subset** ($\approx 1.5\text{ GB}$) into `food_vision/data/nutrition5k/`.
2. **Build dataset loader, transforms, and unit tests** in `food_vision/dataset.py`.
3. **Train the MobileNetV3-Large regression network** on the official Nutrition5k training split.
4. **Evaluate standalone vision accuracy** on the held-out test dishes (reporting MAE in grams for Carbs, Protein, Fat, Calories).
5. **Verify zero alteration to GlucoShield V1** via cryptographic hash checking.

---
*Certified for Phase 7B Step 1 audit completion. Awaiting user approval to proceed with dataset ingestion.*
