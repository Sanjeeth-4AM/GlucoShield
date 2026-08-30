# GlucoShield — Phase 7B Food Vision Dataset Comparison Matrix
**Document ID:** `GLUCOSHIELD-RPT-PHASE7B-COMP-001`  
**Timestamp:** 2026-08-28T16:05:00 Local Time  
**Author:** Lead Computer Vision & Deep Learning Engineer  
**Status:** **DATASET EVALUATION COMPLETE (INSPECTION ONLY)**  

---

## 1. Executive Summary

This document provides a comparative evaluation of candidate food-image datasets for training the **GlucoShield Upstream Food Vision Module**.

The objective of the Food Vision Module is to perform direct **image-to-macronutrient regression**:
$$\mathbf{I}_{\text{meal}} \in \mathbb{R}^{3 \times H \times W} \xrightarrow{\text{Vision Backbone}} \left[\hat{m}_{\text{carbs}}, \; \hat{m}_{\text{protein}}, \; \hat{m}_{\text{fat}}, \; \hat{m}_{\text{calories}}\right] \in \mathbb{R}^4$$

---

## 2. Head-to-Head Dataset Comparison Matrix

| Evaluation Dimension | Nutrition5k (Google Research) | NutritionVerse-Real (Univ. of Waterloo) | NutritionVerse-Synth (Univ. of Waterloo) | D1NAMO Food Sub-Dataset (Hes-so Valais) | Food-101 (ETH Zurich) |
|---|:---:|:---:|:---:|:---:|:---:|
| **Primary Publication** | Thames et al., CVPR 2021 | Kayastha et al., 2023 | Kayastha et al., 2024 | Fraz et al., 2018 | Bossard et al., ECCV 2014 |
| **Official Repository** | GitHub `google-research-datasets/Nutrition5k` | Kaggle / Hugging Face | Kaggle / Hugging Face | Zenodo (Open Science) | ETH Zurich Computer Vision Lab |
| **Access Method** | Open (`gs://nutrition5k/`) | Open (Kaggle API / Direct) | Open (Kaggle API) | Open (Zenodo direct) | Open (TorchVision / Kaggle) |
| **Licence** | Creative Commons Attribution 4.0 (CC BY 4.0) | Creative Commons (CC BY-NC 4.0) | Creative Commons (CC BY-NC 4.0) | Open Academic Research | Academic Open |
| **Real vs. Synthetic** | **100% Real-World Dishes** (Google Cafeteria scanning rig) | **100% Real-World Dishes** (Manually captured) | Synthetic 3D Renderings (Photorealistic) | Real Free-Living Meals (Type 1 Diabetes patients) | Real Web-Scraped Photos |
| **Sample Size** | **$\approx 5,000\text{ unique dishes}$** ($250+\text{ ingredients}$) | $889\text{ images}$ ($251\text{ dishes}$) | $84,000\text{ synthetic images}$ | $\approx 2,000\text{ meal photos}$ | $101,000\text{ images}$ ($101\text{ classes}$) |
| **Carbohydrates (g)** | **YES (Lab-Measured)** | **YES (Lab-Measured)** | **YES (Ground-Truth)** | Estimated (Patient self-log) | **NO (Class label only)** |
| **Protein (g)** | **YES (Lab-Measured)** | **YES (Lab-Measured)** | **YES (Ground-Truth)** | **NO** | **NO** |
| **Total Fat (g)** | **YES (Lab-Measured)** | **YES (Lab-Measured)** | **YES (Ground-Truth)** | **NO** | **NO** |
| **Total Calories (kcal)**| **YES (Lab-Measured)** | **YES (Lab-Measured)** | **YES (Ground-Truth)** | **NO** | **NO** |
| **Total Dish Mass (g)** | **YES (Precision Scale)** | **YES (Precision Scale)** | **YES (Ground-Truth)** | **NO** | **NO** |
| **Measurement Fidelity** | **Gold Standard** (Precision scales + USDA Food Database) | High (Precision scales + USDA) | Exact (3D Mesh Mass Model) | Low-Medium (Self-reported patient diaries) | N/A (Classification only) |
| **Train/Val/Test Splits**| **Official Pre-Defined Splits** (`dish_ids/splits/`) | Pre-defined train/test | Pre-defined train/val/test | Patient-level splits | Standard 75k / 25k split |
| **Full Raw Footprint** | $\approx 700\text{ GB}$ (Multi-angle 360° videos) | $\approx 800\text{ MB}$ (2D RGB) | $\approx 15\text{ GB}$ (2D RGB-D) | $\approx 1.5\text{ GB}$ | $\approx 5\text{ GB}$ |
| **Overhead 2D RGB Frame Subset Footprint** | **$\approx 1.2\text{ to } 2.5\text{ GB}$** (High efficiency) | $\approx 800\text{ MB}$ | $\approx 15\text{ GB}$ | $\approx 1.5\text{ GB}$ | $\approx 5\text{ GB}$ |
| **Suitability for Multi-Macro Regression** | **PERFECT (Primary Dataset)** | **EXCELLENT (Benchmark / Validation)** | **STRONG (Synthetic Augmentation)** | **OOD Free-Living Test Only** | **UNSUITABLE (No gram targets)** |

---

## 3. Dataset Selection Decision

### 1. Primary Dataset: **`Nutrition5k` (Google Research)**
* **Rationale:** It is the largest, most rigorously annotated real-world dataset in academic literature containing true per-dish gram measurements of **Carbohydrates, Protein, Fat, and Mass** measured via industrial scales and verified with USDA food databases.
* **Storage Optimization Strategy:** Rather than downloading the entire $700\text{ GB}$ multi-view video repository, we download **only the overhead 2D RGB image frames and dish metadata CSVs** ($\approx 1.5\text{ GB}$ total disk space), making ingestion fast, lightweight, and fully compatible with standard laptop storage.

### 2. Secondary & Cross-Domain Validation Dataset: **`NutritionVerse-Real`**
* **Rationale:** $889$ real-world dish images with lab-measured macronutrients. Acts as an untouched external validation set to test whether the Nutrition5k-trained model generalizes to independent photographic environments.

### 3. Discarded Datasets:
* **`Food-101`:** Discarded because it only provides categorical class labels (e.g. "pizza", "sushi") with zero portion-size or gram-weight ground truth.
* **`D1NAMO Food Sub-Dataset`:** Discarded for primary model training because it relies on coarse self-reported carbohydrate diaries without protein/fat ground truth (reserved for future exploratory out-of-distribution testing).

---
*Certified for Phase 7B dataset planning.*
