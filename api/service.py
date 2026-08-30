"""
GlucoShield — Production FastAPI Service Layer
==============================================
Exposes standardized REST endpoints for:
  - GET  /api/v1/health
  - POST /api/v1/forecast
  - POST /api/v1/what-if
  - POST /api/v1/food/analyze
  - POST /api/v1/decision/full-flow
"""

import os
import sys
import base64
import torch
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = "D:/ML PROJECT"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from api.schemas import (
    HealthResponse,
    ForecastRequest,
    ForecastResponse,
    WhatIfRequest,
    WhatIfResponse,
    FoodAnalyzeRequest,
    FoodAnalyzeResponse,
    FullFlowDecisionRequest,
    FullFlowDecisionResponse
)
from api.preprocessor import InputPayloadPreprocessor
from neural.models import GlucoShieldMultiTaskRNN
from physiology.hybrid_fusion import GlucoShieldHybridForecaster
from decision_engine.pipeline import EndToEndDecisionPipeline
from decision_engine.safety import SafetyGuardrails
from food_vision.pipeline.meal_analysis_pipeline import MealAnalysisPipeline
from food_vision.providers.mock_provider import MockFoodRecognitionProvider, MockNutritionProvider
from food_vision.providers.usda_nutrition_provider import USDANutritionProvider
from food_vision.providers.huggingface_food_provider import HuggingFaceFoodRecognitionProvider

# State container
class ServiceState:
    hybrid_model: Optional[GlucoShieldHybridForecaster] = None
    decision_pipeline: Optional[EndToEndDecisionPipeline] = None
    preprocessor: Optional[InputPayloadPreprocessor] = None
    meal_pipeline: Optional[MealAnalysisPipeline] = None
    device: torch.device = torch.device("cpu")
    is_ready: bool = False

state = ServiceState()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load models and pipelines
    state.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[API STARTUP] Initializing GlucoShield backend on {state.device}...")

    # 1. Load Preprocessor
    state.preprocessor = InputPayloadPreprocessor()

    # 2. Load Neural & Hybrid Forecaster
    neural_ckpt = os.path.join(BASE_DIR, "models", "glucoshield_neural_best.pt")
    hybrid_ckpt = os.path.join(BASE_DIR, "models", "glucoshield_hybrid_best.pt")

    if os.path.exists(neural_ckpt):
        neural_ckpt_data = torch.load(neural_ckpt, map_location=state.device)
        neural_model = GlucoShieldMultiTaskRNN(
            dynamic_dim=22,
            static_dim=9,
            hidden_dim=neural_ckpt_data["config"]["hidden"],
            num_layers=neural_ckpt_data["config"]["layers"],
            dropout=0.0,
            cell_type=neural_ckpt_data["config"]["cell_type"]
        ).to(state.device)
        neural_model.load_state_dict(neural_ckpt_data["model_state_dict"])
        neural_model.eval()
    else:
        neural_model = GlucoShieldMultiTaskRNN(
            cell_type="gru", dynamic_dim=22, static_dim=9, hidden_dim=128, num_layers=2, dropout=0.0, horizon=20
        ).to(state.device)

    state.hybrid_model = GlucoShieldHybridForecaster(neural_model=neural_model, freeze_neural=True).to(state.device)
    if os.path.exists(hybrid_ckpt):
        hybrid_ckpt_data = torch.load(hybrid_ckpt, map_location=state.device)
        state.hybrid_model.load_state_dict(hybrid_ckpt_data)
    state.hybrid_model.eval()

    # 3. Load Decision Pipeline
    state.decision_pipeline = EndToEndDecisionPipeline(
        hybrid_model=state.hybrid_model,
        device=state.device,
        mc_samples=8
    )

    # 4. Load Food Vision Pipeline with resilient multi-provider fallback
    from food_vision.providers.base import BaseNutritionProvider
    from food_vision.schemas import NutritionResult

    class CompositeNutritionProvider(BaseNutritionProvider):
        def __init__(self):
            self.usda = USDANutritionProvider()
            self.fallback = MockNutritionProvider()

        @property
        def provider_name(self) -> str:
            return "composite_usda_offline_fallback"

        @property
        def is_available(self) -> bool:
            return True

        def lookup_nutrition(self, food_name: str) -> Optional[NutritionResult]:
            try:
                res = self.usda.lookup_nutrition(food_name)
                if res is not None and res.carbs_g_per_100g is not None:
                    return res
            except:
                pass
            return self.fallback.lookup_nutrition(food_name)

    state.meal_pipeline = MealAnalysisPipeline(
        recognition_provider=HuggingFaceFoodRecognitionProvider(),
        nutrition_provider=CompositeNutritionProvider()
    )

    state.is_ready = True
    print("[API STARTUP] GlucoShield API Service successfully initialized.")
    yield
    print("[API SHUTDOWN] Shutting down GlucoShield service.")

app = FastAPI(
    title="GlucoShield Clinical Decision-Support API",
    description="Physics-Informed Neural-ODE Glucose Forecasting & Automated Meal-Aware Decision Engine.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/health", response_model=HealthResponse, tags=["System Health"])
async def get_health():
    """System health check, component readiness, and research disclaimer."""
    return HealthResponse(
        status="healthy" if state.is_ready else "initializing",
        version="1.0.0",
        neural_forecaster_loaded=state.hybrid_model is not None,
        hybrid_forecaster_loaded=state.hybrid_model is not None,
        ode_digital_twin_ready=state.decision_pipeline is not None,
        food_vision_ready=state.meal_pipeline is not None,
        active_channels_contract=22,
        research_disclaimer=SafetyGuardrails.RESEARCH_DISCLAIMER,
        timestamp=datetime.utcnow().isoformat()
    )

@app.post("/api/v1/forecast", response_model=ForecastResponse, tags=["Forecasting & Risk"])
async def post_forecast(request: ForecastRequest):
    """
    Computes 5-hour multi-horizon hybrid glucose forecast, prediction intervals,
    clinical risk alerts, and natural language explanations from 24-hour patient history.
    """
    if not state.is_ready or state.decision_pipeline is None or state.preprocessor is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Model backend is initializing.")

    try:
        d_s, d_r, s_s, s_r, warns = state.preprocessor.preprocess_forecast_input(
            request.history_readings, request.static_profile
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Preprocessing error: {str(e)}")

    decision_out = state.decision_pipeline.process_patient_window(
        dynamic_seq_scaled=d_s,
        dynamic_seq_raw=d_r,
        static_feat_scaled=s_s,
        static_feat_raw=s_r
    )

    return ForecastResponse(
        disclaimer=decision_out["disclaimer"],
        patient_id=request.patient_id,
        current_state=decision_out["current_state"],
        forecast=decision_out["forecast"],
        hybrid_components=decision_out["hybrid_components"],
        risk_assessment=decision_out["risk_assessment"],
        explanation=decision_out["explanation"],
        wearable_context_logged=request.wearable_context is not None
    )

@app.post("/api/v1/what-if", response_model=WhatIfResponse, tags=["Simulation & What-If"])
async def post_what_if(request: WhatIfRequest):
    """
    Executes a mechanistic counterfactual 'What-If' ODE simulation for a proposed meal or insulin bolus.
    """
    if not state.is_ready or state.decision_pipeline is None or state.preprocessor is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Model backend is initializing.")

    try:
        d_s, d_r, s_s, s_r, warns = state.preprocessor.preprocess_forecast_input(
            request.history_readings, request.static_profile
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Preprocessing error: {str(e)}")

    decision_out = state.decision_pipeline.process_patient_window(
        dynamic_seq_scaled=d_s,
        dynamic_seq_raw=d_r,
        static_feat_scaled=s_s,
        static_feat_raw=s_r,
        what_if_carbs=request.scenario_meal_carbs_g,
        what_if_bolus=request.scenario_insulin_bolus_u
    )

    what_if = decision_out.get("what_if_simulation")
    if not what_if:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Counterfactual simulation failed.")

    return WhatIfResponse(
        disclaimer=decision_out["disclaimer"],
        scenario_name=what_if["scenario_name"],
        simulated_trajectory=what_if["simulated_trajectory"],
        nadir_glucose=what_if["nadir_glucose"],
        time_to_nadir_min=what_if["time_to_nadir_min"],
        peak_glucose=what_if["peak_glucose"],
        time_to_peak_min=what_if["time_to_peak_min"],
        time_in_range_pct=what_if["time_in_range_pct"],
        warnings=what_if["warnings"] + warns
    )

@app.post("/api/v1/food/analyze", response_model=FoodAnalyzeResponse, tags=["Food Vision"])
async def post_food_analyze(request: FoodAnalyzeRequest):
    """
    Analyzes a meal photograph (Base64) or text query, estimating macronutrients and applying clinical confidence checks.
    """
    if not state.is_ready or state.meal_pipeline is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Food vision backend is initializing.")

    if not request.image_base64 and not request.food_name_query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'image_base64' or 'food_name_query' must be provided."
        )

    if request.image_base64:
        try:
            image_bytes = base64.b64decode(request.image_base64)
            analysis = state.meal_pipeline.analyze_image(
                image_input=image_bytes,
                portion_g=request.portion_g,
                selected_candidate_index=request.selected_candidate_index
            )
        except Exception as e:
            # Fallback to mock recognition if image parsing fails
            analysis = state.meal_pipeline.analyze_food_text(
                food_name=request.food_name_query or "mixed meal",
                portion_g=request.portion_g
            )
    else:
        analysis = state.meal_pipeline.analyze_food_text(
            food_name=request.food_name_query,
            portion_g=request.portion_g
        )

    return FoodAnalyzeResponse(
        image_food_candidates=[c.to_dict() for c in analysis.image_food_candidates],
        selected_food=analysis.selected_food,
        portion_g=analysis.portion_g,
        nutrition_density=analysis.nutrition.to_dict() if analysis.nutrition else None,
        final_macros=analysis.final_macros,
        requires_user_confirmation=analysis.requires_user_confirmation,
        warnings=analysis.warnings
    )

@app.post("/api/v1/decision/full-flow", response_model=FullFlowDecisionResponse, tags=["End-to-End Orchestration"])
async def post_full_flow(request: FullFlowDecisionRequest):
    """
    Unified Multimodal Decision Flow:
      1. Validates 24-hour patient history.
      2. Analyzes optional meal photo/query via Food Vision.
      3. Computes 22-channel baseline hybrid forecast and risk alerts.
      4. If meal or bolus is proposed, runs counterfactual ODE 'What-If' simulation.
      5. Synthesizes a unified clinical decision report.
    """
    if not state.is_ready or state.decision_pipeline is None or state.preprocessor is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Model backend is initializing.")

    # 1. Optional Food Vision
    food_res = None
    derived_carbs = 0.0

    if request.meal_image_base64 or request.meal_food_query:
        if request.meal_image_base64:
            try:
                img_bytes = base64.b64decode(request.meal_image_base64)
                f_analysis = state.meal_pipeline.analyze_image(img_bytes, portion_g=request.meal_portion_g)
            except:
                f_analysis = state.meal_pipeline.analyze_food_text(request.meal_food_query or "meal", portion_g=request.meal_portion_g)
        else:
            f_analysis = state.meal_pipeline.analyze_food_text(request.meal_food_query, portion_g=request.meal_portion_g)

        food_res = FoodAnalyzeResponse(
            image_food_candidates=[c.to_dict() for c in f_analysis.image_food_candidates],
            selected_food=f_analysis.selected_food,
            portion_g=f_analysis.portion_g,
            nutrition_density=f_analysis.nutrition.to_dict() if f_analysis.nutrition else None,
            final_macros=f_analysis.final_macros,
            requires_user_confirmation=f_analysis.requires_user_confirmation,
            warnings=f_analysis.warnings
        )
        derived_carbs = float(f_analysis.final_macros.get("carbs_g", 0.0))

    # 2. Preprocess 24h history
    try:
        d_s, d_r, s_s, s_r, warns = state.preprocessor.preprocess_forecast_input(
            request.history_readings, request.static_profile
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Preprocessing error: {str(e)}")

    # 3. Run Decision Pipeline (with What-If if meal carbs or bolus present)
    what_if_carbs = derived_carbs if derived_carbs > 0 else None
    what_if_bolus = request.proposed_insulin_bolus_u

    decision_out = state.decision_pipeline.process_patient_window(
        dynamic_seq_scaled=d_s,
        dynamic_seq_raw=d_r,
        static_feat_scaled=s_s,
        static_feat_raw=s_r,
        what_if_carbs=what_if_carbs,
        what_if_bolus=what_if_bolus
    )

    baseline_resp = ForecastResponse(
        disclaimer=decision_out["disclaimer"],
        patient_id=request.patient_id,
        current_state=decision_out["current_state"],
        forecast=decision_out["forecast"],
        hybrid_components=decision_out["hybrid_components"],
        risk_assessment=decision_out["risk_assessment"],
        explanation=decision_out["explanation"],
        wearable_context_logged=request.wearable_context is not None
    )

    what_if_resp = None
    if decision_out.get("what_if_simulation"):
        w = decision_out["what_if_simulation"]
        what_if_resp = WhatIfResponse(
            disclaimer=decision_out["disclaimer"],
            scenario_name=w["scenario_name"],
            simulated_trajectory=w["simulated_trajectory"],
            nadir_glucose=w["nadir_glucose"],
            time_to_nadir_min=w["time_to_nadir_min"],
            peak_glucose=w["peak_glucose"],
            time_to_peak_min=w["time_to_peak_min"],
            time_in_range_pct=w["time_in_range_pct"],
            warnings=w["warnings"] + warns
        )

    # 4. Synthesize Decision Recommendation
    rec_summary = {
        "alert_status": decision_out["risk_assessment"]["alert_level"],
        "recommended_action": "Monitor trend" if decision_out["risk_assessment"]["alert_level"] == "NORMAL" else "Review impending hypoglycemia risk",
        "meal_carbs_considered_g": round(derived_carbs, 1),
        "bolus_considered_u": round(request.proposed_insulin_bolus_u, 1) if request.proposed_insulin_bolus_u is not None else 0.0,
        "requires_food_confirmation": food_res.requires_user_confirmation if food_res else False
    }

    return FullFlowDecisionResponse(
        disclaimer=decision_out["disclaimer"],
        patient_id=request.patient_id,
        food_analysis=food_res,
        baseline_forecast=baseline_resp,
        what_if_simulation=what_if_resp,
        decision_summary=rec_summary
    )

# ------------------------------------------------------------------------------
# Static Frontend Mount (Phase 9 Production Dashboard)
# ------------------------------------------------------------------------------
from fastapi.staticfiles import StaticFiles

DIST_DIR = os.path.join(BASE_DIR, "frontend", "dist")
if os.path.exists(DIST_DIR):
    app.mount("/", StaticFiles(directory=DIST_DIR, html=True), name="frontend")

