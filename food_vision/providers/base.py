"""
GlucoShield Food Vision Base Provider Interfaces
================================================
Abstract base classes for food image recognition and nutrition database lookup.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Union
from food_vision.schemas import FoodCandidate, NutritionResult

class BaseFoodRecognitionProvider(ABC):
    """Abstract interface for image-based food recognition services."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if required credentials or models are loaded."""
        pass

    @abstractmethod
    def recognize_food(
        self,
        image_input: Union[str, bytes],
        top_k: int = 5
    ) -> List[FoodCandidate]:
        """
        Processes an image file path or raw image bytes and returns ranked food candidates.
        """
        pass


class BaseNutritionProvider(ABC):
    """Abstract interface for nutritional database lookup services."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        pass

    @abstractmethod
    def lookup_nutrition(
        self,
        food_name: str
    ) -> Optional[NutritionResult]:
        """
        Queries food name and returns per-100g nutritional content.
        """
        pass
