"""
GlucoShield Physiology Engine - Adaptive Gated Hybrid Fusion Framework
======================================================================
Fuses the locked GLUCOSHIELD_NEURAL_FORECASTER_V1 with the Mechanistic ODE Digital Twin
using an uncertainty-aware, horizon-gated fusion layer.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Tuple, Optional
from neural.models import GlucoShieldMultiTaskRNN
from physiology.state import MetabolicState
from physiology.parameters import PhysiologicalParameters
from physiology.priors import BiomarkerPriorNetwork
from physiology.calibrator import MovingHorizonCalibrator
from physiology.integrator import RK4Integrator

class AdaptiveFusionGate(nn.Module):
    """
    Context-aware adaptive fusion gate that dynamically computes blending weights alpha(k) in [0, 1]
    between the Neural Forecaster and the Mechanistic ODE Digital Twin for each forecast step k in {1..20}.
    
    Inputs to Gate:
      - Horizon step index embedding (20,)
      - Neural forecast uncertainty / volatility
      - Recent glucose velocity and acceleration
      - Active future insulin and meal sum
    """
    def __init__(self, horizon: int = 20, hidden_dim: int = 32):
        super().__init__()
        self.horizon = horizon
        # Learnable baseline decay logit per horizon step (initialized higher at short horizons)
        # alpha_0 ~ 0.90 at k=1 (logit ~ +2.2), alpha_0 ~ 0.45 at k=20 (logit ~ -0.2)
        initial_logits = torch.linspace(2.2, -0.2, horizon)
        self.horizon_base_logits = nn.Parameter(initial_logits)

        # Context modulation network
        # Inputs: [recent_velocity, recent_accel, past_cgm_std_1h, future_insulin_sum, future_carbs_sum] (dim=5)
        self.context_net = nn.Sequential(
            nn.Linear(5, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, horizon)
        )
        # Small initialization so base decay dominates unless context is strong
        nn.init.zeros_(self.context_net[-1].weight)
        nn.init.zeros_(self.context_net[-1].bias)

    def forward(self, context_feat: torch.Tensor) -> torch.Tensor:
        """
        Args:
          context_feat: Tensor of shape (batch, 5)
        Returns:
          alpha: Tensor of shape (batch, 20) with values in (0, 1)
        """
        # (batch, 20)
        context_offset = self.context_net(context_feat)
        total_logits = self.horizon_base_logits.unsqueeze(0) + context_offset
        alpha = torch.sigmoid(total_logits)
        return alpha


class GlucoShieldHybridForecaster(nn.Module):
    """
    Unified Hybrid Forecasting Engine combining:
      1. Locked Data-Driven Neural Multi-Task Forecaster (GRU V1)
      2. Mechanistic Biomarker Prior Network
      3. 24-Hour Online Moving Horizon Calibrator
      4. Differentiable RK4 Digital Twin Forward Simulator
      5. Adaptive Context-Aware Fusion Gate
    """
    def __init__(
        self,
        neural_model: GlucoShieldMultiTaskRNN,
        freeze_neural: bool = True,
        calib_iterations: int = 15
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
        self.fusion_gate = AdaptiveFusionGate(horizon=20)
        self.residual_head = nn.Sequential(
            nn.Linear(20 + 9, 32),
            nn.ReLU(),
            nn.Linear(32, 20)
        )
        nn.init.zeros_(self.residual_head[-1].weight)
        nn.init.zeros_(self.residual_head[-1].bias)

    def compute_neural_uncertainty(
        self,
        dynamic_seq: torch.Tensor,
        static_feat: torch.Tensor,
        num_mc_samples: int = 8
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Computes MC-Dropout uncertainty for the neural forecaster trajectory.
        """
        # Temporarily enable dropout in neural model
        self.neural_model.train()
        preds = []
        with torch.no_grad():
            for _ in range(num_mc_samples):
                out = self.neural_model(dynamic_seq, static_feat)
                preds.append(out["trajectory"])
        self.neural_model.eval()

        # (samples, batch, 20)
        stacked = torch.stack(preds, dim=0)
        mean_traj = torch.mean(stacked, dim=0)
        std_traj = torch.std(stacked, dim=0)
        return mean_traj, std_traj

    def forward(
        self,
        dynamic_seq_scaled: torch.Tensor,   # (batch, 96, 22) scaled inputs for neural model
        dynamic_seq_raw: torch.Tensor,      # (batch, 96, 22) unscaled inputs for physics ODE
        static_feat_scaled: torch.Tensor,   # (batch, 9) scaled static features
        static_feat_raw: torch.Tensor,      # (batch, 9) raw static features
        future_insulin_raw: Optional[torch.Tensor] = None, # (batch, 20) in Units
        future_carbs_raw: Optional[torch.Tensor] = None,   # (batch, 20) in grams
        calibrate: bool = True,
        return_components: bool = False
    ) -> Dict[str, torch.Tensor]:
        """
        Executes end-to-end hybrid forecasting:
          1. Neural forecaster forward pass -> y_neural (batch, 20) & risk_probs (batch, 5)
          2. Static biomarker prior estimation -> params_prior
          3. 24h history MHE calibration -> params_calib, state_at_t0
          4. Forward ODE simulation -> y_ode (batch, 20)
          5. Adaptive fusion gating -> y_hybrid (batch, 20)
        """
        device = dynamic_seq_scaled.device
        batch_size = dynamic_seq_scaled.shape[0]

        # 1. Neural Forecast
        neural_out = self.neural_model(dynamic_seq_scaled, static_feat_scaled)
        y_neural = neural_out["trajectory"]        # (batch, 20)
        risk_probs = neural_out["risk_probs"]      # (batch, 5)
        risk_logits = neural_out["risk_logits"]    # (batch, 5)

        # 2. Physics Prior & Calibration
        params_prior = self.prior_net(static_feat_raw)
        
        if calibrate:
            params_calib, state_t0, calib_diag = self.calibrator.calibrate_and_observe(
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

        # 3. Forward Physics ODE Simulation
        # If future inputs are not explicitly supplied, assume zero future interventions (standard forecast)
        if future_insulin_raw is None:
            future_insulin_raw = torch.zeros(batch_size, 20, device=device)
        if future_carbs_raw is None:
            future_carbs_raw = torch.zeros(batch_size, 20, device=device)

        with torch.no_grad():
            y_ode, ode_states = self.integrator.forward_simulate(
                state_t0, future_insulin_raw, future_carbs_raw, params_calib
            ) # (batch, 20)

        # 4. Context Extraction for Fusion Gate
        # context: [recent_velocity (chan 1), recent_accel (chan 2), roll_std_1h (chan 4), future_ins_sum, future_carbs_sum]
        v_recent = dynamic_seq_raw[:, -1, 1]
        a_recent = dynamic_seq_raw[:, -1, 2]
        std_1h = dynamic_seq_raw[:, -1, 4]
        fut_ins_sum = torch.sum(future_insulin_raw, dim=-1)
        fut_carb_sum = torch.sum(future_carbs_raw, dim=-1)
        
        context_feat = torch.stack([
            v_recent * 0.1,
            a_recent * 0.1,
            std_1h * 0.05,
            fut_ins_sum * 0.1,
            fut_carb_sum * 0.01
        ], dim=-1)

        alpha = self.fusion_gate(context_feat) # (batch, 20) in (0, 1)

        # 5. Hybrid Combination
        y_hybrid = alpha * y_neural + (1.0 - alpha) * y_ode
        
        # Residual correction
        res_input = torch.cat([y_hybrid, static_feat_scaled], dim=-1)
        residual = self.residual_head(res_input)
        y_final = torch.clamp(y_hybrid + residual, min=20.0, max=500.0)

        result = {
            "trajectory": y_final,
            "risk_probs": risk_probs,
            "risk_logits": risk_logits,
            "alpha": alpha
        }

        if return_components:
            result.update({
                "y_neural": y_neural,
                "y_ode": y_ode,
                "y_hybrid_pre_res": y_hybrid,
                "residual": residual,
                "state_t0": state_t0,
                "params_calib": params_calib
            })

        return result
