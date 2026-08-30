# GlucoShield — Food Vision & Nutrition Validation Benchmark

## 1. Purpose & Scope
This directory contains the controlled scientific validation suite for the **GlucoShield Upstream Food Vision & Nutrition Pipeline**.

It evaluates:
1. **Food Recognition:** Candidate extraction from meal images.
2. **Nutrition Retrieval:** Database matching against USDA FoodData Central and Open Food Facts.
3. **Portion Scaling:** Accuracy of linear portion scaling across $50\text{g} - 250\text{g}$.
4. **Portion Error Sensitivity:** Impact of user portion over/underestimation on carbohydrate error ($\text{g}$).
5. **Human Correction Safety:** Traceability and enforcement of mandatory user confirmation.

## 2. Food Benchmark Cohort (17 Items)
* **Simple Foods ($N=4$):** Banana, Apple, White Rice, Bread.
* **Indian Foods ($N=6$):** Samosa, Idli, Dosa, Roti/Chapati, Dal (Lentils), Biryani.
* **Composite Dishes ($N=4$):** Pizza, Burger, Pasta, Fried Rice.
* **Packaged Foods ($N=3$):** Rolled Oats, Greek Yogurt, Digestive Biscuit.

## 3. Directory Layout
* `benchmark_cases.csv`: Defines the 17 benchmark cases and search queries.
* `ground_truth/food_ground_truth.csv`: Official reference macronutrients per 100g.
* `sample_images/`: Synthetic and representative test image fixtures.
* `results/`: Output JSON metric files.
* `figures/`: Publication-quality validation charts.
* `run_validation.py`: Complete automated validation script.
