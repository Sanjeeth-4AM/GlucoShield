"""
GlucoShield Physiology Engine - Constraints & Physical Invariants
==================================================================
Defines physiological boundaries, parameter clamping, and state non-negativity rules.
"""

import torch

# Physiological parameter hard bounds [min, max]
PARAMETER_BOUNDS = {
    "S_I": (1.0e-5, 5.0e-3),        # Insulin sensitivity [(uU/mL)^-1 min^-1]
    "S_G": (0.005, 0.040),          # Glucose effectiveness [min^-1]
    "p2": (0.010, 0.050),           # Insulin action deactivation rate [min^-1]
    "tau_s": (30.0, 90.0),          # Subcutaneous insulin absorption time constant [min]
    "k_empt": (0.008, 0.045),       # Gastric emptying rate [min^-1]
    "k_abs": (0.010, 0.055),        # Intestinal carbohydrate absorption rate [min^-1]
    "tau_d": (5.0, 18.0),           # Interstitial sensor diffusion lag [min]
    "G_b": (70.0, 220.0),           # Basal target glucose equilibrium [mg/dL]
    "V_g": (1.4, 2.6),              # Glucose distribution volume [dL/kg]
    "V_I": (0.10, 0.20),            # Insulin distribution volume [L/kg]
    "k_e": (0.08, 0.20),            # Plasma insulin elimination rate [min^-1]
    "bioavailability": (0.75, 0.95),# Fraction of ingested carbs reaching circulation
    "EGP_0": (1.0, 3.0),            # Basal endogenous glucose production [mg/kg/min]
}

# State non-negativity and clinical safety bounds
MIN_GLUCOSE = 20.0      # mg/dL (absolute survival floor)
MAX_GLUCOSE = 600.0     # mg/dL (meter upper saturation limit)
MAX_CARBS_PER_MEAL = 300.0 # grams

def clamp_parameters(params_dict: dict) -> dict:
    """Clamps a dictionary of physiological parameter tensors to their physical boundaries."""
    clamped = {}
    for key, val in params_dict.items():
        if key in PARAMETER_BOUNDS:
            low, high = PARAMETER_BOUNDS[key]
            clamped[key] = torch.clamp(val, min=low, max=high)
        else:
            clamped[key] = val
    return clamped

def enforce_state_constraints(state_tensor: torch.Tensor) -> torch.Tensor:
    """
    Enforces non-negativity and physical sanity on state tensor (..., 8).
    Indices:
      0: G_p, 1: G_cgm, 2: X, 3: I_p, 4: S1, 5: S2, 6: Q1, 7: Q2
    """
    clamped = state_tensor.clone()
    # Glucose states bounded [MIN_GLUCOSE, MAX_GLUCOSE]
    clamped[..., 0] = torch.clamp(clamped[..., 0], min=MIN_GLUCOSE, max=MAX_GLUCOSE)
    clamped[..., 1] = torch.clamp(clamped[..., 1], min=MIN_GLUCOSE, max=MAX_GLUCOSE)
    
    # Insulin action and compartment pools must be non-negative
    clamped[..., 2] = torch.clamp(clamped[..., 2], min=0.0, max=0.10)     # X
    clamped[..., 3] = torch.clamp(clamped[..., 3], min=0.0, max=500.0)    # I_p
    clamped[..., 4] = torch.clamp(clamped[..., 4], min=0.0)               # S1
    clamped[..., 5] = torch.clamp(clamped[..., 5], min=0.0)               # S2
    clamped[..., 6] = torch.clamp(clamped[..., 6], min=0.0)               # Q1
    clamped[..., 7] = torch.clamp(clamped[..., 7], min=0.0)               # Q2
    return clamped
