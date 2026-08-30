"""
GlucoShield Food Vision Confidence & Safety Policy
==================================================
Applies clinical safety rules to meal image predictions:
  - Low confidence detection (< 0.60)
  - Ambiguous candidate detection (|top1 - top2| < 0.15)
  - Portion sanity bounds (0g < portion <= 1500g)
  - Mandatory human confirmation enforcement
"""

from typing import List, Tuple, Optional
from food_vision.schemas import FoodCandidate, NutritionResult

CONFIDENCE_THRESHOLD_HIGH = 0.75
CONFIDENCE_THRESHOLD_LOW = 0.50
AMBIGUITY_DELTA = 0.15

def evaluate_meal_confidence(
    candidates: List[FoodCandidate],
    nutrition: Optional[NutritionResult],
    portion_g: Optional[float]
) -> Tuple[bool, List[str]]:
    """
    Evaluates prediction uncertainty and generates clinical warnings.
    
    Returns:
      (requires_user_confirmation: bool, warnings: List[str])
    """
    warnings = []
    requires_confirmation = True  # In healthcare, human-in-the-loop is ALWAYS default

    # 1. Check Image Recognition Quality
    if not candidates:
        warnings.append("No food items recognized in photograph. Manual entry required.")
        return True, warnings

    top_candidate = candidates[0]
    
    if top_candidate.confidence < CONFIDENCE_THRESHOLD_LOW:
        warnings.append(
            f"Low visual recognition confidence ({top_candidate.confidence*100:.1f}% for '{top_candidate.name}'). "
            "Please confirm or select the correct item."
        )
    elif len(candidates) > 1:
        second_cand = candidates[1]
        if (top_candidate.confidence - second_cand.confidence) < AMBIGUITY_DELTA:
            warnings.append(
                f"Visual ambiguity detected between '{top_candidate.name}' and '{second_cand.name}'. "
                "Please verify the dish selection."
            )

    # 2. Check Nutritional Lookup Quality
    if nutrition is None:
        warnings.append(
            f"Nutritional lookup unavailable for '{top_candidate.name}'. "
            "Please enter carbohydrate grams manually."
        )
    elif nutrition.carbs_g_per_100g is None:
        warnings.append(
            f"Carbohydrate density unlisted for '{nutrition.food_name}'. "
            "Manual carbohydrate estimation recommended."
        )

    # 3. Check Portion Sanity Bounds
    if portion_g is None or portion_g <= 0.0:
        warnings.append("Portion size not specified (default 100g assumed). Please specify meal portion.")
    elif portion_g > 1500.0:
        warnings.append(f"Extreme meal portion specified ({portion_g}g). Please verify serving size.")

    # 4. Mandatory Clinical Disclaimer
    warnings.append("Advisory estimate only. Photo recognition cannot measure hidden oils, sugars, or exact recipe ratios.")

    return requires_confirmation, warnings
