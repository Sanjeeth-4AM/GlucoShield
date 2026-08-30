"""
GlucoShield Free Food Vision & Nutrition Pipeline Demo
======================================================
CLI interactive tool to demonstrate the 3-stage Food Recognition & Nutrition Lookup:
  1. Food Recognition from Image (or manual text entry)
  2. Nutrient Density Lookup (USDA FoodData Central / Open Food Facts / Mock)
  3. Portion Scaling (Grams) -> Final Carbohydrates, Protein, Fat, Calories
  4. Clinical Safety & Uncertainty Policy

Usage:
  # Manual food search mode (no image required):
  python food_vision/demo_free_food_pipeline.py --food "samosa" --portion-g 120 --provider usda
  python food_vision/demo_free_food_pipeline.py --food "idli" --portion-g 100 --provider openfoodfacts

  # Image recognition mode:
  python food_vision/demo_free_food_pipeline.py --image meal.jpg --portion-g 150

  # Offline deterministic mock demo:
  python food_vision/demo_free_food_pipeline.py --mock
"""

import sys
import os
import argparse
import json

# Ensure project root is in path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from food_vision.pipeline.meal_analysis_pipeline import MealAnalysisPipeline
from food_vision.providers.usda_nutrition_provider import USDANutritionProvider
from food_vision.providers.openfoodfacts_provider import OpenFoodFactsProvider
from food_vision.providers.huggingface_food_provider import HuggingFaceFoodRecognitionProvider
from food_vision.providers.mock_provider import MockFoodRecognitionProvider, MockNutritionProvider

def run_demo():
    parser = argparse.ArgumentParser(description="GlucoShield Free Food Vision & Nutrition Pipeline Demo")
    parser.add_argument("--image", type=str, default=None, help="Path to meal image file")
    parser.add_argument("--food", type=str, default=None, help="Manual food name query (e.g., samosa, idli, rice)")
    parser.add_argument("--portion-g", type=float, default=100.0, help="Portion weight in grams (default 100g)")
    parser.add_argument("--provider", type=str, choices=["usda", "openfoodfacts", "mock"], default="usda", help="Nutrition lookup provider")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode without network calls")
    args = parser.parse_args()

    print("=" * 80)
    print("GLUCOSHIELD — MODULAR FOOD RECOGNITION & NUTRITION LOOKUP DEMO")
    print("=" * 80)

    # 1. Setup Providers
    if args.mock:
        rec_prov = MockFoodRecognitionProvider()
        nut_prov = MockNutritionProvider()
        print("Provider Mode: [OFFLINE MOCK SERVICE]")
    else:
        rec_prov = HuggingFaceFoodRecognitionProvider()
        if args.provider == "openfoodfacts":
            nut_prov = OpenFoodFactsProvider()
        else:
            nut_prov = USDANutritionProvider()
        print(f"Recognition Provider: [{rec_prov.provider_name}]")
        print(f"Nutrition Provider:   [{nut_prov.provider_name}]")

    pipeline = MealAnalysisPipeline(
        recognition_provider=rec_prov,
        nutrition_provider=nut_prov
    )

    # 2. Execute Analysis
    if args.image:
        print(f"\nAnalyzing Image: '{args.image}' (Portion: {args.portion_g}g)...")
        result = pipeline.analyze_image(args.image, portion_g=args.portion_g)
    elif args.food:
        print(f"\nQuerying Food Item: '{args.food}' (Portion: {args.portion_g}g)...")
        result = pipeline.analyze_food_text(args.food, portion_g=args.portion_g)
    else:
        # Default demo query
        print("\nNo image or food specified. Running default demo query: 'samosa' (120g)...")
        result = pipeline.analyze_food_text("samosa", portion_g=120.0)

    # 3. Print Structured Results
    print("\n" + "-" * 80)
    print("STAGE 1: RECOGNIZED FOOD CANDIDATES")
    print("-" * 80)
    if result.image_food_candidates:
        for idx, cand in enumerate(result.image_food_candidates):
            print(f"  [{idx + 1}] {cand.name:<30} | Confidence: {cand.confidence * 100:>5.1f}% | Source: {cand.source}")
    else:
        print("  (No candidate labels returned)")

    print("\n" + "-" * 80)
    print(f"STAGE 2: NUTRITIONAL DENSITY FOR: '{result.selected_food}'")
    print("-" * 80)
    if result.nutrition:
        n = result.nutrition
        print(f"  Reference Match:    {n.food_name}")
        print(f"  Database Source:    {n.source}")
        print(f"  Carbohydrates:      {n.carbs_g_per_100g} g / 100g")
        print(f"  Protein:            {n.protein_g_per_100g} g / 100g")
        print(f"  Total Fat:          {n.fat_g_per_100g} g / 100g")
        print(f"  Total Energy:       {n.calories_kcal_per_100g} kcal / 100g")
    else:
        print("  [Lookup Unavailable / Not Found in Database]")

    print("\n" + "-" * 80)
    print(f"STAGE 3: SCALED MACRONUTRIENTS (PORTION: {result.portion_g:.1f}g)")
    print("-" * 80)
    macros = result.final_macros
    print(f"  * Estimated Carbohydrates:  {macros.get('carbs_g')} g")
    print(f"  * Estimated Protein:        {macros.get('protein_g')} g")
    print(f"  * Estimated Total Fat:      {macros.get('fat_g')} g")
    print(f"  * Estimated Total Calories: {macros.get('calories_kcal')} kcal")

    print("\n" + "-" * 80)
    print("STAGE 4: CLINICAL SAFETY & HUMAN CONFIRMATION POLICY")
    print("-" * 80)
    print(f"  Mandatory Human Confirmation Required: {result.requires_user_confirmation}")
    if result.warnings:
        print("  Clinical Warnings & Uncertainty Flags:")
        for w in result.warnings:
            print(f"    - {w}")

    print("\n" + "=" * 80)
    print("GLUCOSHIELD DEMO EXECUTION COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    run_demo()
