"""
GlucoShield Physiology Engine - Parameter Container & Transformations
======================================================================
Defines physiological parameters with differentiable bounded mapping and patient initialization.
"""

import torch
import torch.nn as nn
from dataclasses import dataclass
from typing import Dict, Optional
from physiology.constraints import PARAMETER_BOUNDS, clamp_parameters

@dataclass
class PhysiologicalParameters:
    """
    Holds the personalized metabolic parameters for the ODE model.
    All attributes are PyTorch tensors supporting batched GPU computations.
    """
    S_I: torch.Tensor             # Insulin sensitivity [(uU/mL)^-1 min^-1]
    S_G: torch.Tensor             # Glucose effectiveness (p1) [min^-1]
    p2: torch.Tensor              # Insulin action deactivation rate [min^-1]
    tau_s: torch.Tensor           # Subcutaneous insulin time constant [min]
    k_empt: torch.Tensor          # Gastric emptying rate [min^-1]
    k_abs: torch.Tensor           # Gut absorption rate [min^-1]
    tau_d: torch.Tensor           # Sensor diffusion delay [min]
    G_b: torch.Tensor             # Basal glucose target [mg/dL]
    V_g: torch.Tensor             # Glucose distribution volume [dL/kg]
    BW: torch.Tensor              # Body weight [kg]
    V_I: torch.Tensor             # Insulin distribution volume [L/kg]
    k_e: torch.Tensor             # Plasma insulin clearance rate [min^-1]
    bioavailability: torch.Tensor # Meal carb bioavailability fraction
    beta_cell: torch.Tensor       # Endogenous insulin response gain

    @classmethod
    def create_population_default(
        cls,
        batch_size: int = 1,
        is_t1dm: Optional[torch.Tensor] = None,
        device: torch.device = torch.device("cpu")
    ) -> "PhysiologicalParameters":
        """Creates population-average parameter tensors."""
        ones = torch.ones(batch_size, device=device)
        
        t1d_mask = is_t1dm.to(device) if is_t1dm is not None else torch.zeros(batch_size, device=device)
        # T1DM has 0 endogenous beta-cell response; T2DM has partial response
        beta_cell = (1.0 - t1d_mask) * 0.008 * ones

        return cls(
            S_I=1.2e-4 * ones,
            S_G=0.015 * ones,
            p2=0.025 * ones,
            tau_s=55.0 * ones,
            k_empt=0.018 * ones,
            k_abs=0.025 * ones,
            tau_d=10.0 * ones,
            G_b=110.0 * ones,
            V_g=1.9 * ones,
            BW=70.0 * ones,
            V_I=0.14 * ones,
            k_e=0.12 * ones,
            bioavailability=0.88 * ones,
            beta_cell=beta_cell
        )

    def to_dict(self) -> Dict[str, torch.Tensor]:
        return {
            "S_I": self.S_I, "S_G": self.S_G, "p2": self.p2,
            "tau_s": self.tau_s, "k_empt": self.k_empt, "k_abs": self.k_abs,
            "tau_d": self.tau_d, "G_b": self.G_b, "V_g": self.V_g,
            "BW": self.BW, "V_I": self.V_I, "k_e": self.k_e,
            "bioavailability": self.bioavailability, "beta_cell": self.beta_cell
        }

    @classmethod
    def from_dict(cls, d: Dict[str, torch.Tensor]) -> "PhysiologicalParameters":
        return cls(**d)

    def clamp(self) -> "PhysiologicalParameters":
        """Returns a new parameter object with all parameters clamped to physiological ranges."""
        clamped_dict = clamp_parameters(self.to_dict())
        return PhysiologicalParameters.from_dict(clamped_dict)

    def clone(self) -> "PhysiologicalParameters":
        return PhysiologicalParameters(
            S_I=self.S_I.clone(), S_G=self.S_G.clone(), p2=self.p2.clone(),
            tau_s=self.tau_s.clone(), k_empt=self.k_empt.clone(), k_abs=self.k_abs.clone(),
            tau_d=self.tau_d.clone(), G_b=self.G_b.clone(), V_g=self.V_g.clone(),
            BW=self.BW.clone(), V_I=self.V_I.clone(), k_e=self.k_e.clone(),
            bioavailability=self.bioavailability.clone(), beta_cell=self.beta_cell.clone()
        )
