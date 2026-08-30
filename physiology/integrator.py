"""
GlucoShield Physiology Engine - Differentiable RK4 Numerical Integrator
========================================================================
Implements batched 4th-Order Runge-Kutta integration with 1-minute micro-stepping
across 15-minute macro intervals. Fully differentiable through PyTorch autograd.
"""

import torch
from typing import Tuple, List, Optional
from physiology.state import MetabolicState
from physiology.parameters import PhysiologicalParameters
from physiology.compartments import compute_metabolic_derivatives
from physiology.constraints import enforce_state_constraints

def rk4_microstep(
    state: MetabolicState,
    u_ins: torch.Tensor,
    D_carb: torch.Tensor,
    params: PhysiologicalParameters,
    dt: float = 1.0
) -> MetabolicState:
    """
    Executes one 4th-Order Runge-Kutta microstep of length dt (default 1.0 minute).
    All state operations are differentiable.
    """
    # k1 = f(x)
    k1 = compute_metabolic_derivatives(state, u_ins, D_carb, params)
    
    # x + 0.5 * dt * k1
    s_half1 = MetabolicState(
        G_p=state.G_p + 0.5 * dt * k1.G_p,
        G_cgm=state.G_cgm + 0.5 * dt * k1.G_cgm,
        X=state.X + 0.5 * dt * k1.X,
        I_p=state.I_p + 0.5 * dt * k1.I_p,
        S1=state.S1 + 0.5 * dt * k1.S1,
        S2=state.S2 + 0.5 * dt * k1.S2,
        Q1=state.Q1 + 0.5 * dt * k1.Q1,
        Q2=state.Q2 + 0.5 * dt * k1.Q2
    )
    # k2 = f(x + 0.5 * dt * k1)
    k2 = compute_metabolic_derivatives(s_half1, u_ins, D_carb, params)
    
    # x + 0.5 * dt * k2
    s_half2 = MetabolicState(
        G_p=state.G_p + 0.5 * dt * k2.G_p,
        G_cgm=state.G_cgm + 0.5 * dt * k2.G_cgm,
        X=state.X + 0.5 * dt * k2.X,
        I_p=state.I_p + 0.5 * dt * k2.I_p,
        S1=state.S1 + 0.5 * dt * k2.S1,
        S2=state.S2 + 0.5 * dt * k2.S2,
        Q1=state.Q1 + 0.5 * dt * k2.Q1,
        Q2=state.Q2 + 0.5 * dt * k2.Q2
    )
    # k3 = f(x + 0.5 * dt * k2)
    k3 = compute_metabolic_derivatives(s_half2, u_ins, D_carb, params)
    
    # x + dt * k3
    s_full = MetabolicState(
        G_p=state.G_p + dt * k3.G_p,
        G_cgm=state.G_cgm + dt * k3.G_cgm,
        X=state.X + dt * k3.X,
        I_p=state.I_p + dt * k3.I_p,
        S1=state.S1 + dt * k3.S1,
        S2=state.S2 + dt * k3.S2,
        Q1=state.Q1 + dt * k3.Q1,
        Q2=state.Q2 + dt * k3.Q2
    )
    # k4 = f(x + dt * k3)
    k4 = compute_metabolic_derivatives(s_full, u_ins, D_carb, params)
    
    # Final RK4 update: x_next = x + (dt/6) * (k1 + 2*k2 + 2*k3 + k4)
    factor = dt / 6.0
    G_p_next = state.G_p + factor * (k1.G_p + 2.0 * k2.G_p + 2.0 * k3.G_p + k4.G_p)
    G_cgm_next = state.G_cgm + factor * (k1.G_cgm + 2.0 * k2.G_cgm + 2.0 * k3.G_cgm + k4.G_cgm)
    X_next = state.X + factor * (k1.X + 2.0 * k2.X + 2.0 * k3.X + k4.X)
    I_p_next = state.I_p + factor * (k1.I_p + 2.0 * k2.I_p + 2.0 * k3.I_p + k4.I_p)
    S1_next = state.S1 + factor * (k1.S1 + 2.0 * k2.S1 + 2.0 * k3.S1 + k4.S1)
    S2_next = state.S2 + factor * (k1.S2 + 2.0 * k2.S2 + 2.0 * k3.S2 + k4.S2)
    Q1_next = state.Q1 + factor * (k1.Q1 + 2.0 * k2.Q1 + 2.0 * k3.Q1 + k4.Q1)
    Q2_next = state.Q2 + factor * (k1.Q2 + 2.0 * k2.Q2 + 2.0 * k3.Q2 + k4.Q2)
    
    # Apply soft/clamped physical safety constraints
    G_p_clamped = torch.clamp(G_p_next, min=20.0, max=600.0)
    G_cgm_clamped = torch.clamp(G_cgm_next, min=20.0, max=600.0)
    X_clamped = torch.clamp(X_next, min=0.0, max=0.10)
    I_p_clamped = torch.clamp(I_p_next, min=0.0, max=500.0)
    S1_clamped = torch.clamp(S1_next, min=0.0)
    S2_clamped = torch.clamp(S2_next, min=0.0)
    Q1_clamped = torch.clamp(Q1_next, min=0.0)
    Q2_clamped = torch.clamp(Q2_next, min=0.0)

    return MetabolicState(
        G_p=G_p_clamped,
        G_cgm=G_cgm_clamped,
        X=X_clamped,
        I_p=I_p_clamped,
        S1=S1_clamped,
        S2=S2_clamped,
        Q1=Q1_clamped,
        Q2=Q2_clamped
    )


class RK4Integrator:
    """
    Batched multi-interval RK4 integrator for 15-minute macro intervals.
    """
    def __init__(self, microsteps_per_interval: int = 15, dt: float = 1.0):
        self.microsteps = microsteps_per_interval
        self.dt = dt  # 1.0 minute

    def step_interval(
        self,
        current_state: MetabolicState,
        insulin_units_15m: torch.Tensor,   # Total insulin units in this 15-min step [Units]
        carbs_grams_15m: torch.Tensor,     # Total carbs in this 15-min step [grams]
        params: PhysiologicalParameters
    ) -> Tuple[MetabolicState, torch.Tensor]:
        """
        Integrates over a single 15-minute macro interval.
        Returns:
          next_state: MetabolicState at t + 15 min
          cgm_trajectory: Tensor of shape (batch, 15) tracking 1-minute interstitial glucose
        """
        # Convert 15-min totals to continuous rates per minute:
        # Insulin: Units / 15 min * 1000 -> mU/min
        u_ins_rate = (insulin_units_15m / 15.0) * 1000.0
        # Carbs: grams / 15 min * 1000 -> mg/min
        D_carb_rate = (carbs_grams_15m / 15.0) * 1000.0

        state = current_state
        cgm_history = []

        for _ in range(self.microsteps):
            state = rk4_microstep(state, u_ins_rate, D_carb_rate, params, dt=self.dt)
            cgm_history.append(state.G_cgm)

        cgm_trajectory = torch.stack(cgm_history, dim=-1)  # (batch, 15)
        return state, cgm_trajectory

    def forward_simulate(
        self,
        initial_state: MetabolicState,
        insulin_sequence: torch.Tensor,    # Shape (batch, num_steps) in Units
        carbs_sequence: torch.Tensor,      # Shape (batch, num_steps) in grams
        params: PhysiologicalParameters
    ) -> Tuple[torch.Tensor, List[MetabolicState]]:
        """
        Simulates forward across multiple 15-minute macro intervals.
        Returns:
          simulated_cgm: Tensor of shape (batch, num_steps) sampled at 15-min marks
          state_history: List of MetabolicState objects at each 15-min mark
        """
        batch_size, num_steps = insulin_sequence.shape
        state = initial_state
        cgm_preds = []
        state_history = [state.clone()]

        for k in range(num_steps):
            u_k = insulin_sequence[:, k]
            d_k = carbs_sequence[:, k]
            state, _ = self.step_interval(state, u_k, d_k, params)
            cgm_preds.append(state.G_cgm)
            state_history.append(state.clone())

        simulated_cgm = torch.stack(cgm_preds, dim=1)  # (batch, num_steps)
        return simulated_cgm, state_history
