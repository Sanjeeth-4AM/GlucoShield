"""
GlucoShield Decision Engine - Uncertainty Estimation & Prediction Intervals
===========================================================================
Computes calibrated epistemic uncertainty via MC-Dropout, model divergence,
and constructs 80% and 95% physical prediction intervals.
"""

import torch
import numpy as np
from dataclasses import dataclass
from typing import Dict, Tuple, Optional
from neural.models import GlucoShieldMultiTaskRNN

@dataclass
class PredictionInterval:
    """Holds point prediction and calibrated uncertainty bounds across 20 horizon steps."""
    point_forecast: np.ndarray      # (20,) [mg/dL]
    std_uncertainty: np.ndarray     # (20,) [mg/dL]
    lower_80: np.ndarray            # (20,) [mg/dL]
    upper_80: np.ndarray            # (20,) [mg/dL]
    lower_95: np.ndarray            # (20,) [mg/dL]
    upper_95: np.ndarray            # (20,) [mg/dL]
    epistemic_neural_std: np.ndarray# (20,) [mg/dL]
    model_disagreement_std: np.ndarray # (20,) [mg/dL]


class UncertaintyEstimator:
    """
    Estimates multi-source uncertainty:
      1. Epistemic uncertainty in neural temporal pattern matching (MC-Dropout)
      2. Mechanistic vs statistical model disagreement
      3. Aleatoric physiological sensor noise growth over horizon
    """
    def __init__(self, num_mc_samples: int = 16):
        self.num_mc_samples = num_mc_samples

    def estimate_mc_dropout(
        self,
        neural_model: GlucoShieldMultiTaskRNN,
        dynamic_seq_s: torch.Tensor,
        static_feat_s: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Runs stochastic forward passes with dropout enabled to capture epistemic variance.
        """
        was_training = neural_model.training
        neural_model.train() # enable dropout
        
        preds = []
        with torch.no_grad():
            for _ in range(self.num_mc_samples):
                out = neural_model(dynamic_seq_s, static_feat_s)
                preds.append(out["trajectory"])
                
        neural_model.train(was_training)
        
        stacked = torch.stack(preds, dim=0) # (samples, batch, 20)
        mean_traj = torch.mean(stacked, dim=0)
        std_traj = torch.std(stacked, dim=0)
        return mean_traj, std_traj

    def construct_prediction_intervals(
        self,
        y_hybrid: np.ndarray,          # (20,) or (batch, 20)
        y_neural: np.ndarray,          # (20,) or (batch, 20)
        y_ode: np.ndarray,             # (20,) or (batch, 20)
        sigma_neural: np.ndarray       # (20,) or (batch, 20)
    ) -> PredictionInterval:
        """
        Constructs physically bounded 80% and 95% prediction intervals.
        """
        # 1. Epistemic model disagreement: |y_neural - y_ode| / 2.0
        sigma_disagree = np.abs(y_neural - y_ode) * 0.35

        # 2. Base physiological & sensor diffusion noise growing with horizon k (k=1..20)
        horizon_steps = np.arange(1, y_hybrid.shape[-1] + 1)
        sigma_aleatoric = 6.0 + 0.65 * horizon_steps # 6.65 mg/dL at 15m -> 19.0 mg/dL at 5h

        # 3. Total combined variance: sqrt(sigma_mc^2 + sigma_disagree^2 + sigma_aleatoric^2)
        sigma_total = np.sqrt(sigma_neural**2 + sigma_disagree**2 + sigma_aleatoric**2)

        # 4. Standard normal z-scores: z_80 = 1.282, z_95 = 1.960
        lower_80 = np.clip(y_hybrid - 1.282 * sigma_total, 20.0, 500.0)
        upper_80 = np.clip(y_hybrid + 1.282 * sigma_total, 20.0, 500.0)
        lower_95 = np.clip(y_hybrid - 1.960 * sigma_total, 20.0, 500.0)
        upper_95 = np.clip(y_hybrid + 1.960 * sigma_total, 20.0, 500.0)

        return PredictionInterval(
            point_forecast=y_hybrid,
            std_uncertainty=sigma_total,
            lower_80=lower_80,
            upper_80=upper_80,
            lower_95=lower_95,
            upper_95=upper_95,
            epistemic_neural_std=sigma_neural,
            model_disagreement_std=sigma_disagree
        )
