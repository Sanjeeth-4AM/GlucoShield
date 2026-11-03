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

    def test_11_usda_composite_thali_lookup(self):
        """Test 11: USDA provider correctly resolves composite thali with honest macronutrients instead of single sauce."""
        usda = USDANutritionProvider()
        res = usda.lookup_nutrition("South Indian thali")
        self.assertIsNotNone(res)
        self.assertIn("Thali", res.food_name)
        self.assertAlmostEqual(res.carbs_g_per_100g, 18.5, places=1)
        self.assertAlmostEqual(res.protein_g_per_100g, 3.8, places=1)
        self.assertAlmostEqual(res.fat_g_per_100g, 2.8, places=1)

        # Portion scaling for 250g composite meal: 18.5 * 2.5 = 46.25g carbs (not 20g curry sauce!)
        pipeline = MealAnalysisPipeline(recognition_provider=self.mock_rec, nutrition_provider=usda)
        analysis = pipeline.analyze_food_text("South Indian thali", portion_g=250.0)
        self.assertIsNotNone(analysis.final_macros)
        self.assertAlmostEqual(analysis.final_macros["carbs_g"], 46.25, places=2)
        self.assertAlmostEqual(analysis.final_macros["protein_g"], 9.5, places=2)
        self.assertAlmostEqual(analysis.final_macros["fat_g"], 7.0, places=2)

    def test_12_candidate_selection_dispatch(self):
        """Test 12: Pipeline respects selected_candidate_index when analyzing recognition candidates."""
        # Mock recognition returns: [0: "samosa", 1: "spring_roll", 2: "dumpling"]
        analysis = self.pipeline.analyze_image("dummy_img.png", portion_g=200.0, selected_candidate_index=1)
        self.assertEqual(analysis.selected_food, "spring_roll")
        self.assertEqual(analysis.portion_g, 200.0)
        self.assertTrue(analysis.requires_user_confirmation)

    def test_13_complex_composite_thali_multi_ingredient_query(self):
        """Test 13: Full multi-item South Indian thali query matches composite dish, NOT single rice/dal."""
        usda = USDANutritionProvider()
        query = "South Indian thali with white rice, dal, potato curry, leafy greens, yogurt and papad"
        res = usda.lookup_nutrition(query)
        self.assertIsNotNone(res)
        self.assertIn("South Indian Thali", res.food_name)
        self.assertAlmostEqual(res.carbs_g_per_100g, 18.5, places=1)
        self.assertEqual(res.source, "Generic Composite Dish Estimate (Literature Population Average; Unverified Exact Plate)")
        self.assertEqual(res.confidence, 0.70)
        self.assertTrue(any("composite platter estimate" in w.lower() for w in res.warnings))

    def test_14_multi_item_query_matching_single_component_warning(self):
        """Test 14: Multi-item query matching only a single non-composite ingredient triggers explicit warning."""
        usda = USDANutritionProvider()
        query = "white rice with exotic unlisted sauce"
        res = usda._lookup_offline_fallback(query)
        self.assertIsNotNone(res)
        self.assertEqual(res.food_name, "Rice, white, cooked")
        self.assertTrue(any("Matched single component" in w for w in res.warnings))

    def test_15_manual_text_query_candidate_confidence_provenance(self):
        """Test 15: Manual text query sets candidate confidence to None rather than fabricating 1.0 (100%)."""
        analysis = self.pipeline.analyze_food_text("South Indian thali", portion_g=250.0)
        self.assertTrue(len(analysis.image_food_candidates) > 0)
        cand = analysis.image_food_candidates[0]
        self.assertIsNone(cand.confidence, "Manual text entry candidate confidence must be None, not 1.0")
        self.assertEqual(cand.source, "manual_user_entry")
        self.assertIsNone(cand.to_dict()["confidence"])
        self.assertTrue(analysis.requires_user_confirmation)

    def test_16_huggingface_provider_unconfigured_token_error_tracking(self):
        """Test 16: HuggingFace provider reports is_available=False and sets last_error when token is missing."""
        from food_vision.providers.huggingface_food_provider import HuggingFaceFoodRecognitionProvider
        hf_provider = HuggingFaceFoodRecognitionProvider(api_token="")
        self.assertFalse(hf_provider.is_available)
        candidates = hf_provider.recognize_food(b"\x89PNG\r\n\x1a\nfake_image_bytes")
        self.assertEqual(candidates, [])
        self.assertIsNotNone(hf_provider.last_error)
        self.assertIn("HUGGINGFACE_API_TOKEN is not configured", hf_provider.last_error)

    def test_17_meal_pipeline_surfaces_recognition_error_in_warnings(self):
        """Test 17: MealAnalysisPipeline propagates recognition_error honestly into warnings."""
        from food_vision.providers.huggingface_food_provider import HuggingFaceFoodRecognitionProvider
        hf_provider = HuggingFaceFoodRecognitionProvider(api_token="")
        pipeline = MealAnalysisPipeline(recognition_provider=hf_provider, nutrition_provider=self.mock_nut)
        result = pipeline.analyze_image(b"\x89PNG\r\n\x1a\nfake_image_bytes", portion_g=250.0)
        self.assertEqual(result.image_food_candidates, [])
        self.assertIsNone(result.selected_food)
        self.assertTrue(any("Visual classification unavailable" in w for w in result.warnings))
        self.assertTrue(any("HUGGINGFACE_API_TOKEN is not configured" in w for w in result.warnings))

    def test_18_image_only_analysis_with_recognized_pizza_candidate(self):
        """Test 18: Genuine visual recognition of pizza resolves USDA nutrition without text query."""
        pizza_cand = [FoodCandidate(name="pizza", confidence=0.892, source="HuggingFace (nateraw/food)", raw_label="pizza")]
        rec_provider = MockFoodRecognitionProvider(canned_candidates=pizza_cand)
        pipeline = MealAnalysisPipeline(recognition_provider=rec_provider, nutrition_provider=self.mock_nut)
        
        # Call image-only analysis without any text query
        result = pipeline.analyze_image(b"fake_pizza_bytes", portion_g=200.0)
        self.assertEqual(len(result.image_food_candidates), 1)
        self.assertEqual(result.selected_food, "pizza")
        self.assertAlmostEqual(result.image_food_candidates[0].confidence, 0.892)
        self.assertIsNotNone(result.nutrition)
        # Mock database pizza: 32.0g carbs per 100g -> for 200g: 64.0g carbs
        self.assertAlmostEqual(result.final_macros["carbs_g"], 64.0, places=1)
        self.assertTrue(result.requires_user_confirmation)

    def test_19_pizza_in_food101_and_usda_mapping(self):
        """Test 19: Pizza maps to nutritional density in USDA provider and scales accurately."""
        usda = USDANutritionProvider()
        res = usda.lookup_nutrition("pizza")
        self.assertIsNotNone(res)
        self.assertIn("pizza", res.food_name.lower())
        self.assertIsNotNone(res.carbs_g_per_100g)
        self.assertTrue(res.carbs_g_per_100g > 0.0)

    def test_20_large_image_preprocessing_and_bounded_payload_size(self):
        """Test 20: Large image is proportionally resized to <= 1024px with bounded payload."""
        from PIL import Image
        import io
        from food_vision.image_preprocessing import preprocess_meal_image

        # 3840x2160 4K image
        img = Image.new("RGB", (3840, 2160), color=(180, 90, 45))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=95)
        raw_4k_bytes = buf.getvalue()
        self.assertTrue(len(raw_4k_bytes) > 100000)

        processed_bytes, meta = preprocess_meal_image(raw_4k_bytes)
        self.assertEqual(meta["processed_format"], "JPEG")
        self.assertLessEqual(meta["processed_dimensions"][0], 1024)
        self.assertLessEqual(meta["processed_dimensions"][1], 1024)
        # 3840/2160 = 16:9 -> 1024x576
        self.assertEqual(meta["processed_dimensions"], (1024, 576))
        self.assertTrue(meta["resized"])
        self.assertLess(meta["processed_bytes"], 2 * 1024 * 1024)

    def test_21_proportional_resizing_and_rgb_preservation(self):
        """Test 21: Non-RGB images with transparency are composited to RGB and preserve aspect ratio."""
        from PIL import Image
        import io
        from food_vision.image_preprocessing import preprocess_meal_image

        # 2000x1000 (2:1 aspect ratio) RGBA with alpha channel
        rgba_img = Image.new("RGBA", (2000, 1000), color=(255, 128, 0, 128))
        buf = io.BytesIO()
        rgba_img.save(buf, format="PNG")
        png_bytes = buf.getvalue()

        processed_bytes, meta = preprocess_meal_image(png_bytes)
        self.assertEqual(meta["original_format"], "PNG")
        self.assertEqual(meta["processed_format"], "JPEG")
        self.assertEqual(meta["processed_dimensions"], (1024, 512))

        # Re-open processed bytes and ensure it is valid RGB without alpha
        reopened = Image.open(io.BytesIO(processed_bytes))
        self.assertEqual(reopened.mode, "RGB")
        self.assertEqual(reopened.size, (1024, 512))

    def test_22_invalid_image_rejection(self):
        """Test 22: Corrupted or non-image bytes are rejected safely with clear diagnostic error."""
        from food_vision.image_preprocessing import preprocess_meal_image, ImagePreprocessingError
        from food_vision.providers.huggingface_food_provider import HuggingFaceFoodRecognitionProvider

        invalid_bytes = b"definitely_not_a_valid_image_stream_or_header"
        with self.assertRaises(ImagePreprocessingError):
            preprocess_meal_image(invalid_bytes)

        # Provider catches error gracefully and records last_error
        hf_provider = HuggingFaceFoodRecognitionProvider(api_token="valid_mock_token")
        candidates = hf_provider.recognize_food(invalid_bytes)
        self.assertEqual(candidates, [])
        self.assertIsNotNone(hf_provider.last_error)
        self.assertIn("Invalid or corrupted image format", hf_provider.last_error)

    def test_23_successful_image_only_inference_mocked_http(self):
        """Test 23: Successful image classification returns genuine candidates and records metadata."""
        import json
        import io
        from unittest.mock import patch, MagicMock
        from PIL import Image
        from food_vision.providers.huggingface_food_provider import HuggingFaceFoodRecognitionProvider

        img = Image.new("RGB", (1200, 900), color=(200, 50, 50))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        test_bytes = buf.getvalue()

        hf_provider = HuggingFaceFoodRecognitionProvider(api_token="test_token_123")
        mock_response_data = [
            {"label": "pizza", "score": 0.9412},
            {"label": "bruschetta", "score": 0.0321}
        ]
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps(mock_response_data).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
            candidates = hf_provider.recognize_food(test_bytes)
            self.assertEqual(len(candidates), 2)
            self.assertEqual(candidates[0].name, "Pizza")
            self.assertAlmostEqual(candidates[0].confidence, 0.9412)
            self.assertEqual(candidates[1].name, "Bruschetta")
            self.assertAlmostEqual(candidates[1].confidence, 0.0321)

            # Verify outgoing request headers
            req_arg = mock_urlopen.call_args[0][0]
            self.assertEqual(req_arg.headers.get("Content-type"), "image/jpeg")
            self.assertEqual(req_arg.headers.get("Authorization"), "Bearer test_token_123")
            # Verify processed payload size is bounded
            self.assertLess(len(req_arg.data), 2 * 1024 * 1024)

            # Verify metadata
            self.assertIsNotNone(hf_provider.last_image_meta)
            self.assertEqual(hf_provider.last_image_meta["original_dimensions"], (1200, 900))
            self.assertEqual(hf_provider.last_image_meta["processed_dimensions"], (1024, 768))

    def test_24_http_413_payload_too_large_provider_failure(self):
        """Test 24: HTTP 413 Payload Too Large reports honest provider error and prevents false claims."""
        import io
        import urllib.error
        from unittest.mock import patch
        from PIL import Image
        from food_vision.providers.huggingface_food_provider import HuggingFaceFoodRecognitionProvider

        img = Image.new("RGB", (500, 500), color=(100, 150, 200))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        test_bytes = buf.getvalue()

        hf_provider = HuggingFaceFoodRecognitionProvider(api_token="test_token_123")
        err_413 = urllib.error.HTTPError(
            url="https://router.huggingface.co/hf-inference/models/nateraw/food",
            code=413,
            msg="Payload Too Large",
            hdrs={},
            fp=io.BytesIO(b"Payload Too Large")
        )

        with patch("urllib.request.urlopen", side_effect=err_413):
            candidates = hf_provider.recognize_food(test_bytes)
            self.assertEqual(candidates, [])
            self.assertIsNotNone(hf_provider.last_error)
            self.assertIn("413 Payload Too Large", hf_provider.last_error)

            # End-to-end pipeline test
            pipeline = MealAnalysisPipeline(recognition_provider=hf_provider, nutrition_provider=self.mock_nut)
            result = pipeline.analyze_image(test_bytes, portion_g=250.0)
            self.assertEqual(result.image_food_candidates, [])
            self.assertIsNone(result.selected_food)
            self.assertTrue(any("413 Payload Too Large" in w for w in result.warnings))
            self.assertTrue(any("Image exceeds provider size limit" in w for w in result.warnings))

    def test_25_http_429_and_503_provider_failures(self):
        """Test 25: HTTP 429 rate limit and HTTP 503 model loading report honest diagnostic messages."""
        import io
        import urllib.error
        from unittest.mock import patch
        from PIL import Image
        from food_vision.providers.huggingface_food_provider import HuggingFaceFoodRecognitionProvider

        img = Image.new("RGB", (200, 200), color=(50, 50, 50))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        test_bytes = buf.getvalue()

        hf_provider = HuggingFaceFoodRecognitionProvider(api_token="test_token_123")

        # 429
        err_429 = urllib.error.HTTPError(url="", code=429, msg="Too Many Requests", hdrs={}, fp=io.BytesIO(b""))
        with patch("urllib.request.urlopen", side_effect=err_429):
            res = hf_provider.recognize_food(test_bytes)
            self.assertEqual(res, [])
            self.assertIn("rate limit exceeded", hf_provider.last_error)

        # 503
        err_503 = urllib.error.HTTPError(url="", code=503, msg="Service Unavailable", hdrs={}, fp=io.BytesIO(b""))
        with patch("urllib.request.urlopen", side_effect=err_503):
            res = hf_provider.recognize_food(test_bytes)
            self.assertEqual(res, [])
            self.assertIn("model is currently loading", hf_provider.last_error)

    def test_26_no_silent_text_fallback_on_visual_inference_failure(self):
        """Test 26: Image-only request failure does NOT trigger silent text fallback or synthetic classification."""
        from food_vision.providers.huggingface_food_provider import HuggingFaceFoodRecognitionProvider

        # Unconfigured or failed provider
        hf_provider = HuggingFaceFoodRecognitionProvider(api_token="")
        pipeline = MealAnalysisPipeline(recognition_provider=hf_provider, nutrition_provider=self.mock_nut)

        # Send image with no text query
        result = pipeline.analyze_image(b"\x89PNG\r\n\x1a\nfake_image", portion_g=200.0)
        self.assertEqual(result.image_food_candidates, [])
        self.assertIsNone(result.selected_food)
        self.assertIsNone(result.nutrition)
        self.assertIsNone(result.final_macros["carbs_g"])
        self.assertTrue(result.requires_user_confirmation)
        # Warnings must explain visual failure honestly, not claim unlisted or invent food
        self.assertTrue(any("Visual classification unavailable" in w for w in result.warnings))

    def test_27_local_food_provider_interface_and_unloaded_state(self):
        """Test 27: LocalFoodRecognitionProvider conforms to BaseFoodRecognitionProvider interface."""
        import io
        from PIL import Image
        from food_vision.providers.local_food_provider import LocalFoodRecognitionProvider

        prov = LocalFoodRecognitionProvider(model_dir="non_existent_dir_99999")
        self.assertIsInstance(prov, BaseFoodRecognitionProvider)
        self.assertFalse(prov.is_available)
        self.assertIn("Local Food-101 ViT", prov.provider_name)

        # Create valid 10x10 JPEG bytes
        img = Image.new("RGB", (10, 10), color=(100, 100, 100))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        valid_bytes = buf.getvalue()

        res = prov.recognize_food(valid_bytes)
        self.assertEqual(res, [])
        self.assertIsNotNone(prov.last_error)
        self.assertIn("not found", prov.last_error)

    def test_28_local_food_provider_invalid_image_handling(self):
        """Test 28: LocalFoodRecognitionProvider rejects corrupted bytes safely."""
        from food_vision.providers.local_food_provider import LocalFoodRecognitionProvider
        prov = LocalFoodRecognitionProvider()
        res = prov.recognize_food(b"not_an_image")
        self.assertEqual(res, [])
        self.assertIsNotNone(prov.last_error)
        self.assertIn("Invalid or corrupted image format", prov.last_error)

    def test_29_omelette_nutrition_lookup_not_shakshuka_sauce(self):
        """Test 29: Omelette maps to genuine whole egg omelet, rejecting branded simmer sauces."""
        usda = USDANutritionProvider()
        # Offline DB test
        offline_res = usda._lookup_offline_fallback("omelette")
        self.assertIsNotNone(offline_res)
        self.assertIn("Egg, whole, cooked, omelet", offline_res.food_name)
        self.assertGreater(offline_res.protein_g_per_100g, 8.0)
        self.assertGreater(offline_res.fat_g_per_100g, 8.0)
        self.assertLess(offline_res.carbs_g_per_100g, 3.0)

        # Candidate selection logic test: mock USDA response with sauce vs SR Legacy
        mock_foods = [
            {"description": "SHAKSHUKA OMELETTE SAUCE, SHAKSHUKA OMELETTE", "dataType": "Branded"},
            {"description": "SPINACH & MUSHROOM OMELETTE STARTER", "dataType": "Branded"},
            {"description": "Egg, whole, cooked, omelet", "dataType": "SR Legacy"}
        ]
        best_match = usda._select_best_food_match(mock_foods, "omelet")
        self.assertIsNotNone(best_match)
        self.assertEqual(best_match["description"], "Egg, whole, cooked, omelet")
        self.assertEqual(best_match["dataType"], "SR Legacy")

        # Portion scaling test for 150g omelette
        pipeline = MealAnalysisPipeline(recognition_provider=self.mock_rec, nutrition_provider=usda)
        res = pipeline.analyze_food_text("omelette", portion_g=150.0)
        self.assertIsNotNone(res.final_macros)
        self.assertGreater(res.final_macros["protein_g"], 12.0)
        self.assertGreater(res.final_macros["fat_g"], 14.0)
        self.assertLess(res.final_macros["carbs_g"], 5.0)

if __name__ == "__main__":
    unittest.main()

