"""
GlucoShield V2 — Physics-Aware, Regime-Conditioned Uncertainty Estimator
========================================================================
Solves the V1 uncertainty calibration collapse on high-variance outpatients by
replacing the static linear heuristic with a multi-source, regime-conditioned
uncertainty formulation.

Quantifies:
  1. Epistemic uncertainty from neural quantile spread
  2. Model divergence between neural and mechanistic ODE predictions
  3. Glycemic regime volatility (trailing 1h standard deviation, glucose rate of change)
  4. Active physiological context perturbation (exercise / sleep debt)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class PredictionIntervalV2:
    """Holds point prediction, total uncertainty, and calibrated physical intervals."""
    point_forecast: torch.Tensor        # (batch, 20) [mg/dL]
    std_uncertainty: torch.Tensor       # (batch, 20) [mg/dL]
    lower_80: torch.Tensor              # (batch, 20) [mg/dL]
    upper_80: torch.Tensor              # (batch, 20) [mg/dL]
    lower_95: torch.Tensor              # (batch, 20) [mg/dL]
    upper_95: torch.Tensor              # (batch, 20) [mg/dL]
    sigma_epistemic: torch.Tensor       # (batch, 20) [mg/dL]
    sigma_disagree: torch.Tensor        # (batch, 20) [mg/dL]
    sigma_regime: torch.Tensor          # (batch, 20) [mg/dL]


class RegimeConditionedUncertaintyHead(nn.Module):
    """
    Dynamic uncertainty estimation engine that scales confidence bands based on
    glycemic volatility, rate-of-change kinematics, and physiological state.
    """
    def __init__(self, horizon: int = 20):
        super().__init__()
        self.horizon = horizon

        # Learnable regime-conditioning parameters (initialized to physiologically grounded values)
        # sigma_base ~ 8.0 mg/dL (base sensor noise)
        self.log_sigma_base = nn.Parameter(torch.tensor(np.log(8.0), dtype=torch.float32))
        
        # Volatility sensitivities: gamma_1 (std_1h), gamma_2 (|velocity|), gamma_3 (context)
        self.log_gamma_std = nn.Parameter(torch.tensor(np.log(0.40), dtype=torch.float32))
        self.log_gamma_vel = nn.Parameter(torch.tensor(np.log(1.50), dtype=torch.float32))
        self.log_gamma_ctx = nn.Parameter(torch.tensor(np.log(0.20), dtype=torch.float32))
        
        # Disagreement scaling beta
        self.log_beta_dis = nn.Parameter(torch.tensor(np.log(0.35), dtype=torch.float32))
        
        # Horizon growth parameter kappa (growth factor across 5 hours)
        self.log_kappa = nn.Parameter(torch.tensor(np.log(1.20), dtype=torch.float32))

    def forward(
        self,
        y_final: torch.Tensor,              # (batch, 20) final hybrid point prediction
        y_neural: torch.Tensor,             # (batch, 20) neural point prediction
        y_ode: torch.Tensor,                # (batch, 20) ODE point prediction
        quantiles: Optional[torch.Tensor],  # (batch, 4, 20): [q025, q10, q90, q975]
        dynamic_seq_raw: torch.Tensor,      # (batch, 96, 22)
        z_context: torch.Tensor             # (batch, 32)
    ) -> PredictionIntervalV2:
        """
        Computes calibrated 80% and 95% physical prediction intervals.
        """
        device = y_final.device
        batch_size = y_final.shape[0]

        # 1. Epistemic Uncertainty from Neural Quantiles
        if quantiles is not None:
            # (q90 - q10) / (2 * 1.282) captures the standard deviation of the central 80% distribution
            q100 = quantiles[:, 1, :]
            q900 = quantiles[:, 2, :]
            sigma_epistemic = torch.clamp((q900 - q100) / (2.0 * 1.282), min=1.0, max=100.0)
        else:
            sigma_epistemic = torch.full_like(y_final, 5.0)

        # 2. Mechanistic-Statistical Disagreement
        beta_dis = torch.exp(self.log_beta_dis)
        sigma_disagree = beta_dis * torch.abs(y_neural - y_ode)

        # 3. Regime-Conditioned Aleatoric Volatility
        sigma_base = torch.exp(self.log_sigma_base)
        gamma_std = torch.exp(self.log_gamma_std)
        gamma_vel = torch.exp(self.log_gamma_vel)
        gamma_ctx = torch.exp(self.log_gamma_ctx)
        kappa = torch.exp(self.log_kappa)

        v_recent = torch.abs(dynamic_seq_raw[:, -1, 1]) # (batch,)
        std_1h = dynamic_seq_raw[:, -1, 4]              # (batch,)
        ctx_norm = torch.norm(z_context, p=2, dim=-1)   # (batch,)

        # Scalar regime standard deviation at T0 per patient
        sigma_regime_t0 = sigma_base + gamma_std * std_1h + gamma_vel * v_recent + gamma_ctx * ctx_norm # (batch,)

        # Horizon growth factor: (1.0 + kappa * k / 20)
        horizon_steps = torch.linspace(0.05, 1.0, self.horizon, device=device).unsqueeze(0) # (1, 20)
        horizon_growth = 1.0 + kappa * horizon_steps # (1, 20)

        sigma_regime = sigma_regime_t0.unsqueeze(-1) * horizon_growth # (batch, 20)

        # 4. Total Multi-Source Standard Deviation
        sigma_total_sq = sigma_epistemic**2 + sigma_disagree**2 + sigma_regime**2
        sigma_total = torch.sqrt(torch.clamp(sigma_total_sq, min=4.0)) # (batch, 20)

        # 5. Calibrated Physical Bounds [20.0, 500.0] mg/dL
        lower_80 = torch.clamp(y_final - 1.282 * sigma_total, min=20.0, max=500.0)
        upper_80 = torch.clamp(y_final + 1.282 * sigma_total, min=20.0, max=500.0)
        lower_95 = torch.clamp(y_final - 1.960 * sigma_total, min=20.0, max=500.0)
        upper_95 = torch.clamp(y_final + 1.960 * sigma_total, min=20.0, max=500.0)

        return PredictionIntervalV2(
            point_forecast=y_final,
            std_uncertainty=sigma_total,
            lower_80=lower_80,
            upper_80=upper_80,
            lower_95=lower_95,
            upper_95=upper_95,
            sigma_epistemic=sigma_epistemic,
            sigma_disagree=sigma_disagree,
            sigma_regime=sigma_regime
        )
