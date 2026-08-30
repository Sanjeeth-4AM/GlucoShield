"""
GlucoShield Food Vision Baselines
=================================
Reference baseline predictors for multi-macronutrient regression:
  1. Mean Predictor (Dataset Average)
  2. Median Predictor (Dataset Median)
  3. Color & Texture Ridge Predictor (Classical image feature baseline)
"""

import numpy as np
from sklearn.linear_model import Ridge
from typing import Dict, Any, Tuple

class MeanMacronutrientBaseline:
    """Predicts empirical mean of training set targets."""
    def __init__(self):
        self.means = None

    def fit(self, y_train: np.ndarray):
        """y_train: (N, 4) -> [carbs, protein, fat, calories]"""
        self.means = np.mean(y_train, axis=0)

    def predict(self, n_samples: int) -> np.ndarray:
        return np.tile(self.means, (n_samples, 1))


class MedianMacronutrientBaseline:
    """Predicts empirical median of training set targets."""
    def __init__(self):
        self.medians = None

    def fit(self, y_train: np.ndarray):
        """y_train: (N, 4) -> [carbs, protein, fat, calories]"""
        self.medians = np.median(y_train, axis=0)

    def predict(self, n_samples: int) -> np.ndarray:
        return np.tile(self.medians, (n_samples, 1))


class ColorTextureRidgeBaseline:
    """
    Classical baseline extracting simple global color moments (mean, std, skew)
    and fitting a multi-output Ridge regressor.
    """
    def __init__(self, alpha: float = 1.0):
        self.alpha = alpha
        self.models = [Ridge(alpha=alpha) for _ in range(4)]

    def extract_features(self, images_np: np.ndarray) -> np.ndarray:
        """
        images_np: (N, H, W, 3) or (N, 3, H, W) in [0, 1]
        """
        if images_np.shape[1] == 3:
            images_np = np.transpose(images_np, (0, 2, 3, 1))
        
        feats = []
        for img in images_np:
            r_mean, g_mean, b_mean = np.mean(img, axis=(0, 1))
            r_std, g_std, b_std = np.std(img, axis=(0, 1))
            r_max, g_max, b_max = np.max(img, axis=(0, 1))
            feats.append([r_mean, g_mean, b_mean, r_std, g_std, b_std, r_max, g_max, b_max])
        return np.array(feats, dtype=np.float32)

    def fit(self, images_np: np.ndarray, y_train: np.ndarray):
        x_feat = self.extract_features(images_np)
        for i in range(4):
            self.models[i].fit(x_feat, y_train[:, i])

    def predict(self, images_np: np.ndarray) -> np.ndarray:
        x_feat = self.extract_features(images_np)
        preds = np.zeros((len(images_np), 4), dtype=np.float32)
        for i in range(4):
            preds[:, i] = np.clip(self.models[i].predict(x_feat), a_min=0.0, a_max=None)
        return preds
