"""
GlucoShield V2 — Factor-Aware Adaptive Physics Fusion Gate
===========================================================
Dynamically computes blending weights alpha(k) in (0, 1) across the 20-step horizon,
conditioning on:
  1. Recent glycemic kinematics (velocity, acceleration, trailing 1h volatility)
  2. Active metabolic interventions (future insulin and meal sums)
  3. Physiological Context Energy (magnitude of factor embedding z_context)
  4. Epistemic Model Disagreement (|y_neural - y_ode|)
  5. Domain-specific factor activity (active exercise, active sleep debt)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Tuple, Optional

class FactorAwareFusionGate(nn.Module):
    """
    Context-aware, factor-conditioned fusion gate that dynamically balances
    data-driven neural representations and mechanistic Digital Twin simulations.
    """
    def __init__(self, horizon: int = 20, hidden_dim: int = 32):
        super().__init__()
        self.horizon = horizon
        self.context_dim = 10

        # Horizon baseline logits: initialized to balanced starting blend
        # alpha_0 ~ 0.75 at k=1 (logit ~ +1.1), alpha_0 ~ 0.50 at k=20 (logit ~ 0.0)
        # Avoids V1's excessive initial bias of +2.2 (90%+)
        initial_logits = torch.linspace(1.1, 0.0, horizon)
        self.horizon_base_logits = nn.Parameter(initial_logits)

        # Context modulation network (10 -> hidden_dim -> horizon)
        self.context_net = nn.Sequential(
            nn.Linear(self.context_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.05),
            nn.Linear(hidden_dim, horizon)
        )
        # Small weight initialization for smooth gradient flow
        nn.init.normal_(self.context_net[-1].weight, std=0.01)
        nn.init.zeros_(self.context_net[-1].bias)

    def extract_gating_features(
        self,
        dynamic_seq_raw: torch.Tensor,    # (batch, 96, 22)
        y_neural: torch.Tensor,            # (batch, 20)
        y_ode: torch.Tensor,               # (batch, 20)
        z_context: torch.Tensor,           # (batch, 32)
        future_ins: torch.Tensor,          # (batch, 20)
        future_carbs: torch.Tensor,        # (batch, 20)
        factor_masks: Optional[torch.Tensor] = None # (batch, 3) [m_ex, m_sl, m_hm]
    ) -> torch.Tensor:
        """
        Builds the 10-dimensional gating context vector phi_gate.
        """
        v_recent = dynamic_seq_raw[:, -1, 1]
        a_recent = dynamic_seq_raw[:, -1, 2]
        std_1h = dynamic_seq_raw[:, -1, 4]
        
        fut_ins_sum = torch.sum(future_ins, dim=-1)
        fut_carb_sum = torch.sum(future_carbs, dim=-1)
        
        # Factor energy: norm of physiological context embedding
        factor_energy = torch.norm(z_context, p=2, dim=-1)
        
        # Model disagreement: mean absolute difference between neural and ODE trajectories
        disagreement = torch.mean(torch.abs(y_neural - y_ode), dim=-1)
        
        # Glycemic volatility index
        volatility_idx = std_1h + torch.abs(v_recent)
        
        # Factor activity indicators
        if factor_masks is not None:
            m_ex = factor_masks[:, 0]
            m_sl = factor_masks[:, 1]
        else:
            m_ex = torch.zeros_like(v_recent)
            m_sl = torch.zeros_like(v_recent)

        phi_gate = torch.stack([
            v_recent * 0.1,             # 1. Glycemic velocity
            a_recent * 0.1,             # 2. Glycemic acceleration
            std_1h * 0.05,              # 3. Trailing volatility
            fut_ins_sum * 0.1,          # 4. Insulin interventions
            fut_carb_sum * 0.01,        # 5. Meal interventions
            factor_energy * 0.1,        # 6. Physiological context magnitude
            disagreement * 0.05,        # 7. Mechanistic-neural divergence
            volatility_idx * 0.05,      # 8. Combined volatility index
            m_ex * 1.0,                 # 9. Exercise activity mask
            m_sl * 1.0                  # 10. Sleep activity mask
        ], dim=-1)

        return phi_gate

    def forward(self, phi_gate: torch.Tensor) -> torch.Tensor:
        """
        Args:
            phi_gate: Tensor of shape (batch, 10)
        Returns:
            alpha: Tensor of shape (batch, 20) with values in (0, 1)
        """
        context_offset = self.context_net(phi_gate)
        total_logits = self.horizon_base_logits.unsqueeze(0) + context_offset
        alpha = torch.sigmoid(total_logits)
        return alpha
