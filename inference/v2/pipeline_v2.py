"""
GlucoShield V2 — Production Inference & Clinical Explanation Pipeline
======================================================================
Executes end-to-end multi-modal inference:
  1. Input validation and causal temporal alignment
  2. Multi-modal physiological telemetry encoding (with missingness safety)
  3. Hybrid forecasting (Factor-aware neural GRU + Mechanistic ODE Digital Twin)
  4. Dynamic context-conditioned fusion gating
  5. Regime-conditioned physical uncertainty interval construction
"""

import os
import torch
import numpy as np
import joblib
from typing import Dict, Any, Optional, Union

from models.v2.context_encoder import PhysiologicalContextBatch
from models.v2.neural_forecaster import GlucoShieldNeuralForecasterV2
from models.v2.hybrid_forecaster_v2 import GlucoShieldHybridForecasterV2

class V2InferencePipeline:
    """
    High-level clinical inference pipeline for GlucoShield V2.
    """
    def __init__(
        self,
        hybrid_model: GlucoShieldHybridForecasterV2,
        feature_scaler_path: str = "data/metadata/feature_scaler.joblib",
        static_scaler_path: str = "data/metadata/static_scaler.joblib",
        device: Optional[torch.device] = None
    ):
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.hybrid_model = hybrid_model.to(self.device)
        self.hybrid_model.eval()

        self.feature_scaler = joblib.load(feature_scaler_path)
        self.static_scaler = joblib.load(static_scaler_path)

    def predict(
        self,
        dynamic_raw: np.ndarray,                                    # (96, 22) or (batch, 96, 22)
        static_raw: np.ndarray,                                     # (9,) or (batch, 9)
        telemetry: Optional[Dict[str, Any]] = None,                 # Factor telemetry
        calibrate_mhe: bool = True
    ) -> Dict[str, Any]:
        """
        Executes causal clinical forecast.
        """
        # Ensure batch dimension
        if dynamic_raw.ndim == 2:
            dynamic_raw = np.expand_dims(dynamic_raw, axis=0)
        if static_raw.ndim == 1:
            static_raw = np.expand_dims(static_raw, axis=0)

        batch_size, T, D = dynamic_raw.shape
        assert T == 96 and D == 22, f"Expected dynamic shape (batch, 96, 22), got {dynamic_raw.shape}"
        assert static_raw.shape[1] == 9, f"Expected static shape (batch, 9), got {static_raw.shape}"

        # 1. Scale inputs
        dyn_flat = dynamic_raw.reshape(-1, D)
        dyn_scaled = self.feature_scaler.transform(dyn_flat).reshape(batch_size, T, D).astype(np.float32)
        stat_scaled = self.static_scaler.transform(static_raw).astype(np.float32)

        t_dyn_s = torch.tensor(dyn_scaled, dtype=torch.float32, device=self.device)
        t_dyn_r = torch.tensor(dynamic_raw, dtype=torch.float32, device=self.device)
        t_stat_s = torch.tensor(stat_scaled, dtype=torch.float32, device=self.device)
        t_stat_r = torch.tensor(static_raw, dtype=torch.float32, device=self.device)

        # 2. Build context batch
        if telemetry is not None:
            f_ex = torch.tensor(telemetry.get("exercise_features", np.zeros((batch_size, 4))), dtype=torch.float32, device=self.device)
            m_ex = torch.tensor(telemetry.get("exercise_mask", np.zeros((batch_size, 1))), dtype=torch.float32, device=self.device)

            f_sl = torch.tensor(telemetry.get("sleep_features", np.zeros((batch_size, 5))), dtype=torch.float32, device=self.device)
            m_sl = torch.tensor(telemetry.get("sleep_mask", np.zeros((batch_size, 1))), dtype=torch.float32, device=self.device)

            f_hm = torch.tensor(telemetry.get("hormonal_features", np.zeros((batch_size, 3))), dtype=torch.float32, device=self.device)
            m_hm = torch.tensor(telemetry.get("hormonal_mask", np.zeros((batch_size, 1))), dtype=torch.float32, device=self.device)

            f_circ = torch.tensor(telemetry.get("circadian_features", np.zeros((batch_size, 4))), dtype=torch.float32, device=self.device)

            ctx_batch = PhysiologicalContextBatch(
                f_exercise=f_ex, m_exercise=m_ex,
                f_sleep=f_sl, m_sleep=m_sl,
                f_hormonal=f_hm, m_hormonal=m_hm,
                f_circadian=f_circ
            )
        else:
            ctx_batch = PhysiologicalContextBatch.create_empty(batch_size, device=self.device)

        # 3. Model Forward Pass
        with torch.no_grad():
            out = self.hybrid_model(
                dynamic_seq_scaled=t_dyn_s,
                dynamic_seq_raw=t_dyn_r,
                static_feat_scaled=t_stat_s,
                static_feat_raw=t_stat_r,
                context_batch=ctx_batch,
                calibrate=calibrate_mhe
            )

        traj = out["trajectory"].cpu().numpy()
        alpha = out["alpha"].cpu().numpy()
        p_int = out["prediction_interval"]
        risks = out["risk_probs"].cpu().numpy()

        return {
            "trajectory": traj,
            "y_neural": out["y_neural"].cpu().numpy(),
            "y_ode": out["y_ode"].cpu().numpy(),
            "fusion_alpha": alpha,
            "lower_80": p_int.lower_80.cpu().numpy(),
            "upper_80": p_int.upper_80.cpu().numpy(),
            "lower_95": p_int.lower_95.cpu().numpy(),
            "upper_95": p_int.upper_95.cpu().numpy(),
            "std_uncertainty": p_int.std_uncertainty.cpu().numpy(),
            "sigma_regime": p_int.sigma_regime.cpu().numpy(),
            "sigma_epistemic": p_int.sigma_epistemic.cpu().numpy(),
            "sigma_disagree": p_int.sigma_disagree.cpu().numpy(),
            "acute_risks": {
                "hypo_1h": risks[:, 0],
                "hypo_2h": risks[:, 1],
                "hypo_4h": risks[:, 2],
                "hyper_2h": risks[:, 3],
                "hyper_4h": risks[:, 4]
            }
        }
