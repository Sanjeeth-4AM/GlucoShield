"""
GlucoShield Mock Food & Nutrition Providers
===========================================
Deterministic mock providers for offline testing, CI/CD, and edge-case simulation.
"""

from typing import List, Optional, Union
from food_vision.providers.base import BaseFoodRecognitionProvider, BaseNutritionProvider
from food_vision.schemas import FoodCandidate, NutritionResult

class MockFoodRecognitionProvider(BaseFoodRecognitionProvider):
    """Deterministic food recognition provider for testing."""

    def __init__(
        self,
        canned_candidates: Optional[List[FoodCandidate]] = None,
        available: bool = True
    ):
        self._available = available
        self._canned = canned_candidates or [
            FoodCandidate(name="samosa", confidence=0.88, source="mock_vision", raw_label="indian_samosa_pastry"),
            FoodCandidate(name="spring_roll", confidence=0.08, source="mock_vision", raw_label="fried_spring_roll"),
            FoodCandidate(name="dumpling", confidence=0.04, source="mock_vision", raw_label="steamed_dumpling")
        ]

    @property
    def provider_name(self) -> str:
        return "mock_recognition_service"

    @property
    def is_available(self) -> bool:
        return self._available

    def recognize_food(
        self,
        image_input: Union[str, bytes],
        top_k: int = 5
    ) -> List[FoodCandidate]:
        if not self._available:
            return []
        return self._canned[:top_k]


class MockNutritionProvider(BaseNutritionProvider):
    """Deterministic nutrition lookup provider for testing."""

    def __init__(
        self,
        custom_database: Optional[dict] = None,
        available: bool = True
    ):
        self._available = available
        self._db = custom_database or {
            "samosa": {"carbs": 33.2, "protein": 5.1, "fat": 17.5, "calories": 310.0},
            "idli": {"carbs": 25.0, "protein": 6.4, "fat": 0.4, "calories": 128.0},
            "dosa": {"carbs": 30.8, "protein": 5.5, "fat": 4.3, "calories": 184.0},
            "rice": {"carbs": 28.2, "protein": 2.7, "fat": 0.3, "calories": 130.0},
            "banana": {"carbs": 22.8, "protein": 1.1, "fat": 0.3, "calories": 89.0},
            "pizza": {"carbs": 32.0, "protein": 11.0, "fat": 10.0, "calories": 266.0},
            "apple": {"carbs": 13.8, "protein": 0.3, "fat": 0.2, "calories": 52.0},
            "pasta": {"carbs": 30.9, "protein": 5.8, "fat": 0.9, "calories": 158.0},
            "bread": {"carbs": 49.4, "protein": 8.9, "fat": 3.3, "calories": 265.0},
            "salad": {"carbs": 3.3, "protein": 1.2, "fat": 0.2, "calories": 17.0}
        }

    @property
    def provider_name(self) -> str:
        return "mock_nutrition_database"

    @property
    def is_available(self) -> bool:
        return self._available

    def lookup_nutrition(
        self,
        food_name: str
    ) -> Optional[NutritionResult]:
        if not self._available or not food_name:
            return None

        clean_name = food_name.strip().lower()
        match = self._db.get(clean_name)
        if not match:
            # Fallback substring match
            for k, v in self._db.items():
                if k in clean_name or clean_name in k:
                    match = v
                    clean_name = k
                    break

        if not match:
            return None

        return NutritionResult(
            food_name=clean_name.capitalize(),
            carbs_g_per_100g=match["carbs"],
            protein_g_per_100g=match["protein"],
            fat_g_per_100g=match["fat"],
            calories_kcal_per_100g=match["calories"],
            serving_description="100g standard portion",
            source="mock_usda_reference",
            confidence=1.0,
            warnings=[]
        )
