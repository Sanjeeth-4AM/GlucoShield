"""
GlucoShield Food Vision Providers Package
=========================================
"""

from food_vision.providers.base import BaseFoodRecognitionProvider, BaseNutritionProvider
from food_vision.providers.mock_provider import MockFoodRecognitionProvider, MockNutritionProvider
from food_vision.providers.usda_nutrition_provider import USDANutritionProvider
from food_vision.providers.openfoodfacts_provider import OpenFoodFactsProvider
from food_vision.providers.huggingface_food_provider import HuggingFaceFoodRecognitionProvider

__all__ = [
    "BaseFoodRecognitionProvider",
    "BaseNutritionProvider",
    "MockFoodRecognitionProvider",
    "MockNutritionProvider",
    "USDANutritionProvider",
    "OpenFoodFactsProvider",
    "HuggingFaceFoodRecognitionProvider"
]
