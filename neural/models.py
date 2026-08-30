"""
GlucoShield Neural Architecture Module
Provides modular, multi-task GRU and LSTM neural forecasters with static patient context fusion.
"""

import os
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

class MealTransformLayer(nn.Module):
    """
    Applies configurable physiological saturation and non-linear log-scaling to carb channels.
    """
    def __init__(self, c_max=200.0, carb_indices=(17, 19, 21)):
        super().__init__()
        self.c_max = c_max
        self.carb_indices = list(carb_indices)

    def forward(self, x):
        """
        Args:
            x: Tensor of shape (batch, seq_len, 22)
        """
        if self.c_max is None or self.c_max <= 0:
            return x
        
        # Clone tensor to avoid in-place mutation
        x_out = x.clone()
        for idx in self.carb_indices:
            # Bound and log-transform: log1p(min(c, c_max))
            carb_chan = x_out[:, :, idx]
            bounded = torch.clamp(carb_chan, min=0.0, max=float(self.c_max))
            x_out[:, :, idx] = torch.log1p(bounded)
        return x_out


class StaticPatientEncoder(nn.Module):
    """
    Encodes static clinical biomarkers (Age, BMI, HbA1c, C-peptide, etc.) into a dense embedding.
    """
    def __init__(self, static_dim=9, embed_dim=32, dropout=0.1):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(static_dim, embed_dim),
            nn.LayerNorm(embed_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(embed_dim, embed_dim),
            nn.LayerNorm(embed_dim),
            nn.ReLU()
        )

    def forward(self, static_x):
        return self.net(static_x)


class GlucoShieldMultiTaskRNN(nn.Module):
    """
    Core Neural Multi-Task Forecaster supporting GRU and LSTM backbones.
    Predicts 20-step continuous glucose trajectory and 5 acute clinical risk logits.
    """
    def __init__(
        self,
        cell_type="gru",          # 'gru' or 'lstm'
        dynamic_dim=22,
        static_dim=9,
        hidden_dim=128,
        num_layers=2,
        dropout=0.2,
        static_embed_dim=32,
        use_static=True,
        meal_c_max=200.0,
        horizon=20,
        residual_target=False      # If True, predicts delta from current glucose
    ):
        super().__init__()
        self.cell_type = cell_type.lower()
        self.dynamic_dim = dynamic_dim
        self.static_dim = static_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.use_static = use_static
        self.horizon = horizon
        self.residual_target = residual_target

        # 1. Meal Preprocessor
        self.meal_transform = MealTransformLayer(c_max=meal_c_max)

        # 2. Dynamic Input Projection
        self.input_proj = nn.Sequential(
            nn.Linear(dynamic_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout * 0.5)
        )

        # 3. Recurrent Sequence Encoder
        rnn_dropout = dropout if num_layers > 1 else 0.0
        if self.cell_type == "gru":
            self.rnn = nn.GRU(
                input_size=hidden_dim,
                hidden_size=hidden_dim,
                num_layers=num_layers,
                batch_first=True,
                dropout=rnn_dropout
            )
        elif self.cell_type == "lstm":
            self.rnn = nn.LSTM(
                input_size=hidden_dim,
                hidden_size=hidden_dim,
                num_layers=num_layers,
                batch_first=True,
                dropout=rnn_dropout
            )
        else:
            raise ValueError(f"Unknown cell_type: {cell_type}")

        # 4. Static Patient Context Encoder
        if self.use_static and static_dim > 0:
            self.static_encoder = StaticPatientEncoder(static_dim=static_dim, embed_dim=static_embed_dim, dropout=dropout)
            fusion_input_dim = hidden_dim + static_embed_dim
        else:
            self.static_encoder = None
            fusion_input_dim = hidden_dim

        # 5. Shared Fusion Layer
        self.fusion = nn.Sequential(
            nn.Linear(fusion_input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout)
        )

        # 6. Output Heads
        # Head A: Trajectory Forecaster (20 continuous future steps)
        self.trajectory_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, horizon)
        )

        # Head B: Acute Risk Classification Heads (5 binary clinical risks)
        # Logits for: [hypo_1h, hypo_2h, hypo_4h, hyper_2h, hyper_4h]
        self.risk_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 5)
        )

    def forward(self, dynamic_seq, static_feat=None):
        """
        Args:
            dynamic_seq: Tensor of shape (batch, 96, 22)
            static_feat: Tensor of shape (batch, 9)
        Returns:
            out_dict: {
                'trajectory': Tensor of shape (batch, 20),
                'risk_logits': Tensor of shape (batch, 5),
                'risk_probs': Tensor of shape (batch, 5)
            }
        """
        batch_size, seq_len, _ = dynamic_seq.shape

        # Extract current raw glucose (feature 0 at timestep -1)
        curr_glucose = dynamic_seq[:, -1, 0]  # shape (batch,)

        # 1. Apply meal transform
        x = self.meal_transform(dynamic_seq)

        # 2. Input projection
        x = self.input_proj(x)

        # 3. Recurrent encoder
        if self.cell_type == "gru":
            _, h_last = self.rnn(x)
            seq_rep = h_last[-1]  # top layer last hidden state (batch, hidden_dim)
        else:
            _, (h_last, _) = self.rnn(x)
            seq_rep = h_last[-1]

        # 4. Static fusion
        if self.use_static and self.static_encoder is not None and static_feat is not None:
            static_rep = self.static_encoder(static_feat)
            fused = torch.cat([seq_rep, static_rep], dim=-1)
        else:
            fused = seq_rep

        latent = self.fusion(fused)

        # 5. Compute heads
        traj_out = self.trajectory_head(latent)
        if self.residual_target:
            traj_out = traj_out + curr_glucose.unsqueeze(-1)

        risk_logits = self.risk_head(latent)
        risk_probs = torch.sigmoid(risk_logits)

        return {
            "trajectory": traj_out,
            "risk_logits": risk_logits,
            "risk_probs": risk_probs
        }
