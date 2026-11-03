"""
GlucoShield — Production FastAPI Service Layer (Phase 16 Hardened)
==================================================================
Exposes standardized REST endpoints for:
  - Authentication: /api/v1/auth/...
  - Longitudinal Data & Profiles: /api/v1/patients/...
  - Health & Readiness Probes:
      * GET /api/v1/health (General status & research disclaimer)
      * GET /api/v1/health/live (Liveness probe)
      * GET /api/v1/health/ready (Readiness probe)
      * GET /api/v1/health/models (Model registry & artifact integrity report)
      * GET /api/v1/health/db (Database connectivity probe)
  - Scientific Forecasting: POST /api/v1/forecast (Supports V1_FROZEN default & PHASE13_VALIDATED)
  - In Silico What-If: POST /api/v1/what-if
  - Food Vision Recognition: POST /api/v1/food/analyze
  - Multimodal Decision Orchestration: POST /api/v1/decision/full-flow
  - Longitudinal Analytics: /api/v1/analytics/...
  - Frontend SPA Static Serving: GET /
"""

import os
import sys
import json
import base64
import torch
import numpy as np
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

BASE_DIR = "D:/ML PROJECT"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from db.session import get_db, engine
from db.models import (
    Base,
    User,
    PatientProfile,
    ForecastRecord,
    WhatIfRecord,
    FoodAnalysisRecord,
    DecisionRecord
)
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
from api.deps import get_optional_current_user
from api.routers import auth_router, patients_router, analytics_router, devices_router, cohort_router
from api.preprocessor import InputPayloadPreprocessor
from api.artifact_verifier import verify_artifact_integrity
from api.config import get_config, AppConfig, EnvironmentProfile
from api.model_registry import (
    get_configured_model_version,
    resolve_model_version,
    get_model_traceability,
    ModelVersion,
    MODEL_METADATA
)
from api.middleware import HardenedProductionMiddleware

# Neural & Physiology Components
from neural.models import GlucoShieldMultiTaskRNN
from physiology.hybrid_fusion import GlucoShieldHybridForecaster
from decision_engine.pipeline import EndToEndDecisionPipeline
from decision_engine.safety import SafetyGuardrails
from food_vision.pipeline.meal_analysis_pipeline import MealAnalysisPipeline
from food_vision.providers.mock_provider import MockNutritionProvider
from food_vision.providers.usda_nutrition_provider import USDANutritionProvider
from food_vision.providers.huggingface_food_provider import HuggingFaceFoodRecognitionProvider
from food_vision.providers.local_food_provider import LocalFoodRecognitionProvider
from food_vision.providers.base import BaseNutritionProvider
from food_vision.schemas import NutritionResult

# Phase 13 / V2 Validated Components
from models.v2.context_encoder import PhysiologicalContextBatch
from models.v2.neural_forecaster import GlucoShieldNeuralForecasterV2
from models.v2.hybrid_forecaster_v2 import GlucoShieldHybridForecasterV2
from scratch.phase13_disagreement_gate.disagreement_gate import DisagreementAttenuatedFusionGate
from scratch.phase13_patient_specific_ode.patient_ode_adapter import PatientOdeAdapter, PatientOdeConfig
from inference.combination_c_adapter import CombinationCProductionAdapter

# State container
class ServiceState:
    config: Optional[AppConfig] = None
    artifact_report: Optional[Dict[str, Any]] = None
    hybrid_model: Optional[GlucoShieldHybridForecaster] = None
    decision_pipeline: Optional[EndToEndDecisionPipeline] = None
    combination_c_adapter: Optional[CombinationCProductionAdapter] = None
    preprocessor: Optional[InputPayloadPreprocessor] = None
    meal_pipeline: Optional[MealAnalysisPipeline] = None
    v2_hybrid: Optional[GlucoShieldHybridForecasterV2] = None
    phase13_gate: Optional[DisagreementAttenuatedFusionGate] = None
    phase13_adapter: Optional[PatientOdeAdapter] = None
    device: torch.device = torch.device("cpu")
    is_ready: bool = False

state = ServiceState()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load and validate application configuration
    app_config = get_config()
    state.config = app_config

    # Ensure all tables exist in database on startup
    Base.metadata.create_all(bind=engine)

    # Startup: 1. Strict Bitwise Frozen Artifact Verification
    passed, report = verify_artifact_integrity(target_model="ALL", fail_fast=True)
    state.artifact_report = report

    # Startup: 2. Hardware Resource Initialization
    state.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[API STARTUP] Initializing GlucoShield backend on {state.device} (Profile: {app_config.app_env.value})...")

    # 3. Load Preprocessor
    state.preprocessor = InputPayloadPreprocessor()

    # 4. Load V1 Neural & Hybrid Forecaster (Production Baseline Default)
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

    # 5. Load V1 Decision Pipeline
    state.decision_pipeline = EndToEndDecisionPipeline(
        hybrid_model=state.hybrid_model,
        device=state.device,
        mc_samples=8
    )

    # 6. Load V2 / Phase 13 Validated Architecture Components
    v2_ckpt = os.path.join(BASE_DIR, "models", "v2", "glucoshield_v2_best.pt")
    if os.path.exists(v2_ckpt):
        v2_neural = GlucoShieldNeuralForecasterV2().to(state.device)
        state.v2_hybrid = GlucoShieldHybridForecasterV2(v2_neural, freeze_neural=False, calib_iterations=5).to(state.device)
        state.v2_hybrid.load_state_dict(torch.load(v2_ckpt, map_location=state.device))
        state.v2_hybrid.eval()

    gate_cfg_path = os.path.join(BASE_DIR, "scratch", "phase13_disagreement_gate", "frozen_gate_config.json")
    if os.path.exists(gate_cfg_path):
        with open(gate_cfg_path) as f:
            g_cfg = json.load(f)["selected_parameters"]
        state.phase13_gate = DisagreementAttenuatedFusionGate(
            ceiling=g_cfg["ceiling"],
            d_mid=g_cfg["d_mid"],
            tau=g_cfg["tau"],
            w_high=g_cfg["w_high"]
        )

    ode_cfg_path = os.path.join(BASE_DIR, "scratch", "phase13_patient_specific_ode", "ode_adaptation_config.json")
    if os.path.exists(ode_cfg_path):
        with open(ode_cfg_path) as f:
            o_cfg = json.load(f)["parameters"]
        state.phase13_adapter = PatientOdeAdapter(PatientOdeConfig(
            adapt_si=o_cfg["adapt_si"],
            adapt_gb=o_cfg["adapt_gb"],
            eta_si=o_cfg["eta_si"],
            eta_gb=o_cfg["eta_gb"],
            beta=o_cfg["beta"],
            clip_si=o_cfg["clip_si"],
            clip_gb=o_cfg["clip_gb"],
            deadband=o_cfg["deadband"]
        ))

    # 7. Load Food Vision Pipeline with resilient multi-provider fallback
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
            except Exception:
                pass
            return self.fallback.lookup_nutrition(food_name)

    local_provider = LocalFoodRecognitionProvider()
    recognition_provider = local_provider if local_provider.is_available else HuggingFaceFoodRecognitionProvider()
    state.meal_pipeline = MealAnalysisPipeline(
        recognition_provider=recognition_provider,
        nutrition_provider=CompositeNutritionProvider()
    )

    # 8. Initialize Certified Combination C Production Serving Adapter
    if state.hybrid_model is not None and state.v2_hybrid is not None and state.phase13_gate is not None:
        state.combination_c_adapter = CombinationCProductionAdapter(
            v1_hybrid=state.hybrid_model,
            v2_hybrid=state.v2_hybrid,
            phase13_gate=state.phase13_gate,
            risk_engine=state.decision_pipeline.risk_engine if state.decision_pipeline else None,
            explainer=state.decision_pipeline.explainer if state.decision_pipeline else None,
            phase13_adapter=state.phase13_adapter,
            device=state.device
        )
        print("[API STARTUP] Certified Combination C Production Serving Adapter initialized.")

    state.is_ready = True
    print(f"[API STARTUP] GlucoShield API Service successfully initialized. (Active Model: {get_configured_model_version()})")
    yield
    print("[API SHUTDOWN] Shutting down GlucoShield service.")

app = FastAPI(
    title="GlucoShield Clinical Decision-Support API",
    description="Physics-Informed Neural-ODE Glucose Forecasting & Automated Meal-Aware Decision Engine.",
    version="1.0.0",
    lifespan=lifespan
)

# Configuration & Middleware
app_config = get_config()

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Hardened Security, Rate Limiting & Observability Middleware
app.add_middleware(HardenedProductionMiddleware, config=app_config)

# Register Sub-Routers
app.include_router(auth_router)
app.include_router(patients_router)
app.include_router(analytics_router)
app.include_router(devices_router)
app.include_router(cohort_router)

# ------------------------------------------------------------------------------
# Health, Readiness, and Liveness Probes
# ------------------------------------------------------------------------------

@app.get("/api/v1/health", response_model=HealthResponse, tags=["System Health"])
def get_health(db: Session = Depends(get_db)):
    """System health check, component readiness, database status, and active model version."""
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    return HealthResponse(
        status="healthy" if state.is_ready else "initializing",
        version="1.0.0",
        neural_forecaster_loaded=state.hybrid_model is not None,
        hybrid_forecaster_loaded=state.hybrid_model is not None,
        ode_digital_twin_ready=state.decision_pipeline is not None,
        food_vision_ready=state.meal_pipeline is not None,
        active_channels_contract=22,
        database_connected=db_ok,
        research_disclaimer=SafetyGuardrails.RESEARCH_DISCLAIMER,
        timestamp=datetime.now(timezone.utc).isoformat(),
        active_model_version=get_configured_model_version(),
        available_models=list(MODEL_METADATA.keys()),
        artifact_integrity="VERIFIED" if (state.artifact_report and state.artifact_report.get("status") == "PASS") else "UNVERIFIED"
    )

@app.get("/api/v1/health/live", tags=["System Health"])
def get_liveness():
    """Liveness probe for orchestrators (Kubernetes / Docker healthcheck)."""
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/v1/health/ready", tags=["System Health"])
def get_readiness(db: Session = Depends(get_db)):
    """Readiness probe checking models and database connectivity."""
    if not state.is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model and service backend is initializing."
        )
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connectivity check failed: {str(e)}"
        )
    return {
        "status": "ready",
        "model_backend": "ready",
        "database": "ready",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/v1/health/models", tags=["System Health"])
def get_models_health():
    """Model artifact verification status and active registry metadata."""
    return {
        "active_model_version": get_configured_model_version(),
        "available_models": list(MODEL_METADATA.keys()),
        "artifact_verification": state.artifact_report or {},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/v1/health/db", tags=["System Health"])
def get_db_health(db: Session = Depends(get_db)):
    """Database connectivity and connection pool diagnostic."""
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unreachable: {str(e)}"
        )
    return {
        "status": db_status,
        "database_type": "postgresql" if "postgresql" in engine.url.drivername else "sqlite",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# ------------------------------------------------------------------------------
# Core Scientific Inference Endpoints
# ------------------------------------------------------------------------------

@app.post("/api/v1/forecast", response_model=ForecastResponse, tags=["Forecasting & Risk"])
def post_forecast(
    request: ForecastRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
    x_model_version: Optional[str] = Header(None)
):
    """
    Computes 5-hour multi-horizon hybrid glucose forecast, prediction intervals,
    clinical risk alerts, and natural language explanations.
    Supports explicit version selection: V1_FROZEN (production default), V2_FROZEN, or PHASE13_VALIDATED.
    """
    if not state.is_ready or state.decision_pipeline is None or state.preprocessor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model backend is initializing."
        )

    # 1. Resolve Model Version
    requested = request.requested_model_version or x_model_version
    model_ver = resolve_model_version(requested)

    # 2. Input Preprocessing
    try:
        d_s, d_r, s_s, s_r, warns = state.preprocessor.preprocess_forecast_input(
            request.history_readings, request.static_profile
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Preprocessing error: {str(e)}"
        )

    # 3. Model Execution Branching
    if model_ver == ModelVersion.COMBINATION_C.value:
        # Certified Production Default: Combination C (V1 Point + Phase 13 Regime-Conditioned Uncertainty)
        if state.combination_c_adapter is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Combination C production serving adapter is uninitialized."
            )
        try:
            pred_dict = state.combination_c_adapter.predict(
                dynamic_seq_scaled=d_s,
                dynamic_seq_raw=d_r,
                static_feat_scaled=s_s,
                static_feat_raw=s_r,
                patient_id=request.patient_id,
                wearable_context_logged=request.wearable_context is not None
            )
            response_obj = ForecastResponse(**pred_dict)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Combination C serving failure: {str(e)}"
            )

    elif model_ver == ModelVersion.PHASE13_VALIDATED.value and state.v2_hybrid is not None and state.phase13_gate is not None:
        # Phase 13 Validated Forecaster
        sin_24 = d_r[:, -1, 10]
        cos_24 = d_r[:, -1, 11]
        f_circ = torch.stack([sin_24, cos_24, 2.0 * sin_24 * cos_24, cos_24**2 - sin_24**2], dim=-1).to(state.device)

        ctx = PhysiologicalContextBatch(
            f_exercise=torch.zeros(1, 4, device=state.device),
            m_exercise=torch.zeros(1, 1, device=state.device),
            f_sleep=torch.zeros(1, 5, device=state.device),
            m_sleep=torch.zeros(1, 1, device=state.device),
            f_hormonal=torch.zeros(1, 3, device=state.device),
            m_hormonal=torch.zeros(1, 1, device=state.device),
            f_circadian=f_circ
        )

        with torch.no_grad():
            v2_out = state.v2_hybrid(d_s, d_r, s_s, s_r, ctx, calibrate=False, ablation_mode="full_v2")
            y_neural = v2_out["y_neural"].cpu().numpy()
            y_ode = v2_out["y_ode"].cpu().numpy()
            alpha_raw = v2_out["alpha"].cpu().numpy()
            residual = v2_out["residual"].cpu().numpy()

            blended = state.phase13_gate.blend(y_neural, y_ode, alpha_raw, residual)
            traj = blended["trajectory"][0]
            w_phys = blended["w_phys"][0]
            disag = blended["disagreement"][0]

            p_int = v2_out["prediction_interval"]
            half_w95 = ((p_int.upper_95 - p_int.lower_95) / 2.0).cpu().numpy()[0]
            half_w80 = ((p_int.upper_80 - p_int.lower_80) / 2.0).cpu().numpy()[0]

            low95 = traj - half_w95
            upp95 = traj + half_w95
            low80 = traj - half_w80
            upp80 = traj + half_w80

        curr_state = {
            "glucose_mg_dl": round(float(d_r[0, -1, 0]), 1),
            "iob_units": round(float(d_r[0, -1, 16]), 2),
            "cob_grams": round(float(d_r[0, -1, 19]), 1),
            "velocity_mg_dl_per_15m": round(float(d_r[0, -1, 1]), 2)
        }

        # Safe clinical risk and explanation evaluation
        if state.decision_pipeline is not None:
            r_ass = state.decision_pipeline.risk_engine.evaluate_risk(
                current_glucose=curr_state["glucose_mg_dl"],
                trajectory=traj,
                risk_probs=np.zeros(5),
                interval_lower_95=low95
            )
            risk_eval = {
                "primary_status": r_ass.primary_status,
                "alert_level": r_ass.alert_level,
                "hypo_1h_prob": r_ass.hypo_risk_1h_prob,
                "hypo_2h_prob": r_ass.hypo_risk_2h_prob,
                "hypo_4h_prob": r_ass.hypo_risk_4h_prob,
                "hyper_2h_prob": r_ass.hyper_risk_2h_prob,
                "hyper_4h_prob": r_ass.hyper_risk_4h_prob,
                "nadir_mg_dl": r_ass.trajectory_nadir_mg_dl,
                "time_to_nadir_min": r_ass.time_to_nadir_min,
                "peak_mg_dl": r_ass.trajectory_peak_mg_dl,
                "time_to_peak_min": r_ass.time_to_peak_min,
                "projected_hypo_duration_min": r_ass.projected_hypo_duration_min,
                "active_alerts": r_ass.active_alerts
            }
            exp_rep = state.decision_pipeline.explainer.generate_explanation(
                current_glucose=curr_state["glucose_mg_dl"],
                trajectory=traj,
                iob_units=curr_state["iob_units"],
                cob_grams=curr_state["cob_grams"],
                mean_alpha=0.40,
                mean_uncertainty_std=float(np.mean(half_w95 / 1.96)),
                primary_status=r_ass.primary_status
            )
            explanation_eval = {
                "headline": exp_rep.headline,
                "trend_summary": exp_rep.trend_summary,
                "metabolic_factors": exp_rep.metabolic_factors,
                "hybrid_attribution": exp_rep.hybrid_attribution,
                "uncertainty_rationale": exp_rep.uncertainty_rationale,
                "key_takeaway": exp_rep.key_takeaway
            }
        else:
            risk_eval = {"alert_level": "NONE", "active_alerts": []}
            explanation_eval = {"headline": "Phase 13 Validated Forecast", "trend_summary": "Stable", "metabolic_factors": [], "hybrid_attribution": "", "uncertainty_rationale": "", "key_takeaway": ""}

        trace = get_model_traceability(ModelVersion.PHASE13_VALIDATED.value)
        telemetry = {
            "disagreement_mean_mg_dl": round(float(np.mean(disag)), 2),
            "disagreement_max_mg_dl": round(float(np.max(disag)), 2),
            "physics_contribution_mean_pct": round(float(np.mean(w_phys) * 100.0), 2),
            "physics_ceiling_enforced": bool(np.max(w_phys) <= 0.40001),
            "adapted_si": state.phase13_adapter.config.base_si if state.phase13_adapter else 0.002869,
            "gb_equilibrium": 141.79
        }

        response_obj = ForecastResponse(
            disclaimer=SafetyGuardrails.RESEARCH_DISCLAIMER,
            patient_id=request.patient_id,
            current_state=curr_state,
            forecast={
                "point_forecast_mg_dl": [round(float(v), 1) for v in traj],
                "lower_80_mg_dl": [round(float(v), 1) for v in low80],
                "upper_80_mg_dl": [round(float(v), 1) for v in upp80],
                "lower_95_mg_dl": [round(float(v), 1) for v in low95],
                "upper_95_mg_dl": [round(float(v), 1) for v in upp95]
            },
            hybrid_components={
                "neural_prediction_mg_dl": [round(float(v), 1) for v in y_neural[0]],
                "physics_ode_prediction_mg_dl": [round(float(v), 1) for v in y_ode[0]],
                "effective_physics_weight": [round(float(v), 3) for v in w_phys]
            },
            risk_assessment=risk_eval,
            explanation=explanation_eval,
            wearable_context_logged=request.wearable_context is not None,
            model_version=ModelVersion.PHASE13_VALIDATED.value,
            traceability=trace,
            telemetry=telemetry
        )

    else:
        # Explicit V1 Legacy Baseline Execution (MC-Dropout intervals)
        decision_out = state.decision_pipeline.process_patient_window(
            dynamic_seq_scaled=d_s,
            dynamic_seq_raw=d_r,
            static_feat_scaled=s_s,
            static_feat_raw=s_r
        )
        trace = get_model_traceability(ModelVersion.V1_FROZEN.value)
        response_obj = ForecastResponse(
            disclaimer=decision_out["disclaimer"],
            patient_id=request.patient_id,
            current_state=decision_out["current_state"],
            forecast=decision_out["forecast"],
            hybrid_components=decision_out.get("hybrid_components", {}),
            risk_assessment=decision_out["risk_assessment"],
            explanation=decision_out["explanation"],
            wearable_context_logged=request.wearable_context is not None,
            model_version=ModelVersion.V1_FROZEN.value,
            traceability=trace,
            telemetry=None
        )

    # 4. Optional Persistence for Authenticated / Recognized Patients
    target_patient = None
    if current_user:
        target_patient = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
    if not target_patient and request.patient_id:
        target_patient = db.query(PatientProfile).filter(
            (PatientProfile.id == request.patient_id) | (PatientProfile.patient_display_id == request.patient_id)
        ).first()

    if target_patient:
        try:
            # Idempotency check: Deduplicate rapid duplicate forecast requests within 45s with identical point forecast
            recent_record = (
                db.query(ForecastRecord)
                .filter(ForecastRecord.patient_id == target_patient.id)
                .order_by(ForecastRecord.created_at.desc())
                .first()
            )
            is_duplicate = False
            if recent_record and recent_record.created_at:
                age_seconds = (datetime.utcnow() - recent_record.created_at).total_seconds()
                if age_seconds < 45.0:
                    same_glucose = abs(recent_record.current_glucose - float(response_obj.current_state["glucose_mg_dl"])) < 0.1
                    same_forecast = recent_record.point_forecast == response_obj.forecast["point_forecast_mg_dl"]
                    if same_glucose and same_forecast:
                        is_duplicate = True
                        response_obj.record_id = recent_record.id

            if not is_duplicate:
                f_record = ForecastRecord(
                    patient_id=target_patient.id,
                    timestamp=datetime.utcnow(),
                    current_glucose=float(response_obj.current_state["glucose_mg_dl"]),
                    current_iob=float(response_obj.current_state["iob_units"]),
                    current_cob=float(response_obj.current_state["cob_grams"]),
                    point_forecast=response_obj.forecast["point_forecast_mg_dl"],
                    lower_80=response_obj.forecast["lower_80_mg_dl"],
                    upper_80=response_obj.forecast["upper_80_mg_dl"],
                    lower_95=response_obj.forecast["lower_95_mg_dl"],
                    upper_95=response_obj.forecast["upper_95_mg_dl"],
                    hybrid_components=response_obj.hybrid_components,
                    risk_assessment=response_obj.risk_assessment,
                    explanation=response_obj.explanation,
                    disclaimer=response_obj.disclaimer
                )
                db.add(f_record)
                db.commit()
                response_obj.record_id = f_record.id
        except Exception:
            db.rollback()

    return response_obj

@app.post("/api/v1/what-if", response_model=WhatIfResponse, tags=["Forecasting & Risk"])
def post_what_if(
    request: WhatIfRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """
    Simulates alternative clinical interventions (what-if meal carbs and bolus insulin)
    against the mechanistic digital twin and neural residual engine.
    """
    if not state.is_ready or state.decision_pipeline is None or state.preprocessor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model backend is initializing."
        )

    try:
        d_s, d_r, s_s, s_r, warns = state.preprocessor.preprocess_forecast_input(
            request.history_readings, request.static_profile
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Preprocessing error: {str(e)}"
        )

    # Use process_patient_window with what-if params — simulation is embedded in the result
    decision_out = state.decision_pipeline.process_patient_window(
        dynamic_seq_scaled=d_s,
        dynamic_seq_raw=d_r,
        static_feat_scaled=s_s,
        static_feat_raw=s_r,
        what_if_carbs=request.scenario_meal_carbs_g,
        what_if_bolus=request.scenario_insulin_bolus_u
    )

    sim_res = decision_out.get("what_if_simulation")
    if not sim_res:
        # Fallback: construct minimal response from forecast when no what-if data
        forecast = decision_out.get("forecast", {})
        traj = forecast.get("point_forecast_mg_dl", [])
        sim_res = {
            "scenario_name": f"What-If: {request.scenario_meal_carbs_g:.0f}g Carbs, {request.scenario_insulin_bolus_u:.1f}U Bolus",
            "simulated_trajectory": traj,
            "nadir_glucose": min(traj) if traj else 0.0,
            "time_to_nadir_min": 0,
            "peak_glucose": max(traj) if traj else 0.0,
            "time_to_peak_min": 0,
            "time_in_range_pct": 0.0,
            "warnings": warns
        }

    record_id = None
    target_patient = None
    if current_user:
        target_patient = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
    if not target_patient and request.patient_id:
        target_patient = db.query(PatientProfile).filter(
            (PatientProfile.id == request.patient_id) | (PatientProfile.patient_display_id == request.patient_id)
        ).first()

    if target_patient:
        try:
            # Idempotency check: Deduplicate rapid duplicate what-if requests within 45s with identical parameters
            recent_whatif = (
                db.query(WhatIfRecord)
                .filter(WhatIfRecord.patient_id == target_patient.id)
                .order_by(WhatIfRecord.created_at.desc())
                .first()
            )
            is_duplicate = False
            if recent_whatif and recent_whatif.created_at:
                age_seconds = (datetime.utcnow() - recent_whatif.created_at).total_seconds()
                if age_seconds < 45.0:
                    same_carbs = abs(recent_whatif.scenario_meal_carbs_g - request.scenario_meal_carbs_g) < 0.05
                    same_bolus = abs(recent_whatif.scenario_insulin_bolus_u - request.scenario_insulin_bolus_u) < 0.05
                    same_name = recent_whatif.scenario_name == sim_res["scenario_name"]
                    if same_carbs and same_bolus and same_name:
                        is_duplicate = True
                        record_id = recent_whatif.id

            if not is_duplicate:
                w_record = WhatIfRecord(
                    patient_id=target_patient.id,
                    timestamp=datetime.utcnow(),
                    scenario_name=sim_res["scenario_name"],
                    scenario_meal_carbs_g=request.scenario_meal_carbs_g,
                    scenario_insulin_bolus_u=request.scenario_insulin_bolus_u,
                    simulated_trajectory=sim_res["simulated_trajectory"],
                    nadir_glucose=sim_res["nadir_glucose"],
                    time_to_nadir_min=int(sim_res.get("time_to_nadir_min", 0)),
                    peak_glucose=sim_res["peak_glucose"],
                    time_to_peak_min=int(sim_res.get("time_to_peak_min", 0)),
                    time_in_range_pct=sim_res["time_in_range_pct"],
                    warnings=sim_res.get("warnings", []) + warns
                )
                db.add(w_record)
                db.commit()
                record_id = w_record.id
        except Exception:
            db.rollback()

    return WhatIfResponse(
        disclaimer=SafetyGuardrails.RESEARCH_DISCLAIMER,
        scenario_name=sim_res["scenario_name"],
        simulated_trajectory=sim_res["simulated_trajectory"],
        nadir_glucose=sim_res["nadir_glucose"],
        time_to_nadir_min=sim_res["time_to_nadir_min"],
        peak_glucose=sim_res["peak_glucose"],
        time_to_peak_min=sim_res["time_to_peak_min"],
        time_in_range_pct=sim_res["time_in_range_pct"],
        warnings=sim_res.get("warnings", []) + warns,
        record_id=record_id
    )

@app.post("/api/v1/food/analyze", response_model=FoodAnalyzeResponse, tags=["Food Vision & Nutrition"])
def post_food_analyze(
    request: FoodAnalyzeRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyzes meal photograph or text query via multimodal vision and USDA nutrition databases.
    """
    if not state.is_ready or state.meal_pipeline is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Food vision engine is initializing."
        )

    image_bytes = None
    if request.image_base64:
        try:
            raw_b64 = request.image_base64
            if "," in raw_b64:
                raw_b64 = raw_b64.split(",", 1)[1]
            image_bytes = base64.b64decode(raw_b64)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid base64 image encoding."
            )

    # Dispatch to correct pipeline method based on input type
    if image_bytes:
        analysis_res = state.meal_pipeline.analyze_image(
            image_input=image_bytes,
            portion_g=request.portion_g,
            selected_candidate_index=request.selected_candidate_index
        )
    elif request.food_name_query:
        analysis_res = state.meal_pipeline.analyze_food_text(
            food_name=request.food_name_query,
            portion_g=request.portion_g
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either image_base64 or food_name_query must be provided."
        )

    record_id = None
    target_patient = None
    if current_user:
        target_patient = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()

    if target_patient:
        try:
            fa_record = FoodAnalysisRecord(
                patient_id=target_patient.id,
                food_name_query=request.food_name_query,
                selected_food=analysis_res.selected_food,
                portion_g=analysis_res.portion_g,
                candidates=analysis_res.image_food_candidates,
                nutrition_density=analysis_res.nutrition_density,
                final_macros=analysis_res.final_macros,
                requires_user_confirmation=analysis_res.requires_user_confirmation,
                warnings=analysis_res.warnings
            )
            db.add(fa_record)
            db.commit()
            record_id = fa_record.id
        except Exception:
            db.rollback()

    return FoodAnalyzeResponse(
        image_food_candidates=[c.to_dict() for c in analysis_res.image_food_candidates],
        selected_food=analysis_res.selected_food,
        portion_g=analysis_res.portion_g,
        nutrition_density=analysis_res.nutrition.to_dict() if analysis_res.nutrition else None,
        final_macros=analysis_res.final_macros,
        requires_user_confirmation=analysis_res.requires_user_confirmation,
        warnings=analysis_res.warnings,
        record_id=record_id
    )

@app.post("/api/v1/decision/full-flow", response_model=FullFlowDecisionResponse, tags=["End-to-End Orchestration"])
def post_full_flow(
    request: FullFlowDecisionRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """
    Executes complete clinical decision orchestration:
      1. Meal Vision & Macro Identification
      2. Baseline 5-Hour Forecast
      3. Counterfactual What-If Simulation
      4. Risk Synthesis & Advisory Recommendation
    """
    if not state.is_ready or state.decision_pipeline is None or state.meal_pipeline is None or state.preprocessor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model and decision backend is initializing."
        )

    # 1. Meal Analysis
    food_res = None
    derived_carbs = 0.0
    if request.meal_image_base64 or request.meal_food_query:
        image_bytes = None
        if request.meal_image_base64:
            try:
                raw_b64 = request.meal_image_base64
                if "," in raw_b64:
                    raw_b64 = raw_b64.split(",", 1)[1]
                image_bytes = base64.b64decode(raw_b64)
            except Exception:
                pass

        # Dispatch to correct pipeline method
        if image_bytes:
            m_out = state.meal_pipeline.analyze_image(
                image_input=image_bytes,
                portion_g=request.meal_portion_g
            )
        elif request.meal_food_query:
            m_out = state.meal_pipeline.analyze_food_text(
                food_name=request.meal_food_query,
                portion_g=request.meal_portion_g
            )
        else:
            m_out = None

        if m_out is not None:
            food_res = FoodAnalyzeResponse(
                image_food_candidates=[c.to_dict() for c in m_out.image_food_candidates],
                selected_food=m_out.selected_food,
                portion_g=m_out.portion_g,
                nutrition_density=m_out.nutrition.to_dict() if m_out.nutrition else None,
                final_macros=m_out.final_macros,
                requires_user_confirmation=m_out.requires_user_confirmation,
                warnings=m_out.warnings
            )
            derived_carbs = m_out.final_macros.get("carbs_g") or 0.0

    # 2. Preprocess Input
    try:
        d_s, d_r, s_s, s_r, warns = state.preprocessor.preprocess_forecast_input(
            request.history_readings, request.static_profile
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Preprocessing error: {str(e)}"
        )

    what_if_carbs = derived_carbs if derived_carbs > 0.0 else None
    what_if_bolus = request.proposed_insulin_bolus_u

    decision_out = state.decision_pipeline.process_patient_window(
        dynamic_seq_scaled=d_s,
        dynamic_seq_raw=d_r,
        static_feat_scaled=s_s,
        static_feat_raw=s_r,
        what_if_carbs=what_if_carbs,
        what_if_bolus=what_if_bolus
    )

    if state.combination_c_adapter is not None:
        comb_dict = state.combination_c_adapter.predict(
            dynamic_seq_scaled=d_s,
            dynamic_seq_raw=d_r,
            static_feat_scaled=s_s,
            static_feat_raw=s_r,
            patient_id=request.patient_id,
            wearable_context_logged=request.wearable_context is not None
        )
        baseline_resp = ForecastResponse(**comb_dict)
    else:
        trace = get_model_traceability(ModelVersion.V1_FROZEN.value)
        baseline_resp = ForecastResponse(
            disclaimer=decision_out["disclaimer"],
            patient_id=request.patient_id,
            current_state=decision_out["current_state"],
            forecast=decision_out["forecast"],
            hybrid_components=decision_out.get("hybrid_components", {}),
            risk_assessment=decision_out["risk_assessment"],
            explanation=decision_out["explanation"],
            wearable_context_logged=request.wearable_context is not None,
            model_version=ModelVersion.V1_FROZEN.value,
            traceability=trace
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

    decision_record_id = None
    target_patient = None
    if current_user:
        target_patient = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
    if not target_patient and request.patient_id:
        target_patient = db.query(PatientProfile).filter(
            (PatientProfile.id == request.patient_id) | (PatientProfile.patient_display_id == request.patient_id)
        ).first()

    if target_patient:
        try:
            d_record = DecisionRecord(
                patient_id=target_patient.id,
                timestamp=datetime.now(timezone.utc),
                alert_status=decision_out["risk_assessment"]["alert_level"],
                recommended_action=rec_summary["recommended_action"],
                decision_summary=rec_summary,
                disclaimer=decision_out["disclaimer"]
            )
            db.add(d_record)
            db.commit()
            decision_record_id = d_record.id
        except Exception:
            db.rollback()

    return FullFlowDecisionResponse(
        disclaimer=decision_out["disclaimer"],
        patient_id=request.patient_id,
        food_analysis=food_res,
        baseline_forecast=baseline_resp,
        what_if_simulation=what_if_resp,
        decision_summary=rec_summary,
        decision_record_id=decision_record_id
    )

# ------------------------------------------------------------------------------
# Static Frontend Mount (Phase 9 Production Dashboard)
# ------------------------------------------------------------------------------
from fastapi.staticfiles import StaticFiles

DIST_DIR = os.path.join(BASE_DIR, "frontend", "dist")
if os.path.exists(DIST_DIR):
    app.mount("/", StaticFiles(directory=DIST_DIR, html=True), name="frontend")
