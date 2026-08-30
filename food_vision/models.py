"""
GlucoShield Food Vision Models
==============================
Provides MobileNetV3-Large and EfficientNet-B0 multi-output regression architectures
for estimating meal macronutrients [Carbohydrates (g), Protein (g), Fat (g), Calories (kcal)]
from 2D RGB meal photographs. Includes Monte Carlo Dropout uncertainty estimation.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models
from typing import Dict, Tuple, Optional

class MacronutrientRegressor(nn.Module):
    """
    Deep Convolutional Multi-Output Regression Network.
    
    Backbone: MobileNetV3-Large (or EfficientNet-B0)
    Head: 2-Layer MLP with LayerNorm, ReLU, Dropout, and Non-Negative Clamping.
    Outputs:
      - carbs_g: Carbohydrates in grams (>= 0.0)
      - protein_g: Protein in grams (>= 0.0)
      - fat_g: Total Fat in grams (>= 0.0)
      - calories_kcal: Total Energy in kcal (>= 0.0)
    """
    def __init__(
        self,
        backbone_name: str = "mobilenet_v3_large",
        pretrained: bool = False,
        hidden_dim: int = 256,
        dropout_p: float = 0.2,
        num_targets: int = 4
    ):
        super().__init__()
        self.backbone_name = backbone_name.lower()
        self.num_targets = num_targets
        self.dropout_p = dropout_p

        # 1. Instantiate Vision Backbone
        if "mobilenet" in self.backbone_name:
            weights = models.MobileNet_V3_Large_Weights.DEFAULT if pretrained else None
            base_model = models.mobilenet_v3_large(weights=weights)
            self.features = base_model.features
            self.pool = nn.AdaptiveAvgPool2d((1, 1))
            in_features = 960  # MobileNetV3-Large output channels
        elif "efficientnet" in self.backbone_name:
            weights = models.EfficientNet_B0_Weights.DEFAULT if pretrained else None
            base_model = models.efficientnet_b0(weights=weights)
            self.features = base_model.features
            self.pool = nn.AdaptiveAvgPool2d((1, 1))
            in_features = 1280
        else:
            raise ValueError(f"Unsupported backbone: {backbone_name}. Choose 'mobilenet_v3_large' or 'efficientnet_b0'.")

        # 2. Multi-Macronutrient Regression Head
        self.head = nn.Sequential(
            nn.Linear(in_features, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(p=dropout_p),
            nn.Linear(hidden_dim, 64),
            nn.ReLU(inplace=True),
            nn.Linear(64, num_targets)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
          x: RGB Image Tensor of shape (batch, 3, H, W), normalized via ImageNet stats.
        Returns:
          preds: Non-negative predictions tensor of shape (batch, 4) -> [carbs, protein, fat, calories]
        """
        feat = self.features(x)
        pooled = self.pool(feat).flatten(1)
        raw_out = self.head(pooled)
        # Enforce physical non-negativity: macronutrients and calories cannot be negative
        preds = F.relu(raw_out)
        return preds

    def predict_with_uncertainty(
        self,
        x: torch.Tensor,
        num_mc_samples: int = 10
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Computes predictive mean and epistemic uncertainty via Monte Carlo Dropout.
        
        Args:
          x: Input image tensor (batch, 3, H, W)
          num_mc_samples: Number of stochastic forward passes
        Returns:
          mean_preds: Tensor of shape (batch, 4)
          std_preds: Tensor of shape (batch, 4) (standard deviation / confidence interval width)
        """
        self.train()  # Enable dropout during inference
        mc_outputs = []
        with torch.no_grad():
            for _ in range(num_mc_samples):
                out = self.forward(x)
                mc_outputs.append(out)
        self.eval()

        stacked = torch.stack(mc_outputs, dim=0)  # (samples, batch, 4)
        mean_preds = torch.mean(stacked, dim=0)
        std_preds = torch.std(stacked, dim=0)
        return mean_preds, std_preds


class MultiTaskMacronutrientLoss(nn.Module):
    """
    Weighted Smooth L1 (Huber) Loss balancing disparate macronutrient and caloric scales.
    """
    def __init__(
        self,
        w_carb: float = 1.0,
        w_prot: float = 0.5,
        w_fat: float = 0.5,
        w_cal: float = 0.05,
        beta: float = 5.0
    ):
        super().__init__()
        self.w_carb = w_carb
        self.w_prot = w_prot
        self.w_fat = w_fat
        self.w_cal = w_cal
        self.huber = nn.SmoothL1Loss(beta=beta, reduction="none")

    def forward(self, preds: torch.Tensor, targets: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        preds, targets: (batch, 4) -> [carbs, protein, fat, calories]
        """
        loss_matrix = self.huber(preds, targets)  # (batch, 4)
        
        l_carb = torch.mean(loss_matrix[:, 0])
        l_prot = torch.mean(loss_matrix[:, 1])
        l_fat  = torch.mean(loss_matrix[:, 2])
        l_cal  = torch.mean(loss_matrix[:, 3])

        total_loss = (
            self.w_carb * l_carb +
            self.w_prot * l_prot +
            self.w_fat  * l_fat +
            self.w_cal  * l_cal
        )

        return {
            "total_loss": total_loss,
            "loss_carbs": l_carb,
            "loss_protein": l_prot,
            "loss_fat": l_fat,
            "loss_calories": l_cal
        }
