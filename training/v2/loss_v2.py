"""
GlucoShield V2 — Structured Multi-Task Loss Engine
===================================================
Formulates:
  L_total = lambda_traj * L_traj + lambda_risk * L_risk + lambda_quant * L_quant + lambda_phys * L_phys

Loss Components:
  1. L_traj: Smooth Huber Loss (beta = 5.0 mg/dL) on 20-step continuous future glucose
  2. L_risk: Weighted BCE with Logits across 5 acute clinical risks
  3. L_quant: Multi-quantile pinball loss for [q0.025, q0.100, q0.900, q0.975]
  4. L_phys: Physics consistency regularization (optional, for ablation E5/E6)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Tuple, Optional

class GlucoShieldLossV2(nn.Module):
    """
    Multi-objective loss engine supporting controlled ablation experiments L0 through L4.
    """
    def __init__(
        self,
        lambda_traj: float = 1.0,
        lambda_risk: float = 5.0,
        lambda_quant: float = 0.5,
        lambda_phys: float = 0.05,
        huber_beta: float = 5.0,
        quantiles: Tuple[float, ...] = (0.025, 0.100, 0.900, 0.975),
        pos_weights: Optional[torch.Tensor] = None
    ):
        super().__init__()
        self.lambda_traj = lambda_traj
        self.lambda_risk = lambda_risk
        self.lambda_quant = lambda_quant
        self.lambda_phys = lambda_phys
        self.quantiles = quantiles

        self.traj_crit = nn.SmoothL1Loss(beta=huber_beta)
        if pos_weights is not None:
            self.risk_crit = nn.BCEWithLogitsLoss(pos_weight=pos_weights)
        else:
            self.risk_crit = nn.BCEWithLogitsLoss()

    def pinball_loss(self, quant_preds: torch.Tensor, y_true: torch.Tensor) -> torch.Tensor:
        """
        Computes average pinball loss across the 4 pre-registered quantiles.
        quant_preds: (batch, 4, 20)
        y_true: (batch, 20)
        """
        loss = 0.0
        y_expanded = y_true.unsqueeze(1) # (batch, 1, 20)
        
        for i, tau in enumerate(self.quantiles):
            err = y_expanded[:, 0, :] - quant_preds[:, i, :] # (batch, 20)
            tau_loss = torch.max(tau * err, (tau - 1.0) * err)
            loss = loss + torch.mean(tau_loss)
            
        return loss / len(self.quantiles)

    def forward(
        self,
        traj_pred: torch.Tensor,                                    # (batch, 20)
        traj_true: torch.Tensor,                                    # (batch, 20)
        risk_logits: Optional[torch.Tensor] = None,                 # (batch, 5)
        risk_true: Optional[torch.Tensor] = None,                   # (batch, 5)
        quant_preds: Optional[torch.Tensor] = None,                 # (batch, 4, 20)
        ode_pred: Optional[torch.Tensor] = None,                    # (batch, 20)
        alpha: Optional[torch.Tensor] = None                        # (batch, 20)
    ) -> Dict[str, torch.Tensor]:
        """
        Computes composite loss and individual components.
        """
        # 1. Trajectory Huber Loss
        l_traj = self.traj_crit(traj_pred, traj_true)
        total_loss = self.lambda_traj * l_traj

        # 2. Acute Risk BCE Loss
        if risk_logits is not None and risk_true is not None and self.lambda_risk > 0:
            l_risk = self.risk_crit(risk_logits, risk_true)
            total_loss = total_loss + self.lambda_risk * l_risk
        else:
            l_risk = torch.tensor(0.0, device=traj_pred.device)

        # 3. Pinball Quantile Loss
        if quant_preds is not None and self.lambda_quant > 0:
            l_quant = self.pinball_loss(quant_preds, traj_true)
            total_loss = total_loss + self.lambda_quant * l_quant
        else:
            l_quant = torch.tensor(0.0, device=traj_pred.device)

        # 4. Physics Consistency Regularization
        if ode_pred is not None and alpha is not None and self.lambda_phys > 0:
            # Penalize discrepancy between hybrid prediction and physics ODE weighted by physics contribution (1 - alpha)
            phys_weight = (1.0 - alpha).detach()
            l_phys = torch.mean(phys_weight * (traj_pred - ode_pred)**2)
            total_loss = total_loss + self.lambda_phys * l_phys
        else:
            l_phys = torch.tensor(0.0, device=traj_pred.device)

        return {
            "total_loss": total_loss,
            "loss_traj": l_traj,
            "loss_risk": l_risk,
            "loss_quant": l_quant,
            "loss_phys": l_phys
        }
