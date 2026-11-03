"""
GlucoShield V2 — Training Package
==================================
Provides loss functions, multi-modal dataset loaders, and experiment runners.
"""

from training.v2.loss_v2 import GlucoShieldLossV2
from training.v2.dataset_v2 import MultiModalGlucoDatasetV2

__all__ = ["GlucoShieldLossV2", "MultiModalGlucoDatasetV2"]
