"""
GlucoShield Phase 13 — Disagreement-Attenuated Fusion Gate
==========================================================
Implements a smooth, deterministic disagreement-conditioned gating mechanism
that enforces a global physics ceiling and attenuates physics authority
when the neural and ODE predictions diverge.

Governance:
  - Does NOT alter V1 or V2 weights.
  - Does NOT alter Hovorka ODE equations.
  - Zero retraining required.
"""

import torch
import torch.nn as nn
import numpy as np
from typing import Union, Tuple, Dict, Any

class DisagreementAttenuatedFusionGate(nn.Module):
    """
    Smooth, deterministic disagreement-attenuated fusion gate.
    
    Parameters:
      ceiling (float): Global ceiling on physics contribution (e.g. 0.40).
                       Ensures 1 - alpha_eff <= ceiling <=> alpha_eff >= 1 - ceiling.
      d_mid (float): Disagreement midpoint in mg/dL (e.g. 35.0 mg/dL).
      tau (float): Transition smoothness scale in mg/dL (e.g. 5.0 mg/dL).
      w_high (float): Maximum allowed physics contribution under extreme disagreement (e.g. 0.20).
    """
    def __init__(self, ceiling: float = 0.40, d_mid: float = 35.0, tau: float = 5.0, w_high: float = 0.20):
        super().__init__()
        assert 0.0 < ceiling <= 1.0, "Ceiling must be in (0, 1]"
        assert d_mid > 0.0, "d_mid must be positive"
        assert tau > 0.0, "tau must be positive"
        assert 0.0 <= w_high <= ceiling, "w_high must be <= ceiling"
        
        self.ceiling = float(ceiling)
        self.d_mid = float(d_mid)
        self.tau = float(tau)
        self.w_high = float(w_high)

    def compute_effective_weights(
        self,
        y_neural: Union[torch.Tensor, np.ndarray],
        y_ode: Union[torch.Tensor, np.ndarray],
        alpha_raw: Union[torch.Tensor, np.ndarray]
    ) -> Tuple[Union[torch.Tensor, np.ndarray], Union[torch.Tensor, np.ndarray], Union[torch.Tensor, np.ndarray]]:
        """
        Computes effective neural weight (alpha_eff), effective physics weight (w_phys),
        and point-wise disagreement (D).
        """
        is_torch = isinstance(y_neural, torch.Tensor)
        
        if is_torch:
            D = torch.abs(y_neural - y_ode)
            w_raw = 1.0 - alpha_raw
            w_capped = torch.clamp(w_raw, max=self.ceiling)
            g = torch.sigmoid((D - self.d_mid) / self.tau)
            w_target_high = torch.clamp(w_capped, max=self.w_high)
            w_phys = w_capped * (1.0 - g) + w_target_high * g
            alpha_eff = 1.0 - w_phys
            # Strict safety bounds
            alpha_eff = torch.clamp(alpha_eff, min=1.0 - self.ceiling, max=1.0)
            w_phys = 1.0 - alpha_eff
        else:
            D = np.abs(y_neural - y_ode)
            w_raw = 1.0 - alpha_raw
            w_capped = np.minimum(w_raw, self.ceiling)
            g = 1.0 / (1.0 + np.exp(-np.clip((D - self.d_mid) / self.tau, -20.0, 20.0)))
            w_target_high = np.minimum(w_capped, self.w_high)
            w_phys = w_capped * (1.0 - g) + w_target_high * g
            alpha_eff = 1.0 - w_phys
            alpha_eff = np.clip(alpha_eff, 1.0 - self.ceiling, 1.0)
            w_phys = 1.0 - alpha_eff
            
        return alpha_eff, w_phys, D

    def blend(
        self,
        y_neural: Union[torch.Tensor, np.ndarray],
        y_ode: Union[torch.Tensor, np.ndarray],
        alpha_raw: Union[torch.Tensor, np.ndarray],
        residual: Union[torch.Tensor, np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        Blends neural and ODE forecasts using disagreement-attenuated weights.
        """
        alpha_eff, w_phys, D = self.compute_effective_weights(y_neural, y_ode, alpha_raw)
        
        y_hybrid = alpha_eff * y_neural + (1.0 - alpha_eff) * y_ode
        if residual is not None:
            y_final = y_hybrid + residual
        else:
            y_final = y_hybrid

        return {
            "trajectory": y_final,
            "y_hybrid": y_hybrid,
            "alpha_eff": alpha_eff,
            "w_phys": w_phys,
            "disagreement": D
        }
