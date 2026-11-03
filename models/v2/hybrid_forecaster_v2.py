"""
GlucoShield V2 — Unified Factor-Aware Hybrid Forecaster
=========================================================
End-to-end integration of:
  1. Factor-Aware Recurrent Neural Forecaster V2
  2. Mechanistic Biomarker Prior Network
  3. Online 24-Hour Moving Horizon Calibrator (MHE)
  4. Differentiable RK4 Digital Twin Forward Simulator
  5. Factor-Aware Adaptive Fusion Gate
  6. Multi-Modal Non-Linear Residual Head
  7. Physics-Aware, Regime-Conditioned Uncertainty Estimator
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import dataclasses
from typing import Dict, Tuple, Optional, Any

from models.v2.context_encoder import PhysiologicalContextBatch
from models.v2.neural_forecaster import GlucoShieldNeuralForecasterV2
from models.v2.factor_fusion_gate import FactorAwareFusionGate
from models.v2.uncertainty_head import RegimeConditionedUncertaintyHead, PredictionIntervalV2

from physiology.state import MetabolicState
from physiology.parameters import PhysiologicalParameters
from physiology.priors import BiomarkerPriorNetwork
from physiology.calibrator import MovingHorizonCalibrator
from physiology.integrator import RK4Integrator

class GlucoShieldHybridForecasterV2(nn.Module):
    """
    Unified V2 Hybrid Forecaster supporting factor-aware neural representations,
    physiologically responsive gating, and regime-conditioned uncertainty quantification.
    """
    def __init__(
        self,
        neural_model: GlucoShieldNeuralForecasterV2,
        freeze_neural: bool = False,
        calib_iterations: int = 15,
        horizon: int = 20
    ):
        super().__init__()
        self.neural_model = neural_model
        if freeze_neural:
            for p in self.neural_model.parameters():
                p.requires_grad = False
            self.neural_model.eval()

        self.prior_net = BiomarkerPriorNetwork(static_dim=9, hidden_dim=32)
        self.calibrator = MovingHorizonCalibrator(num_iterations=calib_iterations)
        self.integrator = RK4Integrator(microsteps_per_interval=5, dt=3.0)
        self.fusion_gate = FactorAwareFusionGate(horizon=horizon)
        
        # Residual Head: [y_hybrid (20), z_context (32), static_feat_scaled (9)] = 61 -> 32 -> 20
        self.residual_head = nn.Sequential(
            nn.Linear(horizon + 32 + 9, 32),
            nn.LayerNorm(32),
            nn.ReLU(),
            nn.Linear(32, horizon)
        )
        nn.init.zeros_(self.residual_head[-1].weight)
        nn.init.zeros_(self.residual_head[-1].bias)

        # Uncertainty Head
        self.uncertainty_head = RegimeConditionedUncertaintyHead(horizon=horizon)

    def forward(
        self,
        dynamic_seq_scaled: torch.Tensor,                               # (batch, 96, 22)
        dynamic_seq_raw: torch.Tensor,                                  # (batch, 96, 22)
        static_feat_scaled: torch.Tensor,                               # (batch, 9)
        static_feat_raw: torch.Tensor,                                  # (batch, 9)
        context_batch: Optional[PhysiologicalContextBatch] = None,      # Multi-modal context
        future_insulin_raw: Optional[torch.Tensor] = None,              # (batch, 20)
        future_carbs_raw: Optional[torch.Tensor] = None,                # (batch, 20)
        calibrate: bool = True,
        factor_ode_mod: Optional[Dict[str, torch.Tensor]] = None,       # ODE factor shifts (e.g. SI_mult, Gb_shift)
        ablation_mode: str = "full_v2"                                  # e0, e1, e2, e3, e4, full_v2
    ) -> Dict[str, Any]:
        """
        Executes end-to-end V2 hybrid forecasting.
        """
        device = dynamic_seq_scaled.device
        batch_size = dynamic_seq_scaled.shape[0]

        if context_batch is None:
            context_batch = PhysiologicalContextBatch.create_empty(batch_size, device=device)
        else:
            context_batch = context_batch.to(device)

        if future_insulin_raw is None:
            future_insulin_raw = torch.zeros(batch_size, 20, device=device)
        if future_carbs_raw is None:
            future_carbs_raw = torch.zeros(batch_size, 20, device=device)

        # ----------------------------------------------------------------------
        # 1. Neural Forward Pass
        # ----------------------------------------------------------------------
        # In ablation E1 (no factors), pass empty context to neural model
        if ablation_mode in ["e0", "e1"]:
            empty_ctx = PhysiologicalContextBatch.create_empty(batch_size, device=device)
            neural_out = self.neural_model(dynamic_seq_scaled, static_feat_scaled, context_batch=empty_ctx)
        else:
            neural_out = self.neural_model(dynamic_seq_scaled, static_feat_scaled, context_batch=context_batch)

        y_neural = neural_out["trajectory"]
        quantiles = neural_out["quantiles"]
        risk_probs = neural_out["risk_probs"]
        risk_logits = neural_out["risk_logits"]
        z_context = neural_out["z_context"]

        # ----------------------------------------------------------------------
        # 2. Mechanistic Digital Twin (ODE Simulation)
        # ----------------------------------------------------------------------
        params_prior = self.prior_net(static_feat_raw)
        
        if calibrate and ablation_mode != "no_mhe":
            params_calib, state_t0, _ = self.calibrator.calibrate_and_observe(
                dynamic_seq_raw, params_prior, optimize_parameters=True
            )
        else:
            params_calib = params_prior
            state_t0 = MetabolicState.create_initial_state(
                initial_glucose=dynamic_seq_raw[:, -1, 0],
                initial_iob=dynamic_seq_raw[:, -1, 16],
                initial_cob=dynamic_seq_raw[:, -1, 19],
                device=device
            )

        # Apply physiological factor modulation to ODE parameters if supplied
        if factor_ode_mod is not None:
            mod_si = params_calib.S_I
            mod_gb = params_calib.G_b
            if "si_mult" in factor_ode_mod:
                mod_si = torch.clamp(mod_si * factor_ode_mod["si_mult"], min=1e-6, max=0.01)
            if "gb_shift" in factor_ode_mod:
                mod_gb = torch.clamp(mod_gb + factor_ode_mod["gb_shift"], min=60.0, max=300.0)
            params_ode = dataclasses.replace(params_calib, S_I=mod_si, G_b=mod_gb)
        else:
            params_ode = params_calib

        with torch.no_grad():
            y_ode, _ = self.integrator.forward_simulate(
                state_t0, future_insulin_raw, future_carbs_raw, params_ode
            )

        # ----------------------------------------------------------------------
        # 3. Factor-Aware Adaptive Fusion Gating
        # ----------------------------------------------------------------------
        factor_masks = torch.cat([
            context_batch.m_exercise,
            context_batch.m_sleep,
            context_batch.m_hormonal
        ], dim=-1)

        phi_gate = self.fusion_gate.extract_gating_features(
            dynamic_seq_raw=dynamic_seq_raw,
            y_neural=y_neural,
            y_ode=y_ode,
            z_context=z_context,
            future_ins=future_insulin_raw,
            future_carbs=future_carbs_raw,
            factor_masks=factor_masks
        )

        if ablation_mode in ["e0", "e1", "e2"]:
            # Static V1-style linspace logits behavior
            alpha = torch.sigmoid(torch.linspace(2.2, -0.2, 20, device=device).unsqueeze(0).expand(batch_size, -1))
        else:
            alpha = self.fusion_gate(phi_gate)

        y_hybrid = alpha * y_neural + (1.0 - alpha) * y_ode

        # ----------------------------------------------------------------------
        # 4. Multi-Modal Residual Head
        # ----------------------------------------------------------------------
        res_input = torch.cat([y_hybrid, z_context, static_feat_scaled], dim=-1)
        residual = self.residual_head(res_input)
        y_final = y_hybrid + residual

        # ----------------------------------------------------------------------
        # 5. Regime-Conditioned Uncertainty Quantification
        # ----------------------------------------------------------------------
        prediction_interval = self.uncertainty_head(
            y_final=y_final,
            y_neural=y_neural,
            y_ode=y_ode,
            quantiles=quantiles if ablation_mode not in ["e0", "e1", "e2", "e3"] else None,
            dynamic_seq_raw=dynamic_seq_raw,
            z_context=z_context
        )

        return {
            "trajectory": y_final,
            "y_hybrid": y_hybrid,
            "y_neural": y_neural,
            "y_ode": y_ode,
            "alpha": alpha,
            "residual": residual,
            "quantiles": quantiles,
            "risk_logits": risk_logits,
            "risk_probs": risk_probs,
            "prediction_interval": prediction_interval,
            "z_context": z_context,
            "phi_gate": phi_gate,
            "params_ode": params_ode,
            "state_t0": state_t0
        }
