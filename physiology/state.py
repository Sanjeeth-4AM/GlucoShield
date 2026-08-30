"""
GlucoShield Physiology Engine - State Container
================================================
Defines the explicit physical state variables tracked by the Mechanistic Digital Twin.
"""

import torch
from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class MetabolicState:
    """
    Container for the 8 continuous physiological states in the metabolic ODE system.
    Supports batched PyTorch tensors (Batch, ...) on CPU and CUDA.
    
    States:
      1. G_p: Plasma Glucose concentration [mg/dL]
      2. G_cgm: Interstitial Glucose concentration measured by CGM [mg/dL]
      3. X: Remote/interstitial active insulin action [min^-1]
      4. I_p: Plasma insulin concentration above basal [uU/mL]
      5. S1: Subcutaneous insulin absorption compartment 1 (non-monomeric) [mU]
      6. S2: Subcutaneous insulin absorption compartment 2 (monomeric) [mU]
      7. Q1: Solid/un-emptied carbohydrate pool in stomach [mg]
      8. Q2: Soluble carbohydrate pool in small intestine [mg]
    """
    G_p: torch.Tensor      # Plasma glucose [mg/dL]
    G_cgm: torch.Tensor    # Interstitial sensor glucose [mg/dL]
    X: torch.Tensor        # Remote active insulin action [min^-1]
    I_p: torch.Tensor      # Plasma insulin above basal [uU/mL]
    S1: torch.Tensor       # Subcutaneous insulin compartment 1 [mU]
    S2: torch.Tensor       # Subcutaneous insulin compartment 2 [mU]
    Q1: torch.Tensor       # Stomach carbohydrate pool [mg]
    Q2: torch.Tensor       # Intestinal carbohydrate pool [mg]

    @classmethod
    def create_initial_state(
        cls,
        initial_glucose: torch.Tensor,
        initial_iob: Optional[torch.Tensor] = None,
        initial_cob: Optional[torch.Tensor] = None,
        device: Optional[torch.device] = None
    ) -> "MetabolicState":
        """
        Creates an initial metabolic state consistent with observed initial CGM and empirical IOB/COB.
        """
        if device is None:
            device = initial_glucose.device

        batch_size = initial_glucose.shape[0] if initial_glucose.dim() > 0 else 1
        
        # Plasma glucose starts at observed CGM glucose
        G_p = initial_glucose.clone().to(device)
        G_cgm = initial_glucose.clone().to(device)
        
        # If IOB is available, split into S1/S2 pools (mU = Units * 1000)
        if initial_iob is not None:
            iob_mU = torch.clamp(initial_iob.to(device), min=0.0) * 1000.0
            S1 = iob_mU * 0.5
            S2 = iob_mU * 0.5
            # Estimate active remote insulin action from IOB
            X = torch.clamp(initial_iob.to(device) * 1.5e-4, min=0.0, max=0.05)
            I_p = torch.clamp(initial_iob.to(device) * 5.0, min=0.0)
        else:
            S1 = torch.zeros(batch_size, device=device)
            S2 = torch.zeros(batch_size, device=device)
            X = torch.zeros(batch_size, device=device)
            I_p = torch.zeros(batch_size, device=device)

        # If COB is available, split into Q1/Q2 pools (mg = g * 1000)
        if initial_cob is not None:
            cob_mg = torch.clamp(initial_cob.to(device), min=0.0) * 1000.0
            Q1 = cob_mg * 0.6  # 60% in stomach
            Q2 = cob_mg * 0.4  # 40% in intestine
        else:
            Q1 = torch.zeros(batch_size, device=device)
            Q2 = torch.zeros(batch_size, device=device)

        return cls(G_p=G_p, G_cgm=G_cgm, X=X, I_p=I_p, S1=S1, S2=S2, Q1=Q1, Q2=Q2)

    def to_tensor(self) -> torch.Tensor:
        """Stacks all 8 states into a single tensor of shape (batch, 8)."""
        return torch.stack([self.G_p, self.G_cgm, self.X, self.I_p, self.S1, self.S2, self.Q1, self.Q2], dim=-1)

    @classmethod
    def from_tensor(cls, tensor: torch.Tensor) -> "MetabolicState":
        """Reconstructs MetabolicState from tensor of shape (..., 8)."""
        return cls(
            G_p=tensor[..., 0],
            G_cgm=tensor[..., 1],
            X=tensor[..., 2],
            I_p=tensor[..., 3],
            S1=tensor[..., 4],
            S2=tensor[..., 5],
            Q1=tensor[..., 6],
            Q2=tensor[..., 7]
        )

    def clone(self) -> "MetabolicState":
        return MetabolicState(
            G_p=self.G_p.clone(),
            G_cgm=self.G_cgm.clone(),
            X=self.X.clone(),
            I_p=self.I_p.clone(),
            S1=self.S1.clone(),
            S2=self.S2.clone(),
            Q1=self.Q1.clone(),
            Q2=self.Q2.clone()
        )

    @property
    def iob(self) -> torch.Tensor:
        """Current Insulin-on-Board in Units."""
        return (self.S1 + self.S2) / 1000.0

    @property
    def cob(self) -> torch.Tensor:
        """Current Carbs-on-Board in grams."""
        return (self.Q1 + self.Q2) / 1000.0
