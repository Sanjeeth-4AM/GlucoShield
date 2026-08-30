"""
GlucoShield Physiology Engine - Tier 2 Moving Horizon Parameter Calibrator
===========================================================================
Performs differentiable moving horizon calibration over the preceding 24-hour window (96 timesteps)
to personalize metabolic parameters (S_I, k_empt, S_G, G_b) and reconstruct latent states at t=0.
"""

import time
import torch
import torch.nn as nn
from typing import Tuple, Dict, Optional
from physiology.state import MetabolicState
from physiology.parameters import PhysiologicalParameters
from physiology.integrator import RK4Integrator
from physiology.constraints import PARAMETER_BOUNDS, clamp_parameters

class MovingHorizonCalibrator(nn.Module):
    """
    Online parameter calibrator and state observer.
    Optimizes 4 key patient-specific scaling factors over past 24 hours:
      delta_0: log-scale multiplier for Insulin Sensitivity S_I
      delta_1: log-scale multiplier for Gastric Emptying k_empt
      delta_2: log-scale multiplier for Glucose Effectiveness S_G
      delta_3: additive offset for Basal Glucose G_b [mg/dL]
    """
    def __init__(
        self,
        num_iterations: int = 15,
        learning_rate: float = 0.05,
        lambda_reg: float = 0.01,
        substeps: int = 15
    ):
        super().__init__()
        self.num_iterations = num_iterations
        self.learning_rate = learning_rate
        self.lambda_reg = lambda_reg
        self.integrator = RK4Integrator(microsteps_per_interval=substeps, dt=1.0)

    def calibrate_and_observe(
        self,
        history_sequences: torch.Tensor,    # Shape (batch, 96, 22) - past 24 hours
        prior_params: PhysiologicalParameters,
        optimize_parameters: bool = True
    ) -> Tuple[PhysiologicalParameters, MetabolicState, Dict[str, float]]:
        """
        Calibrates physiological parameters on past 24-hour CGM and returns the
        calibrated parameters along with the estimated metabolic state at t=0.
        
        Returns:
          calibrated_params: PhysiologicalParameters
          state_at_t0: MetabolicState at prediction cutoff (t=0)
          diagnostics: Dict containing calibration loss, runtime (ms), etc.
        """
        t0_time = time.time()
        device = history_sequences.device
        batch_size = history_sequences.shape[0]

        # Extract past 24h channels
        past_cgm = history_sequences[:, :, 0]       # (batch, 96) [mg/dL]
        past_insulin = history_sequences[:, :, 15]   # (batch, 96) [Units per 15 min]
        past_carbs = history_sequences[:, :, 17]     # (batch, 96) [grams per 15 min]
        
        # Initial state at t = -96 (24 hours ago)
        # Initialize from the first observed CGM value 24 hours ago
        init_state_t_minus_96 = MetabolicState.create_initial_state(
            initial_glucose=past_cgm[:, 0],
            device=device
        )

        # Detach prior parameters to prevent graph contamination
        prior_p = PhysiologicalParameters(
            S_I=prior_params.S_I.detach().clone(),
            S_G=prior_params.S_G.detach().clone(),
            p2=prior_params.p2.detach().clone(),
            tau_s=prior_params.tau_s.detach().clone(),
            k_empt=prior_params.k_empt.detach().clone(),
            k_abs=prior_params.k_abs.detach().clone(),
            tau_d=prior_params.tau_d.detach().clone(),
            G_b=prior_params.G_b.detach().clone(),
            V_g=prior_params.V_g.detach().clone(),
            BW=prior_params.BW.detach().clone(),
            V_I=prior_params.V_I.detach().clone(),
            k_e=prior_params.k_e.detach().clone(),
            bioavailability=prior_params.bioavailability.detach().clone(),
            beta_cell=prior_params.beta_cell.detach().clone()
        )

        if optimize_parameters and self.num_iterations > 0:
            with torch.enable_grad():
                # delta: [log_S_I_mult, log_k_empt_mult, log_S_G_mult, G_b_offset]
                delta = torch.zeros(batch_size, 4, device=device, requires_grad=True)
                optimizer = torch.optim.Adam([delta], lr=self.learning_rate)

                # Sub-sample history for fast calibration (every 2nd step -> 48 points)
                cgm_target_sub = past_cgm[:, ::2]  # (batch, 48)
                ins_sub = past_insulin[:, ::2] + past_insulin[:, 1::2] # total units in 30-min
                carbs_sub = past_carbs[:, ::2] + past_carbs[:, 1::2]   # total carbs in 30-min

                calib_integrator = RK4Integrator(microsteps_per_interval=10, dt=3.0)

                for it in range(self.num_iterations):
                    optimizer.zero_grad()
                    
                    # Apply delta modifiers to prior params
                    s_i_mult = torch.exp(torch.clamp(delta[:, 0], -1.5, 1.5))
                    k_empt_mult = torch.exp(torch.clamp(delta[:, 1], -1.0, 1.0))
                    s_g_mult = torch.exp(torch.clamp(delta[:, 2], -1.0, 1.0))
                    g_b_offset = torch.clamp(delta[:, 3], -40.0, 40.0)

                    temp_params = PhysiologicalParameters(
                        S_I=torch.clamp(prior_p.S_I * s_i_mult, PARAMETER_BOUNDS["S_I"][0], PARAMETER_BOUNDS["S_I"][1]),
                        S_G=torch.clamp(prior_p.S_G * s_g_mult, PARAMETER_BOUNDS["S_G"][0], PARAMETER_BOUNDS["S_G"][1]),
                        p2=prior_p.p2,
                        tau_s=prior_p.tau_s,
                        k_empt=torch.clamp(prior_p.k_empt * k_empt_mult, PARAMETER_BOUNDS["k_empt"][0], PARAMETER_BOUNDS["k_empt"][1]),
                        k_abs=prior_p.k_abs,
                        tau_d=prior_p.tau_d,
                        G_b=torch.clamp(prior_p.G_b + g_b_offset, PARAMETER_BOUNDS["G_b"][0], PARAMETER_BOUNDS["G_b"][1]),
                        V_g=prior_p.V_g,
                        BW=prior_p.BW,
                        V_I=prior_p.V_I,
                        k_e=prior_p.k_e,
                        bioavailability=prior_p.bioavailability,
                        beta_cell=prior_p.beta_cell
                    )

                    sim_cgm, _ = calib_integrator.forward_simulate(
                        init_state_t_minus_96, ins_sub, carbs_sub, temp_params
                    )

                    # Huber loss against observed history + L2 regularization toward prior (delta -> 0)
                    loss_fit = torch.nn.functional.smooth_l1_loss(sim_cgm, cgm_target_sub, beta=10.0)
                    loss_reg = self.lambda_reg * torch.mean(delta ** 2)
                    loss = loss_fit + loss_reg

                    loss.backward()
                    optimizer.step()

                # Detach optimal deltas
                delta_opt = delta.detach()
                s_i_mult = torch.exp(torch.clamp(delta_opt[:, 0], -1.5, 1.5))
                k_empt_mult = torch.exp(torch.clamp(delta_opt[:, 1], -1.0, 1.0))
                s_g_mult = torch.exp(torch.clamp(delta_opt[:, 2], -1.0, 1.0))
                g_b_offset = torch.clamp(delta_opt[:, 3], -40.0, 40.0)

                calibrated_params = PhysiologicalParameters(
                    S_I=torch.clamp(prior_p.S_I * s_i_mult, PARAMETER_BOUNDS["S_I"][0], PARAMETER_BOUNDS["S_I"][1]),
                    S_G=torch.clamp(prior_p.S_G * s_g_mult, PARAMETER_BOUNDS["S_G"][0], PARAMETER_BOUNDS["S_G"][1]),
                    p2=prior_p.p2,
                    tau_s=prior_p.tau_s,
                    k_empt=torch.clamp(prior_p.k_empt * k_empt_mult, PARAMETER_BOUNDS["k_empt"][0], PARAMETER_BOUNDS["k_empt"][1]),
                    k_abs=prior_p.k_abs,
                    tau_d=prior_p.tau_d,
                    G_b=torch.clamp(prior_p.G_b + g_b_offset, PARAMETER_BOUNDS["G_b"][0], PARAMETER_BOUNDS["G_b"][1]),
                    V_g=prior_p.V_g,
                    BW=prior_p.BW,
                    V_I=prior_p.V_I,
                    k_e=prior_p.k_e,
                    bioavailability=prior_p.bioavailability,
                    beta_cell=prior_p.beta_cell
                )
        else:
            calibrated_params = prior_p

        # Perform exact full-resolution 96-step forward simulation with calibrated parameters
        # to observe the precise state x(t=0) at the prediction cutoff
        with torch.no_grad():
            _, state_history = self.integrator.forward_simulate(
                init_state_t_minus_96, past_insulin, past_carbs, calibrated_params
            )
            # State at t=0 (last step in history)
            state_at_t0 = state_history[-1]
            
            # Align glucose state with the known observed current CGM reading at t=0
            # to eliminate accumulated offset while keeping internal kinetic states (X, S1, S2, Q1, Q2)
            current_cgm_obs = past_cgm[:, -1]
            state_at_t0.G_p = current_cgm_obs.clone()
            state_at_t0.G_cgm = current_cgm_obs.clone()

        elapsed_ms = (time.time() - t0_time) * 1000.0
        diagnostics = {
            "calibration_time_ms": elapsed_ms,
            "mean_s_i": calibrated_params.S_I.mean().item(),
            "mean_k_empt": calibrated_params.k_empt.mean().item(),
            "mean_g_b": calibrated_params.G_b.mean().item()
        }

        return calibrated_params, state_at_t0, diagnostics
