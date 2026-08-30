"""
GlucoShield Physiology Engine - Tier 1 Static Biomarker Prior Estimator
========================================================================
Maps static clinical biomarkers to bounded physiological parameter priors.
"""

import torch
import torch.nn as nn
from typing import Dict
from physiology.parameters import PhysiologicalParameters
from physiology.constraints import PARAMETER_BOUNDS

class BiomarkerPriorNetwork(nn.Module):
    """
    Differentiable neural prior that estimates baseline physiological parameters
    from a patient's static clinical biomarkers:
      0: Age (years)
      1: BMI (kg/m^2)
      2: HbA1c (mmol/mol)
      3: Glycated Albumin (%)
      4: Fasting Glucose (mg/dL)
      5: Fasting C-peptide (ng/mL)
      6: Macrovascular complications count
      7: Microvascular complications count
      8: is_t1dm (0.0 or 1.0)
    """
    def __init__(self, static_dim: int = 9, hidden_dim: int = 32):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(static_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 8) # Outputs raw logits for 8 learnable parameters
        )
        # Learnable logit offsets initialized near population defaults
        # Parameter order: S_I, S_G, p2, tau_s, k_empt, k_abs, G_b, V_g

    def forward(self, static_features: torch.Tensor) -> PhysiologicalParameters:
        """
        Args:
          static_features: Tensor of shape (batch, 9) [can be raw or scaled]
        Returns:
          PhysiologicalParameters object with bounded parameter tensors (batch,)
        """
        device = static_features.device
        batch_size = static_features.shape[0]

        # Extract specific raw physiological anchors if available
        # Channel 1 is BMI, Channel 4 is Fasting Glucose, Channel 8 is is_t1dm
        bmi = static_features[:, 1]
        fasting_gluc = static_features[:, 4]
        is_t1dm = static_features[:, 8]

        # Estimate patient body weight: BW ~ BMI * (1.70m)^2 = BMI * 2.89
        BW = torch.clamp(bmi * 2.89, min=45.0, max=140.0)

        # Forward through prior network
        logits = self.net(static_features)  # (batch, 8)
        norm_vals = torch.sigmoid(logits)    # (batch, 8) in (0, 1)

        # Project each normalized value into its clinical physiological interval [low, high]
        def scale_param(norm, key):
            low, high = PARAMETER_BOUNDS[key]
            return low + norm * (high - low)

        S_I = scale_param(norm_vals[:, 0], "S_I")
        S_G = scale_param(norm_vals[:, 1], "S_G")
        p2 = scale_param(norm_vals[:, 2], "p2")
        tau_s = scale_param(norm_vals[:, 3], "tau_s")
        k_empt = scale_param(norm_vals[:, 4], "k_empt")
        k_abs = scale_param(norm_vals[:, 5], "k_abs")
        
        # Basal glucose target is anchored around patient's fasting glucose
        G_b_pred = scale_param(norm_vals[:, 6], "G_b")
        # Soft blend with fasting glucose if fasting glucose is in valid range
        G_b = torch.where(
            (fasting_gluc >= 70.0) & (fasting_gluc <= 300.0),
            0.6 * G_b_pred + 0.4 * torch.clamp(fasting_gluc, 70.0, 220.0),
            G_b_pred
        )

        V_g = scale_param(norm_vals[:, 7], "V_g")
        tau_d = torch.full((batch_size,), 10.0, device=device)
        V_I = torch.full((batch_size,), 0.14, device=device)
        k_e = torch.full((batch_size,), 0.12, device=device)
        bioavail = torch.full((batch_size,), 0.88, device=device)
        
        # Beta-cell endogenous response: 0 for T1DM, 0.008 for T2DM
        beta_cell = (1.0 - is_t1dm) * 0.008

        return PhysiologicalParameters(
            S_I=S_I, S_G=S_G, p2=p2, tau_s=tau_s,
            k_empt=k_empt, k_abs=k_abs, tau_d=tau_d,
            G_b=G_b, V_g=V_g, BW=BW, V_I=V_I, k_e=k_e,
            bioavailability=bioavail, beta_cell=beta_cell
        )
