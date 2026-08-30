"""
GlucoShield Physiology Engine - Counterfactual "What-If" Simulation Engine
===========================================================================
Simulates hypothetical meal and insulin scenarios (dose variation, timing shifts,
rescue carbohydrates, correction doses) for clinical decision-support and patient empowerment.
"""

import torch
from typing import Dict, List, Optional, Any
from physiology.state import MetabolicState
from physiology.parameters import PhysiologicalParameters
from physiology.integrator import RK4Integrator

class CounterfactualSimulator:
    """
    Simulates forward metabolic outcomes for hypothetical patient decisions.
    Framed as a decision-support research simulation engine.
    """
    def __init__(self, horizon_steps: int = 20, dt: float = 1.0):
        self.horizon_steps = horizon_steps  # 20 steps = 5 hours
        self.integrator = RK4Integrator(microsteps_per_interval=15, dt=dt)

    def simulate_scenario(
        self,
        initial_state: MetabolicState,
        parameters: PhysiologicalParameters,
        scenario_insulin: torch.Tensor,     # (batch, horizon_steps) in Units
        scenario_carbs: torch.Tensor,       # (batch, horizon_steps) in grams
        scenario_name: str = "custom_scenario"
    ) -> Dict[str, Any]:
        """
        Simulates a specific hypothetical scenario over 5 hours (20 steps of 15 min).
        
        Returns:
          Dictionary containing:
            - simulated_glucose: Tensor (batch, 20) [mg/dL]
            - nadir_glucose: Tensor (batch,)
            - time_to_nadir_min: Tensor (batch,)
            - peak_glucose: Tensor (batch,)
            - time_to_peak_min: Tensor (batch,)
            - time_in_range_pct: Tensor (batch,) [70-180 mg/dL]
            - time_below_70_pct: Tensor (batch,)
            - time_above_180_pct: Tensor (batch,)
            - iob_trajectory: Tensor (batch, 20) [Units]
            - cob_trajectory: Tensor (batch, 20) [grams]
            - active_insulin_action: Tensor (batch, 20)
            - warnings: List of warning strings
        """
        device = scenario_insulin.device
        batch_size = scenario_insulin.shape[0]

        sim_cgm, state_history = self.integrator.forward_simulate(
            initial_state, scenario_insulin, scenario_carbs, parameters
        )  # sim_cgm is (batch, 20)

        # Extract summary metrics
        nadir_vals, nadir_indices = torch.min(sim_cgm, dim=-1)
        peak_vals, peak_indices = torch.max(sim_cgm, dim=-1)
        
        time_to_nadir_min = (nadir_indices + 1) * 15
        time_to_peak_min = (peak_indices + 1) * 15

        # Time in Range calculations (70 to 180 mg/dL)
        in_range = (sim_cgm >= 70.0) & (sim_cgm <= 180.0)
        below_70 = (sim_cgm < 70.0)
        above_180 = (sim_cgm > 180.0)

        tir_pct = torch.mean(in_range.float(), dim=-1) * 100.0
        tbr_pct = torch.mean(below_70.float(), dim=-1) * 100.0
        tar_pct = torch.mean(above_180.float(), dim=-1) * 100.0

        # Trajectories for IOB, COB, X (skip state 0 which is initial)
        iob_traj = torch.stack([s.iob for s in state_history[1:]], dim=-1)
        cob_traj = torch.stack([s.cob for s in state_history[1:]], dim=-1)
        x_traj = torch.stack([s.X for s in state_history[1:]], dim=-1)

        warnings = []
        if torch.any(nadir_vals < 70.0):
            min_val = nadir_vals.min().item()
            warnings.append(f"WARNING: High Hypoglycemia Risk detected (Projected nadir: {min_val:.1f} mg/dL).")
        if torch.any(peak_vals > 250.0):
            max_val = peak_vals.max().item()
            warnings.append(f"WARNING: Severe Hyperglycemia projected (Peak: {max_val:.1f} mg/dL).")

        return {
            "scenario_name": scenario_name,
            "simulated_glucose": sim_cgm,
            "nadir_glucose": nadir_vals,
            "time_to_nadir_min": time_to_nadir_min,
            "peak_glucose": peak_vals,
            "time_to_peak_min": time_to_peak_min,
            "time_in_range_pct": tir_pct,
            "time_below_70_pct": tbr_pct,
            "time_above_180_pct": tar_pct,
            "iob_trajectory": iob_traj,
            "cob_trajectory": cob_traj,
            "active_insulin_action": x_traj,
            "warnings": warnings
        }

    def compare_meal_bolus_options(
        self,
        initial_state: MetabolicState,
        parameters: PhysiologicalParameters,
        meal_grams: float,
        bolus_options: List[float] = [2.0, 4.0, 6.0, 8.0]
    ) -> Dict[str, Any]:
        """
        Evaluates multiple alternative insulin bolus options for an upcoming meal.
        """
        device = initial_state.G_p.device
        results = {}
        
        for bolus_u in bolus_options:
            ins = torch.zeros(1, self.horizon_steps, device=device)
            carbs = torch.zeros(1, self.horizon_steps, device=device)
            # Meal and bolus at t=0
            carbs[0, 0] = meal_grams
            ins[0, 0] = bolus_u
            
            res = self.simulate_scenario(
                initial_state, parameters, ins, carbs,
                scenario_name=f"bolus_{bolus_u:.1f}U_meal_{meal_grams:.0f}g"
            )
            results[f"{bolus_u:.1f}U"] = res
            
        return results

    def simulate_rescue_carbs(
        self,
        initial_state: MetabolicState,
        parameters: PhysiologicalParameters,
        active_bolus: float,
        rescue_carbs_grams: float = 15.0,
        rescue_delay_steps: int = 2 # 30 minutes after start
    ) -> Dict[str, Any]:
        """
        Simulates hypothetical intake of rescue carbohydrates (e.g. 15g glucose tabs)
        to evaluate whether it arrests a projected hypoglycemia event.
        """
        device = initial_state.G_p.device
        
        # Scenario 1: No rescue carbs
        ins_no_rescue = torch.zeros(1, self.horizon_steps, device=device)
        ins_no_rescue[0, 0] = active_bolus
        carbs_no_rescue = torch.zeros(1, self.horizon_steps, device=device)
        res_no_rescue = self.simulate_scenario(
            initial_state, parameters, ins_no_rescue, carbs_no_rescue, "unmitigated"
        )
        
        # Scenario 2: Rescue carbs administered at delay
        ins_rescue = torch.zeros(1, self.horizon_steps, device=device)
        ins_rescue[0, 0] = active_bolus
        carbs_rescue = torch.zeros(1, self.horizon_steps, device=device)
        carbs_rescue[0, rescue_delay_steps] = rescue_carbs_grams
        res_rescue = self.simulate_scenario(
            initial_state, parameters, ins_rescue, carbs_rescue, f"rescue_{rescue_carbs_grams:.0f}g_at_{rescue_delay_steps*15}m"
        )
        
        return {
            "unmitigated": res_no_rescue,
            "with_rescue": res_rescue,
            "nadir_gain_mg_dl": res_rescue["nadir_glucose"].item() - res_no_rescue["nadir_glucose"].item()
        }
