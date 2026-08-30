"""
GlucoShield Physiology Engine - Compartmental ODE Equations
============================================================
Implements the first-principles nonlinear metabolic differential equations:
  dQ1/dt, dQ2/dt (Gut absorption & Ra)
  dS1/dt, dS2/dt (Subcutaneous insulin absorption & UI)
  dIp/dt (Plasma insulin)
  dX/dt (Remote active insulin action)
  dGp/dt (Plasma glucose balance with hepatic & peripheral clearance)
  dGcgm/dt (Interstitial sensor diffusion delay)
"""

import torch
from physiology.state import MetabolicState
from physiology.parameters import PhysiologicalParameters

def compute_metabolic_derivatives(
    state: MetabolicState,
    u_ins: torch.Tensor,       # Total insulin input rate [mU/min = Units/min * 1000]
    D_carb: torch.Tensor,      # Carbohydrate ingestion rate [mg/min = g/min * 1000]
    params: PhysiologicalParameters
) -> MetabolicState:
    """
    Computes time derivatives dx/dt for all 8 physiological states.
    All inputs and outputs are batched tensors (Batch,).
    """
    # 1. Carbohydrate Gastrointestinal Subsystem (2-compartment gut)
    # dQ1/dt = -k_empt * Q1 + D(t)
    # dQ2/dt = k_empt * Q1 - k_abs * Q2
    dQ1_dt = -params.k_empt * state.Q1 + D_carb
    dQ2_dt = params.k_empt * state.Q1 - params.k_abs * state.Q2
    
    # Rate of systemic glucose appearance Ra(t) [mg/dL/min]
    # Total volume in dL = V_g [dL/kg] * BW [kg]
    vol_glucose_dL = params.V_g * params.BW
    Ra = (params.bioavailability * params.k_abs * state.Q2) / vol_glucose_dL

    # 2. Subcutaneous Insulin Absorption Subsystem (2-compartment)
    # dS1/dt = u_ins(t) - S1 / tau_s
    # dS2/dt = (S1 - S2) / tau_s
    dS1_dt = u_ins - (state.S1 / params.tau_s)
    dS2_dt = (state.S1 - state.S2) / params.tau_s
    
    # Systemic insulin appearance rate UI(t) [mU/min]
    UI = state.S2 / params.tau_s

    # 3. Plasma Insulin Kinetics & Endogenous Secretion
    # Vol in Liters = V_I [L/kg] * BW [kg]
    # UI [mU/min] / (V_I * BW) -> uU/mL/min (since 1 mU/L = 1 uU/mL)
    vol_insulin_L = params.V_I * params.BW
    # Endogenous insulin response to hyperglycemia above baseline
    hyperglycemia = torch.clamp(state.G_p - params.G_b, min=0.0)
    endog_secretion = params.beta_cell * hyperglycemia  # [uU/mL/min]
    
    dIp_dt = (UI / vol_insulin_L) - (params.k_e * state.I_p) + endog_secretion

    # 4. Remote Active Insulin Action (Bergman Remote Compartment)
    # dX/dt = -p2 * X + p3 * I_p, where S_I = p3 / p2 => p3 = S_I * p2
    p3 = params.S_I * params.p2
    dX_dt = -params.p2 * state.X + p3 * state.I_p

    # 5. Plasma Glucose Balance (Minimal Model with Hepatic Suppression)
    # dGp/dt = - [S_G + X(t)] * G_p(t) + S_G * G_b + Ra(t)
    # Peripheral uptake + Basal suppression
    dGp_dt = -(params.S_G + state.X) * state.G_p + (params.S_G * params.G_b) + Ra

    # 6. Interstitial Sensor Diffusion Delay (CGM Sensor)
    # dGcgm/dt = (G_p - G_cgm) / tau_d
    dGcgm_dt = (state.G_p - state.G_cgm) / params.tau_d

    return MetabolicState(
        G_p=dGp_dt,
        G_cgm=dGcgm_dt,
        X=dX_dt,
        I_p=dIp_dt,
        S1=dS1_dt,
        S2=dS2_dt,
        Q1=dQ1_dt,
        Q2=dQ2_dt
    )
