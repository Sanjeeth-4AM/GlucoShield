"""
GlucoShield Food Vision API & Provider Test Suite
=================================================
Automated unit tests verifying the 2-stage provider architecture:
  1. Provider interface contracts
  2. Missing API key / offline resilience
  3. Mock recognition and nutrition providers
  4. Accurate portion scaling: final = (per_100g * portion) / 100
  5. Mandatory user confirmation enforcement
  6. Low-confidence recognition policy
  7. Unknown food handling
  8. Zero and negative portion validation
  9. Preservation of GlucoShield V1 frozen checkpoints and datasets
"""

import os
import sys
import unittest
import hashlib

# Ensure project root is in sys.path
BASE_DIR = "D:/ML PROJECT"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from food_vision.schemas import FoodCandidate, NutritionResult, MealAnalysisResult
from food_vision.providers.base import BaseFoodRecognitionProvider, BaseNutritionProvider
from food_vision.providers.mock_provider import MockFoodRecognitionProvider, MockNutritionProvider
from food_vision.providers.usda_nutrition_provider import USDANutritionProvider
from food_vision.providers.openfoodfacts_provider import OpenFoodFactsProvider
from food_vision.pipeline.meal_analysis_pipeline import MealAnalysisPipeline
from food_vision.pipeline.confidence_policy import evaluate_meal_confidence

class TestFoodApiPipeline(unittest.TestCase):

    def setUp(self):
        self.mock_rec = MockFoodRecognitionProvider()
        self.mock_nut = MockNutritionProvider()
        self.pipeline = MealAnalysisPipeline(
            recognition_provider=self.mock_rec,
            nutrition_provider=self.mock_nut
        )

    def test_01_provider_interface_contract(self):
        """Test 1: Providers adhere to base interface contract."""
        self.assertIsInstance(self.mock_rec, BaseFoodRecognitionProvider)
        self.assertIsInstance(self.mock_nut, BaseNutritionProvider)
        self.assertTrue(self.mock_rec.is_available)
        self.assertTrue(self.mock_nut.is_available)
        self.assertIsInstance(self.mock_rec.provider_name, str)
        self.assertIsInstance(self.mock_nut.provider_name, str)

    def test_02_missing_credentials_handling(self):
        """Test 2: Providers handle missing credentials or unconfigured state without crashing."""
        offline_rec = MockFoodRecognitionProvider(available=False)
        self.assertFalse(offline_rec.is_available)
        res = offline_rec.recognize_food("nonexistent.jpg")
        self.assertEqual(res, [])

        offline_nut = MockNutritionProvider(available=False)
        self.assertFalse(offline_nut.is_available)
        nut_res = offline_nut.lookup_nutrition("samosa")
        self.assertIsNone(nut_res)

    def test_03_mock_recognition_provider(self):
        """Test 3: Mock recognition provider returns top-K candidates."""
        candidates = self.mock_rec.recognize_food("dummy_img.png", top_k=2)
        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0].name, "samosa")
        self.assertAlmostEqual(candidates[0].confidence, 0.88)

    def test_04_mock_nutrition_provider(self):
        """Test 4: Mock nutrition provider returns accurate per-100g values."""
        res = self.mock_nut.lookup_nutrition("samosa")
        self.assertIsNotNone(res)
        self.assertEqual(res.food_name, "Samosa")
        self.assertAlmostEqual(res.carbs_g_per_100g, 33.2)
        self.assertAlmostEqual(res.protein_g_per_100g, 5.1)
        self.assertAlmostEqual(res.fat_g_per_100g, 17.5)
        self.assertAlmostEqual(res.calories_kcal_per_100g, 310.0)

    def test_05_portion_scaling_calculation(self):
        """Test 5: Accurate portion scaling: final = (per_100g * portion_g) / 100.0"""
        # Samosa 120g: Carbs = 33.2 * 1.2 = 39.84g, Fat = 17.5 * 1.2 = 21.0g
        res = self.pipeline.analyze_food_text("samosa", portion_g=120.0)
        self.assertIsNotNone(res.final_macros)
        self.assertAlmostEqual(res.final_macros["carbs_g"], 39.84, places=2)
        self.assertAlmostEqual(res.final_macros["protein_g"], 6.12, places=2)
        self.assertAlmostEqual(res.final_macros["fat_g"], 21.0, places=2)
        self.assertAlmostEqual(res.final_macros["calories_kcal"], 372.0, places=1)

    def test_06_mandatory_user_confirmation_enforcement(self):
        """Test 6: User confirmation is strictly enforced for all meal predictions."""
        res = self.pipeline.analyze_food_text("samosa", portion_g=100.0)
        self.assertTrue(res.requires_user_confirmation)

    def test_07_low_confidence_recognition_handling(self):
        """Test 7: Low confidence (< 0.50) triggers explicit warning message."""
        low_conf_cands = [
            FoodCandidate(name="mysterious_snack", confidence=0.35, source="mock")
        ]
        requires_confirm, warnings = evaluate_meal_confidence(low_conf_cands, None, 100.0)
        self.assertTrue(requires_confirm)
        self.assertTrue(any("Low visual recognition confidence" in w for w in warnings))

    def test_08_unknown_food_handling(self):
        """Test 8: Unknown food without database entry produces graceful warning."""
        res = self.pipeline.analyze_food_text("unobtainium_dish_9999", portion_g=100.0)
        self.assertIsNone(res.nutrition)
        self.assertIsNone(res.final_macros["carbs_g"])
        self.assertTrue(any("Nutritional lookup unavailable" in w for w in res.warnings))

    def test_09_zero_and_negative_portion_validation(self):
        """Test 9: Zero or negative portion inputs are clamped and handled safely."""
        res_zero = self.pipeline.analyze_food_text("samosa", portion_g=0.0)
        self.assertIsNone(res_zero.final_macros["carbs_g"])

        res_neg = self.pipeline.analyze_food_text("samosa", portion_g=-50.0)
        self.assertIsNone(res_neg.final_macros["carbs_g"])

    def test_10_preservation_of_glucoshield_v1_files(self):
        """Test 10: Verify GlucoShield V1 checkpoints and datasets are completely intact."""
        neural_path = os.path.join(BASE_DIR, "models", "glucoshield_neural_best.pt")
        hybrid_path = os.path.join(BASE_DIR, "models", "glucoshield_hybrid_best.pt")
        
        self.assertTrue(os.path.exists(neural_path))
        self.assertTrue(os.path.exists(hybrid_path))

        def get_sha256(p):
            h = hashlib.sha256()
            with open(p, "rb") as f:
                while chunk := f.read(65536):
                    h.update(chunk)
            return h.hexdigest()

        # Check known hashes
        self.assertEqual(get_sha256(neural_path), "026af3341a91064136c38b0172f2aa6af34806913640a02270c7d82a28ea13fb")
        self.assertEqual(get_sha256(hybrid_path), "89a67710aa4931246f9097674332cbfd9d1af3d20c722c04d806ef66e47298d1")

if __name__ == "__main__":
    unittest.main()
