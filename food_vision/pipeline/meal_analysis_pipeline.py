"""
GlucoShield Modular Meal Analysis Pipeline
==========================================
Coordinates Stage 1 (Food Recognition), Stage 2 (Nutrition Density Lookup),
and Stage 3 (Portion-Scaled Calculation & Clinical Safety Checks).
"""

from typing import Optional, Union, List
from food_vision.schemas import FoodCandidate, NutritionResult, MealAnalysisResult
from food_vision.providers.base import BaseFoodRecognitionProvider, BaseNutritionProvider
from food_vision.providers.usda_nutrition_provider import USDANutritionProvider
from food_vision.providers.huggingface_food_provider import HuggingFaceFoodRecognitionProvider
from food_vision.providers.local_food_provider import LocalFoodRecognitionProvider
from food_vision.pipeline.confidence_policy import evaluate_meal_confidence

class MealAnalysisPipeline:
    """
    End-to-end multi-stage meal analysis coordinator.
    """
    def __init__(
        self,
        recognition_provider: Optional[BaseFoodRecognitionProvider] = None,
        nutrition_provider: Optional[BaseNutritionProvider] = None
    ):
        if recognition_provider is not None:
            self.recognition_provider = recognition_provider
            self._custom_recognition_provider = True
        else:
            self._custom_recognition_provider = False
            local_prov = LocalFoodRecognitionProvider()
            if local_prov.is_available:
                self.recognition_provider = local_prov
            else:
                self.recognition_provider = HuggingFaceFoodRecognitionProvider()
        self.nutrition_provider = nutrition_provider or USDANutritionProvider()

    def analyze_image(
        self,
        image_input: Union[str, bytes],
        portion_g: float = 100.0,
        selected_candidate_index: int = 0
    ) -> MealAnalysisResult:
        """
        Full photo-to-macronutrient analysis pipeline.
        
        Args:
          image_input: Filepath or raw bytes of meal photograph
          portion_g: Weight of the meal in grams (defaults to 100g)
          selected_candidate_index: Candidate index to query for nutrition (default 0 = top match)
        """
        # Validate portion
        valid_portion = max(0.0, float(portion_g))

        # Stage 1: Recognize Food Candidates
        if not getattr(self, "_custom_recognition_provider", False):
            if not isinstance(self.recognition_provider, LocalFoodRecognitionProvider) or not getattr(self.recognition_provider, "is_available", False):
                local_prov = LocalFoodRecognitionProvider()
                if local_prov.is_available:
                    self.recognition_provider = local_prov

        candidates = self.recognition_provider.recognize_food(image_input, top_k=5)
        recognition_error = getattr(self.recognition_provider, "last_error", None)

        selected_food_name = None
        nutrition_res = None

        if candidates and 0 <= selected_candidate_index < len(candidates):
            selected_candidate = candidates[selected_candidate_index]
            selected_food_name = selected_candidate.name

            # Stage 2: Nutrition Lookup
            nutrition_res = self.nutrition_provider.lookup_nutrition(selected_food_name)

        # Stage 3: Calculate Final Macronutrients
        final_macros = self._calculate_final_macros(nutrition_res, valid_portion)

        # Stage 4: Apply Safety & Confidence Policy
        requires_confirm, warnings = evaluate_meal_confidence(
            candidates,
            nutrition_res,
            valid_portion,
            recognition_error=recognition_error
        )

        return MealAnalysisResult(
            image_food_candidates=candidates,
            selected_food=selected_food_name,
            nutrition=nutrition_res,
            portion_g=valid_portion,
            final_macros=final_macros,
            requires_user_confirmation=requires_confirm,
            warnings=warnings
        )

    def analyze_food_text(
        self,
        food_name: str,
        portion_g: float = 100.0
    ) -> MealAnalysisResult:
        """
        Direct manual search / text entry mode without image recognition.
        """
        valid_portion = max(0.0, float(portion_g))
        nutrition_res = self.nutrition_provider.lookup_nutrition(food_name)
        final_macros = self._calculate_final_macros(nutrition_res, valid_portion)

        synthetic_candidate = FoodCandidate(
            name=food_name,
            confidence=None,
            source="manual_user_entry",
            raw_label=food_name
        )

        requires_confirm, warnings = evaluate_meal_confidence([synthetic_candidate], nutrition_res, valid_portion)

        return MealAnalysisResult(
            image_food_candidates=[synthetic_candidate],
            selected_food=food_name,
            nutrition=nutrition_res,
            portion_g=valid_portion,
            final_macros=final_macros,
            requires_user_confirmation=requires_confirm,
            warnings=warnings
        )

    def _calculate_final_macros(
        self,
        nutrition: Optional[NutritionResult],
        portion_g: float
    ) -> dict:
        """Applies portion scaling: final = (per_100g * portion_g) / 100.0"""
        if not nutrition or portion_g <= 0.0:
            return {"carbs_g": None, "protein_g": None, "fat_g": None, "calories_kcal": None}

        scale = portion_g / 100.0

        def scale_val(val):
            return round(val * scale, 2) if val is not None else None

        return {
            "carbs_g": scale_val(nutrition.carbs_g_per_100g),
            "protein_g": scale_val(nutrition.protein_g_per_100g),
            "fat_g": scale_val(nutrition.fat_g_per_100g),
            "calories_kcal": scale_val(nutrition.calories_kcal_per_100g)
        }
