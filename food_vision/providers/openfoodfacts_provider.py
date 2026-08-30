"""
GlucoShield Open Food Facts Provider
====================================
Queries the open, free Open Food Facts worldwide database for nutritional density.
Requires no API keys or paid accounts.
"""

import json
import urllib.request
import urllib.parse
from typing import Optional
from food_vision.providers.base import BaseNutritionProvider
from food_vision.schemas import NutritionResult

class OpenFoodFactsProvider(BaseNutritionProvider):
    """
    Queries Open Food Facts (world.openfoodfacts.org).
    100% Free and Open Access.
    """
    def __init__(self, timeout: int = 8):
        self.timeout = timeout
        self.base_url = "https://world.openfoodfacts.org/cgi/search.pl"

    @property
    def provider_name(self) -> str:
        return "open_food_facts"

    @property
    def is_available(self) -> bool:
        return True

    def lookup_nutrition(self, food_name: str) -> Optional[NutritionResult]:
        if not food_name:
            return None

        query_clean = food_name.strip()
        params = {
            "search_terms": query_clean,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": 2
        }
        url = f"{self.base_url}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "GlucoShield-OpenResearch/1.0 (sanjeev@glucoshield.local)"}
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status != 200:
                    return None
                data = json.loads(resp.read().decode("utf-8"))
                products = data.get("products", [])
                if not products:
                    return None

                top_p = products[0]
                p_name = top_p.get("product_name") or food_name
                nutriments = top_p.get("nutriments", {})

                carbs = nutriments.get("carbohydrates_100g")
                protein = nutriments.get("proteins_100g")
                fat = nutriments.get("fat_100g")
                calories = nutriments.get("energy-kcal_100g") or (
                    nutriments.get("energy_100g") / 4.184 if nutriments.get("energy_100g") else None
                )

                if carbs is None and protein is None and fat is None:
                    return None

                return NutritionResult(
                    food_name=p_name,
                    carbs_g_per_100g=float(carbs) if carbs is not None else None,
                    protein_g_per_100g=float(protein) if protein is not None else None,
                    fat_g_per_100g=float(fat) if fat is not None else None,
                    calories_kcal_per_100g=float(calories) if calories is not None else None,
                    serving_description="100g standard portion",
                    source="Open Food Facts (world.openfoodfacts.org)",
                    confidence=0.80,
                    warnings=["Community crowdsourced nutrient data (subject to packaging variance)"]
                )

        except Exception:
            return None
