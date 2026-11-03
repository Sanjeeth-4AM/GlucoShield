"""
GlucoShield V2 — Physiological Context Encoder
================================================
Encodes multi-modal physiological telemetry:
  1. Exercise / Physical Activity (MET, Heart Rate Reserve, Elapsed Time)
  2. Sleep Context (Duration, Efficiency, Deep Sleep %, Sleep Debt, Waking Decay)
  3. Hormonal Context (Menstrual Cycle Phase, Progesterone Proxy)
  4. Circadian Phase (Harmonic Trigonometric Basis)

Enforces strict causal boundaries and explicit missingness / validity masking:
  m_factor in {0, 1} guarantees zero-leakage and safe fallback when telemetry is absent.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from dataclasses import dataclass
from typing import Optional, Dict, Tuple

@dataclass
class PhysiologicalContextBatch:
    """
    Container for multi-modal physiological telemetry at forecast origin T0.
    """
    f_exercise: torch.Tensor    # (batch, 4): [log_met, hrr, exp_tau_ex, intensity_norm]
    m_exercise: torch.Tensor    # (batch, 1): {0.0, 1.0} validity mask
    f_sleep: torch.Tensor       # (batch, 5): [dur_norm, efficiency, deep_pct, debt_norm, psi_decay]
    m_sleep: torch.Tensor       # (batch, 1): {0.0, 1.0} validity mask
    f_hormonal: torch.Tensor    # (batch, 3): [is_follicular, is_luteal, prog_proxy]
    m_hormonal: torch.Tensor    # (batch, 1): {0.0, 1.0} validity mask
    f_circadian: torch.Tensor   # (batch, 4): [sin_24, cos_24, sin_12, cos_12]

    @classmethod
    def create_empty(cls, batch_size: int, device: torch.device = torch.device("cpu")) -> "PhysiologicalContextBatch":
        """Creates an all-missing neutral context batch (fallback for pure V1 behavior)."""
        return cls(
            f_exercise=torch.zeros(batch_size, 4, device=device),
            m_exercise=torch.zeros(batch_size, 1, device=device),
            f_sleep=torch.zeros(batch_size, 5, device=device),
            m_sleep=torch.zeros(batch_size, 1, device=device),
            f_hormonal=torch.zeros(batch_size, 3, device=device),
            m_hormonal=torch.zeros(batch_size, 1, device=device),
            f_circadian=torch.zeros(batch_size, 4, device=device)
        )

    def to(self, device: torch.device) -> "PhysiologicalContextBatch":
        return PhysiologicalContextBatch(
            f_exercise=self.f_exercise.to(device),
            m_exercise=self.m_exercise.to(device),
            f_sleep=self.f_sleep.to(device),
            m_sleep=self.m_sleep.to(device),
            f_hormonal=self.f_hormonal.to(device),
            m_hormonal=self.m_hormonal.to(device),
            f_circadian=self.f_circadian.to(device)
        )


class PhysiologicalContextEncoder(nn.Module):
    """
    Deep multi-modal context encoder mapping discrete and continuous physiological telemetry
    into a 32-dimensional patient context representation z_context.
    """
    def __init__(self, embed_dim: int = 32, dropout: float = 0.1):
        super().__init__()
        self.embed_dim = embed_dim

        # 1. Exercise Sub-Encoder (4 -> 16 -> 12)
        self.exercise_net = nn.Sequential(
            nn.Linear(4, 16),
            nn.LayerNorm(16),
            nn.ReLU(),
            nn.Dropout(dropout * 0.5),
            nn.Linear(16, 12)
        )

        # 2. Sleep Sub-Encoder (5 -> 16 -> 12)
        self.sleep_net = nn.Sequential(
            nn.Linear(5, 16),
            nn.LayerNorm(16),
            nn.ReLU(),
            nn.Dropout(dropout * 0.5),
            nn.Linear(16, 12)
        )

        # 3. Hormonal Sub-Encoder (3 -> 12 -> 8)
        self.hormonal_net = nn.Sequential(
            nn.Linear(3, 12),
            nn.LayerNorm(12),
            nn.ReLU(),
            nn.Dropout(dropout * 0.5),
            nn.Linear(12, 8)
        )

        # 4. Circadian Sub-Encoder (4 -> 8)
        self.circadian_net = nn.Sequential(
            nn.Linear(4, 8),
            nn.LayerNorm(8),
            nn.ReLU()
        )

        # 5. Context Bottleneck Fusion (12 + 12 + 8 + 8 + 3 = 43 -> embed_dim)
        raw_context_dim = 12 + 12 + 8 + 8 + 3
        self.bottleneck = nn.Sequential(
            nn.Linear(raw_context_dim, embed_dim),
            nn.LayerNorm(embed_dim),
            nn.GELU(),
            nn.Dropout(dropout)
        )

    def forward(self, context_batch: PhysiologicalContextBatch) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
        """
        Forward pass with strict validity masking.
        Args:
            context_batch: PhysiologicalContextBatch
        Returns:
            z_context: Tensor of shape (batch, embed_dim)
            domain_embeds: Dict containing individual factor embeddings
        """
        # 1. Compute factor embeddings with mask gating
        # Ensure float32 dtype for all factor tensors
        f_ex = context_batch.f_exercise.float()
        m_ex = context_batch.m_exercise.float()
        f_sl = context_batch.f_sleep.float()
        m_sl = context_batch.m_sleep.float()
        f_hm = context_batch.f_hormonal.float()
        m_hm = context_batch.m_hormonal.float()
        f_circ = context_batch.f_circadian.float()

        # If mask is 0.0, embedding is strictly identical to zero
        e_ex = m_ex * self.exercise_net(f_ex)
        e_sl = m_sl * self.sleep_net(f_sl)
        e_hm = m_hm * self.hormonal_net(f_hm)
        e_circ = self.circadian_net(f_circ)

        # 2. Concatenate embeddings with explicit missingness masks
        raw_concat = torch.cat([
            e_ex, e_sl, e_hm, e_circ,
            m_ex,
            m_sl,
            m_hm
        ], dim=-1)

        # 3. Project through bottleneck
        z_context = self.bottleneck(raw_concat)

        domain_embeds = {
            "exercise": e_ex,
            "sleep": e_sl,
            "hormonal": e_hm,
            "circadian": e_circ,
            "masks": torch.cat([context_batch.m_exercise, context_batch.m_sleep, context_batch.m_hormonal], dim=-1)
        }

        return z_context, domain_embeds
