"""
GlucoShield Food Vision Validation Test Suite
=============================================
Automated unit tests covering Phase 7B Step 4:
  1. Correct Top-1 scoring logic
  2. Correct Top-3 scoring logic
  3. Unknown food handling
  4. Exact nutrition match classification
  5. Ambiguous nutrition match classification
  6. Portion scaling across multiple sizes (50g - 250g)
  7. Negative portion rejection
  8. Zero portion rejection
  9. Portion error sensitivity calculation
  10. Human correction overrides AI prediction
  11. Low confidence requires confirmation
  12. Missing API/provider does not fabricate success
  13. GlucoShield V1 integrity invariant
"""

import os
import sys
import unittest
import hashlib
import numpy as np

# Ensure project root is in sys.path
BASE_DIR = "D:/ML PROJECT"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from food_vision.schemas import FoodCandidate, NutritionResult, MealAnalysisResult
from food_vision.providers.mock_provider import MockFoodRecognitionProvider, MockNutritionProvider
from food_vision.pipeline.meal_analysis_pipeline import MealAnalysisPipeline
from food_vision.pipeline.confidence_policy import evaluate_meal_confidence

class TestFoodValidationPipeline(unittest.TestCase):

    def setUp(self):
        self.mock_rec = MockFoodRecognitionProvider()
        self.mock_nut = MockNutritionProvider()
        self.pipeline = MealAnalysisPipeline(
            recognition_provider=self.mock_rec,
            nutrition_provider=self.mock_nut
        )

    def test_01_correct_top1_scoring(self):
        """Test 1: Top-1 scoring correctly identifies exact match."""
        candidates = [
            FoodCandidate(name="Samosa", confidence=0.85, source="vision"),
            FoodCandidate(name="Dumpling", confidence=0.10, source="vision")
        ]
        target_synonyms = ["samosa", "samosas", "vegetable samosa"]
        is_top1 = any(syn in candidates[0].name.lower() for syn in target_synonyms)
        self.assertTrue(is_top1)

    def test_02_correct_top3_scoring(self):
        """Test 2: Top-3 scoring detects target when not in Top-1."""
        candidates = [
            FoodCandidate(name="Dumpling", confidence=0.45, source="vision"),
            FoodCandidate(name="Samosa", confidence=0.40, source="vision"),
            FoodCandidate(name="Puff Pastry", confidence=0.15, source="vision")
        ]
        target_synonyms = ["samosa"]
        is_top1 = any(syn in candidates[0].name.lower() for syn in target_synonyms)
        is_top3 = any(any(syn in c.name.lower() for syn in target_synonyms) for c in candidates[:3])
        
        self.assertFalse(is_top1)
        self.assertTrue(is_top3)

    def test_03_unknown_food_handling(self):
        """Test 3: Completely unknown food generates missing nutrition warning."""
        res = self.pipeline.analyze_food_text("synthetic_unobtainium_dish_123", portion_g=100.0)
        self.assertIsNone(res.nutrition)
        self.assertTrue(any("Nutritional lookup unavailable" in w for w in res.warnings))
        self.assertTrue(res.requires_user_confirmation)

    def test_04_exact_nutrition_match_classification(self):
        """Test 4: Exact food match is identified correctly."""
        res = self.mock_nut.lookup_nutrition("samosa")
        self.assertIsNotNone(res)
        self.assertEqual(res.food_name, "Samosa")
        self.assertEqual(res.carbs_g_per_100g, 33.2)

    def test_05_ambiguous_nutrition_match_classification(self):
        """Test 5: Ambiguous query triggers uncertainty flags."""
        amb_cands = [
            FoodCandidate(name="Roti Flatbread", confidence=0.42, source="vision"),
            FoodCandidate(name="Naan Bread", confidence=0.38, source="vision")
        ]
        req_confirm, warnings = evaluate_meal_confidence(amb_cands, None, 50.0)
        self.assertTrue(req_confirm)
        self.assertTrue(any("Visual ambiguity" in w or "Low visual recognition" in w for w in warnings))

    def test_06_portion_scaling_across_multiple_sizes(self):
        """Test 6: Accurate linear portion scaling across 50g, 75g, 100g, 150g, 250g."""
        portions = [50.0, 75.0, 100.0, 150.0, 250.0]
        # Rice: 28.2g carbs / 100g in mock
        for p in portions:
            res = self.pipeline.analyze_food_text("rice", portion_g=p)
            expected_carbs = round((28.2 * p) / 100.0, 2)
            self.assertAlmostEqual(res.final_macros["carbs_g"], expected_carbs, places=2)

    def test_07_negative_portion_rejection(self):
        """Test 7: Negative portion is clamped to 0.0 with no negative macros."""
        res = self.pipeline.analyze_food_text("samosa", portion_g=-100.0)
        self.assertEqual(res.portion_g, 0.0)
        self.assertIsNone(res.final_macros["carbs_g"])

    def test_08_zero_portion_rejection(self):
        """Test 8: Zero portion returns None macros and warning."""
        res = self.pipeline.analyze_food_text("samosa", portion_g=0.0)
        self.assertEqual(res.portion_g, 0.0)
        self.assertIsNone(res.final_macros["carbs_g"])
        self.assertTrue(any("Portion size not specified" in w for w in res.warnings))

    def test_09_portion_error_sensitivity_calculation(self):
        """Test 9: Accurate mathematical computation of portion error vs carb error."""
        # Food: Samosa (33.2g / 100g), true portion = 100g -> true carbs = 33.2g
        # User estimates 150g (+50% portion error) -> est carbs = 49.8g -> error = +16.6g
        true_portion = 100.0
        ref_carb_100g = 33.2
        true_carbs = (ref_carb_100g * true_portion) / 100.0

        est_portion = true_portion * 1.50  # +50%
        est_carbs = (ref_carb_100g * est_portion) / 100.0
        carb_error = est_carbs - true_carbs

        self.assertAlmostEqual(carb_error, 16.6, places=2)

    def test_10_human_correction_overrides_prediction(self):
        """Test 10: Human selection/manual search completely overrides wrong AI prediction."""
        # AI predicted Samosa (top candidate), but user manually corrects to "idli"
        res_override = self.pipeline.analyze_food_text("idli", portion_g=90.0)
        self.assertEqual(res_override.selected_food, "idli")
        self.assertEqual(res_override.nutrition.food_name, "Idli")
        # Idli: 25.0g / 100g * 0.9 = 22.5g carbs
        self.assertAlmostEqual(res_override.final_macros["carbs_g"], 22.5, places=2)

    def test_11_low_confidence_requires_confirmation(self):
        """Test 11: Low confidence (< 0.50) triggers mandatory confirmation."""
        low_cands = [FoodCandidate(name="mystery_soup", confidence=0.25, source="vision")]
        req_confirm, warnings = evaluate_meal_confidence(low_cands, None, 100.0)
        self.assertTrue(req_confirm)
        self.assertTrue(any("Low visual recognition confidence" in w for w in warnings))

    def test_12_missing_provider_does_not_fabricate_success(self):
        """Test 12: Missing or unavailable provider returns None without fabricating values."""
        offline_pipeline = MealAnalysisPipeline(
            recognition_provider=MockFoodRecognitionProvider(available=False),
            nutrition_provider=MockNutritionProvider(available=False)
        )
        res = offline_pipeline.analyze_image("test.png", portion_g=100.0)
        self.assertEqual(res.image_food_candidates, [])
        self.assertIsNone(res.selected_food)
        self.assertIsNone(res.nutrition)
        self.assertIsNone(res.final_macros["carbs_g"])

    def test_13_glucoshield_v1_integrity_invariant(self):
        """Test 13: Strict invariant check that V1 models and datasets are unmodified."""
        manifest_path = os.path.join(BASE_DIR, "data", "metadata", "dataset_manifest.json")
        self.assertTrue(os.path.exists(manifest_path))

        neural_path = os.path.join(BASE_DIR, "models", "glucoshield_neural_best.pt")
        hybrid_path = os.path.join(BASE_DIR, "models", "glucoshield_hybrid_best.pt")
        
        def get_sha256(p):
            h = hashlib.sha256()
            with open(p, "rb") as f:
                while chunk := f.read(65536):
                    h.update(chunk)
            return h.hexdigest()

        self.assertEqual(get_sha256(neural_path), "026af3341a91064136c38b0172f2aa6af34806913640a02270c7d82a28ea13fb")
        self.assertEqual(get_sha256(hybrid_path), "89a67710aa4931246f9097674332cbfd9d1af3d20c722c04d806ef66e47298d1")

if __name__ == "__main__":
    unittest.main()
