"""
GlucoShield Food Vision Schemas
===============================
Pydantic/Dataclass schemas defining standardized outputs for:
  - FoodCandidate (Image Recognition Stage 1)
  - NutritionResult (Nutrition Database Lookup Stage 2)
  - MealAnalysisResult (Final Human-In-The-Loop Synthesis Stage 3)
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class FoodCandidate:
    """A candidate food item recognized from an image."""
    name: str
    confidence: float
    source: str
    raw_label: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "confidence": round(float(self.confidence), 4),
            "source": self.source,
            "raw_label": self.raw_label
        }


@dataclass
class NutritionResult:
    """Nutritional density data for a recognized food item (per 100g or serving)."""
    food_name: str
    carbs_g_per_100g: Optional[float]
    protein_g_per_100g: Optional[float]
    fat_g_per_100g: Optional[float]
    calories_kcal_per_100g: Optional[float]
    source: str
    serving_description: Optional[str] = "100g"
    confidence: Optional[float] = 1.0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "food_name": self.food_name,
            "carbs_g_per_100g": round(self.carbs_g_per_100g, 2) if self.carbs_g_per_100g is not None else None,
            "protein_g_per_100g": round(self.protein_g_per_100g, 2) if self.protein_g_per_100g is not None else None,
            "fat_g_per_100g": round(self.fat_g_per_100g, 2) if self.fat_g_per_100g is not None else None,
            "calories_kcal_per_100g": round(self.calories_kcal_per_100g, 1) if self.calories_kcal_per_100g is not None else None,
            "serving_description": self.serving_description,
            "source": self.source,
            "confidence": self.confidence,
            "warnings": self.warnings
        }


@dataclass
class MealAnalysisResult:
    """
    End-to-end meal analysis outcome combining image recognition candidates,
    selected item nutrition density, confirmed portion size, and final calculated macros.
    """
    image_food_candidates: List[FoodCandidate] = field(default_factory=list)
    selected_food: Optional[str] = None
    nutrition: Optional[NutritionResult] = None
    portion_g: Optional[float] = None
    final_macros: Dict[str, Optional[float]] = field(default_factory=lambda: {
        "carbs_g": None,
        "protein_g": None,
        "fat_g": None,
        "calories_kcal": None
    })
    requires_user_confirmation: bool = True
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "image_food_candidates": [c.to_dict() for c in self.image_food_candidates],
            "selected_food": self.selected_food,
            "nutrition": self.nutrition.to_dict() if self.nutrition else None,
            "portion_g": self.portion_g,
            "final_macros": {k: (round(v, 2) if v is not None else None) for k, v in self.final_macros.items()},
            "requires_user_confirmation": self.requires_user_confirmation,
            "warnings": self.warnings
        }
