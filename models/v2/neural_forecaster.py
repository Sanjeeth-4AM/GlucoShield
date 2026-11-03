"""
GlucoShield V2 — Factor-Aware Temporal Neural Forecaster
=========================================================
Extends the V1 Recurrent Neural Forecaster with:
  1. Multi-modal Physiological Context Integration (Exercise, Sleep, Hormones, Circadian)
  2. Multi-Task Trajectory Forecasting (20-step continuous future glucose)
  3. Direct Non-Parametric Quantile Regression Heads (q0.025, q0.100, q0.900, q0.975)
  4. Acute Clinical Risk Prediction (5 binary hazard logits)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, Dict, Tuple

from neural.models import MealTransformLayer, StaticPatientEncoder
from models.v2.context_encoder import PhysiologicalContextEncoder, PhysiologicalContextBatch

class GlucoShieldNeuralForecasterV2(nn.Module):
    """
    V2 Neural Forecaster incorporating explicit physiological context representation.
    """
    def __init__(
        self,
        dynamic_dim: int = 22,
        static_dim: int = 9,
        hidden_dim: int = 128,
        num_layers: int = 2,
        dropout: float = 0.2,
        static_embed_dim: int = 16,
        context_embed_dim: int = 32,
        horizon: int = 20,
        meal_c_max: float = 200.0
    ):
        super().__init__()
        self.dynamic_dim = dynamic_dim
        self.static_dim = static_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.horizon = horizon

        # 1. Meal Preprocessor (V1 compatible)
        self.meal_transform = MealTransformLayer(c_max=meal_c_max)

        # 2. Dynamic Input Projection
        self.input_proj = nn.Sequential(
            nn.Linear(dynamic_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout * 0.5)
        )

        # 3. Recurrent Sequence Encoder (2-layer GRU)
        self.rnn = nn.GRU(
            input_size=hidden_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0
        )

        # 4. Static Patient Context Encoder
        self.static_encoder = StaticPatientEncoder(
            static_dim=static_dim, embed_dim=static_embed_dim, dropout=dropout
        )

        # 5. Multi-Modal Context Encoder (Exercise, Sleep, Hormones, Circadian)
        self.context_encoder = PhysiologicalContextEncoder(
            embed_dim=context_embed_dim, dropout=dropout
        )

        # 6. Unified Fusion Layer: [h_temporal (128) + z_context (32) + static_rep (16)] -> 176 -> 128
        fused_in_dim = hidden_dim + context_embed_dim + static_embed_dim
        self.fusion = nn.Sequential(
            nn.Linear(fused_in_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout)
        )

        # 7. Output Heads
        # Head A: Trajectory Forecaster (20 continuous future steps)
        self.trajectory_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, horizon)
        )

        # Head B: Multi-Quantile Head (4 quantiles x 20 steps: q0.025, q0.100, q0.900, q0.975)
        self.quantile_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 4 * horizon)
        )

        # Head C: Acute Risk Classification Head (5 clinical risk logits)
        self.risk_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 5)
        )

    def forward(
        self,
        dynamic_seq: torch.Tensor,                                      # (batch, 96, 22)
        static_feat: torch.Tensor,                                       # (batch, 9)
        context_batch: Optional[PhysiologicalContextBatch] = None       # Multi-modal context
    ) -> Dict[str, torch.Tensor]:
        """
        Forward pass executing factor-aware multi-task forecasting.
        """
        batch_size, seq_len, _ = dynamic_seq.shape
        device = dynamic_seq.device
        assert seq_len == 96, f"Expected dynamic sequence length 96, got {seq_len}"

        # Default to empty context if not supplied
        if context_batch is None:
            context_batch = PhysiologicalContextBatch.create_empty(batch_size, device=device)
        else:
            context_batch = context_batch.to(device)

        # 1. Meal transform & input projection
        x = self.meal_transform(dynamic_seq)
        x = self.input_proj(x)

        # 2. Recurrent temporal encoding
        _, h_last = self.rnn(x)
        h_temporal = h_last[-1] # (batch, hidden_dim)

        # 3. Static clinical encoding
        static_rep = self.static_encoder(static_feat) # (batch, static_embed_dim)

        # 4. Physiological context encoding
        z_context, factor_embeds = self.context_encoder(context_batch) # (batch, context_embed_dim)

        # 5. Multi-modal patient state fusion
        fused = torch.cat([h_temporal, z_context, static_rep], dim=-1)
        z_patient = self.fusion(fused) # (batch, hidden_dim)

        # 6. Heads
        y_traj = self.trajectory_head(z_patient) # (batch, 20)
        
        quant_raw = self.quantile_head(z_patient).view(batch_size, 4, self.horizon) # (batch, 4, 20)
        # Ensure monotonic ordering: q025 <= q10 <= q90 <= q975 via positive offsets
        q025 = quant_raw[:, 0, :]
        q100 = q025 + F.softplus(quant_raw[:, 1, :])
        q900 = q100 + F.softplus(quant_raw[:, 2, :])
        q975 = q900 + F.softplus(quant_raw[:, 3, :])
        quantiles = torch.stack([q025, q100, q900, q975], dim=1) # (batch, 4, 20)

        risk_logits = self.risk_head(z_patient) # (batch, 5)
        risk_probs = torch.sigmoid(risk_logits)

        return {
            "trajectory": y_traj,
            "quantiles": quantiles,
            "risk_logits": risk_logits,
            "risk_probs": risk_probs,
            "z_context": z_context,
            "z_patient": z_patient,
            "factor_embeds": factor_embeds
        }
