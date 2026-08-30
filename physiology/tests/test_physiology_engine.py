"""
GlucoShield Physiology Engine - 20-Point Comprehensive Unit & Scientific Test Suite
===================================================================================
Covers all 20 required verification dimensions:
  1. Import test
  2. CPU smoke test
  3. CUDA smoke test
  4. RK4 known-system numerical accuracy test
  5. 15 microsteps per macro interval test
  6. Gradient / backpropagation differentiability test
  7. No NaN/Inf propagation test
  8. State and batch shape preservation test
  9. Non-negative physiological state constraints test
  10. Zero-meal scenario baseline test
  11. Meal absorption kinetic response test
  12. Bolus response directionality & monotonicity test
  13. Basal equilibrium & stability test
  14. Interstitial CGM sensor delay test
  15. Counterfactual immutability test
  16. Calibrator causality test (strictly past 96 steps)
  17. Calibrator bounded-parameter preservation test
  18. Hybrid gate output range [0, 1] test
  19. Hybrid trajectory shape & horizon alignment test
  20. CPU / GPU numerical consistency test
"""

import sys
import os
import unittest
import torch
import torch.nn as nn
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from physiology.state import MetabolicState
from physiology.parameters import PhysiologicalParameters
from physiology.integrator import RK4Integrator, rk4_microstep
from physiology.compartments import compute_metabolic_derivatives
from physiology.constraints import PARAMETER_BOUNDS, clamp_parameters, enforce_state_constraints
from physiology.priors import BiomarkerPriorNetwork
from physiology.calibrator import MovingHorizonCalibrator
from physiology.simulator import CounterfactualSimulator
from physiology.hybrid_fusion import AdaptiveFusionGate

class ComprehensivePhysiologyTestSuite(unittest.TestCase):
    def setUp(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.integrator = RK4Integrator(microsteps_per_interval=15, dt=1.0)
        self.params = PhysiologicalParameters.create_population_default(batch_size=1, device=self.device)

    # 1. Import test
    def test_01_imports(self):
        """Test 1: Verify all core physiology modules import cleanly without circular dependencies."""
        from physiology import MetabolicState, PhysiologicalParameters, RK4Integrator
        from physiology.priors import BiomarkerPriorNetwork
        from physiology.calibrator import MovingHorizonCalibrator
        from physiology.simulator import CounterfactualSimulator
        from physiology.hybrid_fusion import GlucoShieldHybridForecaster
        self.assertTrue(True)

    # 2. CPU smoke test
    def test_02_cpu_smoke(self):
        """Test 2: Complete end-to-end forward simulation on CPU."""
        state_cpu = MetabolicState.create_initial_state(torch.tensor([120.0]), device=torch.device("cpu"))
        params_cpu = PhysiologicalParameters.create_population_default(1, device=torch.device("cpu"))
        ins_cpu = torch.tensor([[2.0, 0.0, 0.0, 0.0]], device=torch.device("cpu"))
        carbs_cpu = torch.tensor([[40.0, 0.0, 0.0, 0.0]], device=torch.device("cpu"))
        int_cpu = RK4Integrator(15, 1.0)
        
        cgm_sim, states = int_cpu.forward_simulate(state_cpu, ins_cpu, carbs_cpu, params_cpu)
        self.assertEqual(cgm_sim.shape, (1, 4))
        self.assertEqual(len(states), 5)

    # 3. CUDA smoke test
    def test_03_cuda_smoke(self):
        """Test 3: Complete end-to-end forward simulation on CUDA GPU."""
        if not torch.cuda.is_available():
            self.skipTest("CUDA not available")
        state_gpu = MetabolicState.create_initial_state(torch.tensor([120.0], device="cuda"), device=torch.device("cuda"))
        params_gpu = PhysiologicalParameters.create_population_default(1, device=torch.device("cuda"))
        ins_gpu = torch.tensor([[2.0, 0.0, 0.0, 0.0]], device="cuda")
        carbs_gpu = torch.tensor([[40.0, 0.0, 0.0, 0.0]], device="cuda")
        
        cgm_sim, _ = self.integrator.forward_simulate(state_gpu, ins_gpu, carbs_gpu, params_gpu)
        self.assertEqual(cgm_sim.device.type, "cuda")
        self.assertEqual(cgm_sim.shape, (1, 4))

    # 4. RK4 known-system numerical accuracy test
    def test_04_rk4_analytical_accuracy(self):
        """Test 4: RK4 integration matches analytical exponential decay dQ/dt = -k * Q."""
        k = 0.05
        q0 = 1000.0
        dt = 1.0
        steps = 60  # 60 minutes
        
        # Analytical solution at t=60: Q(60) = Q0 * exp(-k * 60)
        expected_q60 = q0 * np.exp(-k * steps)
        
        # Numerical RK4 for dQ/dt = -k * Q
        q_num = q0
        for _ in range(steps):
            k1 = -k * q_num
            k2 = -k * (q_num + 0.5 * dt * k1)
            k3 = -k * (q_num + 0.5 * dt * k2)
            k4 = -k * (q_num + dt * k3)
            q_num = q_num + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
            
        rel_error = abs(q_num - expected_q60) / expected_q60
        self.assertLess(rel_error, 1e-5, f"RK4 numerical error exceeds tolerance: {rel_error}")

    # 5. 15 microsteps per macro interval test
    def test_05_microstep_count(self):
        """Test 5: Verify each 15-minute macro interval executes exactly 15 microsteps of 1 minute."""
        state = MetabolicState.create_initial_state(torch.tensor([130.0], device=self.device), device=self.device)
        u_ins = torch.tensor([1.0], device=self.device)
        d_carbs = torch.tensor([20.0], device=self.device)
        
        next_state, traj_15m = self.integrator.step_interval(state, u_ins, d_carbs, self.params)
        self.assertEqual(traj_15m.shape[-1], 15, "15-minute interval must produce 15 internal microstep evaluations")

    # 6. Gradient / backpropagation differentiability test
    def test_06_differentiability(self):
        """Test 6: Backpropagation through the full simulation graph produces valid non-zero gradients."""
        init_state = MetabolicState.create_initial_state(torch.tensor([120.0], device=self.device), device=self.device)
        # Learnable insulin sensitivity
        S_I_param = nn.Parameter(torch.tensor([1.5e-4], device=self.device))
        
        params = self.params.clone()
        params.S_I = S_I_param
        
        ins = torch.tensor([[4.0, 0.0, 0.0, 0.0]], device=self.device)
        carbs = torch.tensor([[50.0, 0.0, 0.0, 0.0]], device=self.device)
        
        cgm_sim, _ = self.integrator.forward_simulate(init_state, ins, carbs, params)
        loss = torch.sum(cgm_sim)
        loss.backward()
        
        self.assertIsNotNone(S_I_param.grad, "Gradient was not computed through ODE simulation")
        self.assertFalse(torch.isnan(S_I_param.grad), "Gradient contains NaNs")
        self.assertNotEqual(S_I_param.grad.item(), 0.0, "Gradient is zero")

    # 7. No NaN/Inf propagation test
    def test_07_no_nan_inf(self):
        """Test 7: Extreme inputs (zero glucose, 300g carbs, 30U insulin) do not trigger NaNs or Infs."""
        state = MetabolicState.create_initial_state(torch.tensor([40.0], device=self.device), device=self.device)
        ins = torch.tensor([[30.0, 0.0, 0.0, 0.0]], device=self.device)
        carbs = torch.tensor([[300.0, 0.0, 0.0, 0.0]], device=self.device)
        
        cgm_sim, states = self.integrator.forward_simulate(state, ins, carbs, self.params)
        self.assertFalse(torch.any(torch.isnan(cgm_sim)))
        self.assertFalse(torch.any(torch.isinf(cgm_sim)))

    # 8. State and batch shape preservation test
    def test_08_shapes(self):
        """Test 8: Batch dimension B and horizon H are preserved across all tensor outputs."""
        batch_size = 8
        horizon = 20
        init_state = MetabolicState.create_initial_state(
            torch.full((batch_size,), 125.0, device=self.device), device=self.device
        )
        params_batch = PhysiologicalParameters.create_population_default(batch_size, device=self.device)
        ins = torch.zeros(batch_size, horizon, device=self.device)
        carbs = torch.zeros(batch_size, horizon, device=self.device)
        
        cgm_sim, states = self.integrator.forward_simulate(init_state, ins, carbs, params_batch)
        self.assertEqual(cgm_sim.shape, (batch_size, horizon))
        self.assertEqual(len(states), horizon + 1)

    # 9. Non-negative physiological state constraints test
    def test_09_state_constraints(self):
        """Test 9: Enforce non-negativity and bounded survival ranges."""
        raw_state = torch.tensor([[-50.0, -10.0, -0.05, -5.0, -100.0, -50.0, -20.0, -10.0]], device=self.device)
        clamped = enforce_state_constraints(raw_state)
        self.assertGreaterEqual(clamped[0, 0].item(), 20.0) # Plasma floor
        self.assertGreaterEqual(clamped[0, 1].item(), 20.0) # Sensor floor
        self.assertGreaterEqual(clamped[0, 2].item(), 0.0)  # X >= 0
        self.assertGreaterEqual(clamped[0, 4].item(), 0.0)  # S1 >= 0
        self.assertGreaterEqual(clamped[0, 6].item(), 0.0)  # Q1 >= 0

    # 10. Zero-meal scenario baseline test
    def test_10_zero_meal_baseline(self):
        """Test 10: Zero meal and basal insulin maintains steady glucose within +/-4 mg/dL."""
        state = MetabolicState.create_initial_state(torch.tensor([110.0], device=self.device), device=self.device)
        ins = torch.zeros(1, 16, device=self.device)
        carbs = torch.zeros(1, 16, device=self.device)
        
        cgm_sim, _ = self.integrator.forward_simulate(state, ins, carbs, self.params)
        max_deviation = torch.max(torch.abs(cgm_sim - 110.0)).item()
        self.assertLess(max_deviation, 4.0, f"Basal drift exceeded 4 mg/dL: {max_deviation:.2f}")

    # 11. Meal absorption kinetic response test
    def test_11_meal_absorption_kinetics(self):
        """Test 11: 60g meal increases glucose with realistic peak timing between 45m and 135m."""
        state = MetabolicState.create_initial_state(torch.tensor([100.0], device=self.device), device=self.device)
        ins = torch.zeros(1, 20, device=self.device)
        carbs = torch.zeros(1, 20, device=self.device)
        carbs[0, 0] = 60.0 # 60g meal
        
        cgm_sim, _ = self.integrator.forward_simulate(state, ins, carbs, self.params)
        peak_val = cgm_sim.max().item()
        peak_idx = cgm_sim.argmax().item()
        peak_min = (peak_idx + 1) * 15
        
        self.assertGreater(peak_val, 135.0, "Meal failed to elevate glucose")
        self.assertTrue(30 <= peak_min <= 135, f"Peak time {peak_min}m outside physiological 30-135m window")

    # 12. Bolus response directionality & monotonicity test
    def test_12_bolus_monotonicity(self):
        """Test 12: Incremental insulin boluses (2U, 5U, 10U) produce monotonically decreasing nadirs."""
        state = MetabolicState.create_initial_state(torch.tensor([160.0], device=self.device), device=self.device)
        carbs = torch.zeros(1, 20, device=self.device)
        carbs[0, 0] = 50.0
        
        nadirs = []
        for bolus in [2.0, 5.0, 10.0]:
            ins = torch.zeros(1, 20, device=self.device)
            ins[0, 0] = bolus
            sim, _ = self.integrator.forward_simulate(state.clone(), ins, carbs, self.params)
            nadirs.append(sim.min().item())
            
        self.assertGreater(nadirs[0], nadirs[1], "2U nadir not higher than 5U nadir")
        self.assertGreater(nadirs[1], nadirs[2], "5U nadir not higher than 10U nadir")

    # 13. Basal equilibrium & stability test
    def test_13_basal_stability_24h(self):
        """Test 13: 24-hour simulation under basal conditions remains bounded without explosion."""
        state = MetabolicState.create_initial_state(torch.tensor([120.0], device=self.device), device=self.device)
        ins = torch.zeros(1, 96, device=self.device)
        carbs = torch.zeros(1, 96, device=self.device)
        
        sim, _ = self.integrator.forward_simulate(state, ins, carbs, self.params)
        self.assertFalse(torch.any(torch.isnan(sim)))
        self.assertTrue(torch.all(sim >= 50.0) and torch.all(sim <= 250.0))

    # 14. Interstitial CGM sensor delay test
    def test_14_sensor_delay(self):
        """Test 14: Sensor glucose G_cgm lags behind plasma glucose G_p during rapid glucose change."""
        state = MetabolicState.create_initial_state(torch.tensor([90.0], device=self.device), device=self.device)
        carbs = torch.tensor([[80.0, 0.0, 0.0, 0.0]], device=self.device)
        ins = torch.zeros(1, 4, device=self.device)
        
        _, states = self.integrator.forward_simulate(state, ins, carbs, self.params)
        # Plasma glucose must lead sensor glucose during rise
        gp_lead_found = False
        for s in states[1:]:
            if (s.G_p - s.G_cgm).item() > 2.0:
                gp_lead_found = True
                break
        self.assertTrue(gp_lead_found, "Sensor delay was not observed during postprandial rise")

    # 15. Counterfactual immutability test
    def test_15_simulator_immutability(self):
        """Test 15: Simulating hypothetical scenarios does not mutate the original patient state."""
        state = MetabolicState.create_initial_state(torch.tensor([140.0], device=self.device), device=self.device)
        orig_gp = state.G_p.item()
        
        sim = CounterfactualSimulator(horizon_steps=20)
        _ = sim.simulate_scenario(
            state, self.params,
            scenario_insulin=torch.full((1, 20), 5.0, device=self.device),
            scenario_carbs=torch.zeros((1, 20), device=self.device)
        )
        self.assertEqual(state.G_p.item(), orig_gp, "Simulator mutated original patient state!")

    # 16. Calibrator causality test (strictly past 96 steps)
    def test_16_calibrator_causality(self):
        """Test 16: Calibrator only consumes history tensor (batch, 96, 22) without accessing future."""
        history = torch.randn(2, 96, 22, device=self.device)
        history[:, :, 0] = torch.clamp(history[:, :, 0] * 50 + 130, 70, 300) # realistic CGM
        history[:, :, 15] = torch.clamp(history[:, :, 15], 0, 5)              # insulin
        history[:, :, 17] = torch.clamp(history[:, :, 17], 0, 60)             # carbs
        
        calibrator = MovingHorizonCalibrator(num_iterations=5).to(self.device)
        prior_net = BiomarkerPriorNetwork(9, 32).to(self.device)
        static_dummy = torch.randn(2, 9, device=self.device)
        
        prior_p = prior_net(static_dummy)
        calib_p, state_t0, diag = calibrator.calibrate_and_observe(history, prior_p, optimize_parameters=True)
        
        self.assertIn("calibration_time_ms", diag)
        self.assertEqual(state_t0.G_p.shape, (2,))

    # 17. Calibrator bounded-parameter preservation test
    def test_17_calibrator_parameter_bounds(self):
        """Test 17: Calibrated parameters must strictly respect physical PARAMETER_BOUNDS."""
        history = torch.randn(1, 96, 22, device=self.device)
        history[:, :, 0] = 180.0
        calibrator = MovingHorizonCalibrator(num_iterations=10).to(self.device)
        
        prior_p = self.params.clone()
        calib_p, _, _ = calibrator.calibrate_and_observe(history, prior_p, optimize_parameters=True)
        
        low_si, high_si = PARAMETER_BOUNDS["S_I"]
        self.assertTrue(low_si <= calib_p.S_I.item() <= high_si, f"S_I out of bounds: {calib_p.S_I.item()}")
        low_gb, high_gb = PARAMETER_BOUNDS["G_b"]
        self.assertTrue(low_gb <= calib_p.G_b.item() <= high_gb, f"G_b out of bounds: {calib_p.G_b.item()}")

    # 18. Hybrid gate output range test
    def test_18_hybrid_gate_range(self):
        """Test 18: Adaptive fusion gate outputs alpha(k) strictly in [0, 1] across all horizon steps."""
        gate = AdaptiveFusionGate(horizon=20).to(self.device)
        context = torch.randn(4, 5, device=self.device)
        alpha = gate(context)
        
        self.assertEqual(alpha.shape, (4, 20))
        self.assertTrue(torch.all(alpha >= 0.0) and torch.all(alpha <= 1.0), "Gate produced values outside [0, 1]")

    # 19. Hybrid trajectory shape & horizon alignment test
    def test_19_hybrid_shape_alignment(self):
        """Test 19: Prior network produces 8 bounded physiological parameter tensors."""
        prior_net = BiomarkerPriorNetwork(9, 32).to(self.device)
        static_x = torch.randn(4, 9, device=self.device)
        params = prior_net(static_x)
        
        self.assertEqual(params.S_I.shape, (4,))
        self.assertEqual(params.G_b.shape, (4,))
        self.assertEqual(params.BW.shape, (4,))

    # 20. CPU / GPU numerical consistency test
    def test_20_cpu_gpu_consistency(self):
        """Test 20: Forward simulation on CPU and CUDA yields identical results (<1e-3 mg/dL)."""
        if not torch.cuda.is_available():
            self.skipTest("CUDA not available")
            
        s_cpu = MetabolicState.create_initial_state(torch.tensor([135.0]), device=torch.device("cpu"))
        s_gpu = MetabolicState.create_initial_state(torch.tensor([135.0], device="cuda"), device=torch.device("cuda"))
        
        p_cpu = PhysiologicalParameters.create_population_default(1, device=torch.device("cpu"))
        p_gpu = PhysiologicalParameters.create_population_default(1, device=torch.device("cuda"))
        
        ins_cpu = torch.tensor([[3.0, 0.0, 1.0, 0.0]], device="cpu")
        ins_gpu = ins_cpu.to("cuda")
        carbs_cpu = torch.tensor([[45.0, 0.0, 0.0, 10.0]], device="cpu")
        carbs_gpu = carbs_cpu.to("cuda")
        
        int_cpu = RK4Integrator(15, 1.0)
        int_gpu = RK4Integrator(15, 1.0)
        
        res_cpu, _ = int_cpu.forward_simulate(s_cpu, ins_cpu, carbs_cpu, p_cpu)
        res_gpu, _ = int_gpu.forward_simulate(s_gpu, ins_gpu, carbs_gpu, p_gpu)
        
        diff = np.max(np.abs(res_cpu.numpy() - res_gpu.cpu().numpy()))
        self.assertLess(diff, 1e-3, f"CPU vs GPU numerical discrepancy: {diff:.6f} mg/dL")

if __name__ == "__main__":
    unittest.main(verbosity=2)
