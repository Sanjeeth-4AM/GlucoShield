"""
GlucoShield Phase 13 — Patient-Specific Online ODE Parameter Adapter
=====================================================================
Implements causal, online recursive parameter adaptation for Hovorka ODE parameters
(primarily Insulin Sensitivity S_I and Basal Target G_b) under free-living telemetry.

Governance:
  - Does NOT alter V1 or V2 model weights.
  - Does NOT alter Hovorka differential equations.
  - Zero model retraining.
  - Strictly causal: relies only on observations up to forecast origin t.
  - Enforces physical parameter bounds at every step:
      S_I in [1.0e-5, 5.0e-3]
      G_b in [70.0, 220.0]
"""

import numpy as np
import torch
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

@dataclass
class PatientOdeConfig:
    """Hyperparameters for causal online ODE parameter adaptation."""
    adapt_si: bool = True
    adapt_gb: bool = False
    eta_si: float = 0.04
    eta_gb: float = 0.0
    beta: float = 0.70
    clip_si: float = 0.10
    clip_gb: float = 5.0
    deadband: float = 3.0
    insulin_iob_threshold: float = 0.20
    insulin_rate_threshold: float = 0.10
    si_bounds: Tuple[float, float] = (1.0e-5, 5.0e-3)
    gb_bounds: Tuple[float, float] = (70.0, 220.0)
    base_si: float = 0.002869
    base_gb: float = 141.79

@dataclass
class ParticipantState:
    """Tracks sequential parameters and audit telemetry for a single participant."""
    pid: str
    si_curr: float
    gb_curr: float
    base_si: float
    base_gb: float
    history_si: List[float] = field(default_factory=list)
    history_gb: List[float] = field(default_factory=list)
    history_res: List[float] = field(default_factory=list)
    adapt_count: int = 0
    clip_count: int = 0
    total_windows: int = 0

class PatientOdeAdapter:
    """
    Online causal estimator for patient-specific ODE parameters.
    Processes sequential window streams per participant and enforces physical invariants.
    """
    def __init__(self, config: Optional[PatientOdeConfig] = None):
        self.config = config or PatientOdeConfig()
        self.participant_states: Dict[str, ParticipantState] = {}

    def reset(self):
        """Clears all participant states."""
        self.participant_states.clear()

    def get_or_create_state(self, pid: str) -> ParticipantState:
        if pid not in self.participant_states:
            self.participant_states[pid] = ParticipantState(
                pid=pid,
                si_curr=self.config.base_si,
                gb_curr=self.config.base_gb,
                base_si=self.config.base_si,
                base_gb=self.config.base_gb
            )
        return self.participant_states[pid]

    def update_window(
        self,
        pid: str,
        cgm_recent_4: np.ndarray,
        prev_ode_pred_4: Optional[np.ndarray],
        iob_recent_4: np.ndarray,
        ins_recent_4: np.ndarray
    ) -> Tuple[float, float, Dict[str, Any]]:
        """
        Updates parameters causally at the forecast origin of window k.
        Returns:
          (si_curr, gb_curr, diag_dict)
        """
        state = self.get_or_create_state(pid)
        state.total_windows += 1

        res_innov = 0.0
        adapted_this_step = False
        clipped_this_step = False

        if prev_ode_pred_4 is not None:
            # Innovation residual over the 4 macro-steps elapsed since previous forecast
            res_innov = float(np.mean(cgm_recent_4 - prev_ode_pred_4[:4]))

            # Guard against NaN/Inf
            if np.isnan(res_innov) or np.isinf(res_innov):
                # Reset to prior on numerical corruption
                state.si_curr = self.config.base_si
                state.gb_curr = self.config.base_gb
                res_innov = 0.0

            elif np.abs(res_innov) > self.config.deadband:
                effective_res = res_innov - np.sign(res_innov) * self.config.deadband

                # 1. Adapt S_I (Insulin Sensitivity)
                if self.config.adapt_si:
                    iob_mean = float(np.mean(iob_recent_4))
                    ins_sum = float(np.sum(ins_recent_4))
                    if iob_mean > self.config.insulin_iob_threshold or ins_sum > self.config.insulin_rate_threshold:
                        adapted_this_step = True
                        ins_scale = float(np.clip(iob_mean / 1.0, 0.2, 1.0))
                        delta_log_si = -self.config.eta_si * (effective_res / 50.0) * ins_scale
                        if np.abs(delta_log_si) > self.config.clip_si:
                            clipped_this_step = True
                            delta_log_si = float(np.clip(delta_log_si, -self.config.clip_si, self.config.clip_si))
                        cand_si = float(np.clip(state.si_curr * np.exp(delta_log_si), self.config.si_bounds[0], self.config.si_bounds[1]))
                        state.si_curr = self.config.beta * state.si_curr + (1.0 - self.config.beta) * cand_si

                # 2. Adapt G_b (Basal Equilibrium)
                if self.config.adapt_gb:
                    adapted_this_step = True
                    delta_gb = self.config.eta_gb * effective_res
                    if np.abs(delta_gb) > self.config.clip_gb:
                        clipped_this_step = True
                        delta_gb = float(np.clip(delta_gb, -self.config.clip_gb, self.config.clip_gb))
                    cand_gb = float(np.clip(state.gb_curr + delta_gb, self.config.gb_bounds[0], self.config.gb_bounds[1]))
                    state.gb_curr = self.config.beta * state.gb_curr + (1.0 - self.config.beta) * cand_gb

        # Final safety bounds invariant
        state.si_curr = float(np.clip(state.si_curr, self.config.si_bounds[0], self.config.si_bounds[1]))
        state.gb_curr = float(np.clip(state.gb_curr, self.config.gb_bounds[0], self.config.gb_bounds[1]))

        if adapted_this_step:
            state.adapt_count += 1
        if clipped_this_step:
            state.clip_count += 1

        state.history_si.append(state.si_curr)
        state.history_gb.append(state.gb_curr)
        state.history_res.append(res_innov)

        diag = {
            "res_innov": res_innov,
            "adapted": adapted_this_step,
            "clipped": clipped_this_step
        }
        return state.si_curr, state.gb_curr, diag

    def process_stream(
        self,
        pids: np.ndarray,
        dyn_raw: np.ndarray,
        ode_proxy_predictions: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
        """
        Processes a full sequential telemetry stream window-by-window.
        """
        N = len(pids)
        adapted_si = np.empty(N, dtype=np.float32)
        adapted_gb = np.empty(N, dtype=np.float32)

        prev_pid = None
        prev_ode = None

        for i in range(N):
            pid = pids[i]
            if pid != prev_pid:
                prev_ode = None
                prev_pid = pid

            cgm_4 = dyn_raw[i, -4:, 0]
            iob_4 = dyn_raw[i, -4:, 16]
            ins_4 = dyn_raw[i, -4:, 15]

            si, gb, _ = self.update_window(
                pid=pid,
                cgm_recent_4=cgm_4,
                prev_ode_pred_4=prev_ode,
                iob_recent_4=iob_4,
                ins_recent_4=ins_4
            )
            adapted_si[i] = si
            adapted_gb[i] = gb

            # Store ODE prediction for next window
            prev_ode = ode_proxy_predictions[i]

        return adapted_si, adapted_gb, self.get_audit_summary()

    def get_audit_summary(self) -> Dict[str, Any]:
        """Aggregates parameter audit statistics across all participants."""
        summary = {}
        for pid, state in self.participant_states.items():
            si_arr = np.array(state.history_si)
            gb_arr = np.array(state.history_gb)
            summary[pid] = {
                "base_si": state.base_si,
                "median_si": float(np.median(si_arr)),
                "iqr_si": float(np.percentile(si_arr, 75) - np.percentile(si_arr, 25)),
                "min_si": float(np.min(si_arr)),
                "max_si": float(np.max(si_arr)),
                "max_abs_si_change": float(np.max(np.abs(si_arr - state.base_si))),
                "base_gb": state.base_gb,
                "median_gb": float(np.median(gb_arr)),
                "iqr_gb": float(np.percentile(gb_arr, 75) - np.percentile(gb_arr, 25)),
                "min_gb": float(np.min(gb_arr)),
                "max_gb": float(np.max(gb_arr)),
                "max_abs_gb_change": float(np.max(np.abs(gb_arr - state.base_gb))),
                "total_windows": state.total_windows,
                "adapt_count": state.adapt_count,
                "adapt_pct": float(state.adapt_count / max(1, state.total_windows) * 100.0),
                "clip_count": state.clip_count,
                "clip_pct": float(state.clip_count / max(1, state.total_windows) * 100.0),
                "stability_si_std": float(np.std(si_arr)),
                "stability_gb_std": float(np.std(gb_arr))
            }
        return summary
