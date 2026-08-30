"""
GlucoShield Baseline C: Classical Machine Learning Forecaster
Extracts causal summary features from past 24h history and trains regularized linear/tree models.
"""

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

def extract_causal_summary_features(X_raw, static_raw=None):
    """
    Extracts summary statistics from past 96 steps of history and static features.
    
    Args:
        X_raw: np.ndarray of shape (N, 96, 22) - unscaled raw features
        static_raw: np.ndarray of shape (N, 9) - raw static clinical features
    Returns:
        features: np.ndarray of shape (N, n_features)
    """
    N, T, _ = X_raw.shape
    g_seq = X_raw[:, :, 0]  # glucose history (N, 96)

    # 1. Current state
    curr_g = g_seq[:, -1:]  # (N, 1)

    # 2. Causal rolling means
    mean_1h = np.mean(g_seq[:, -4:], axis=1, keepdims=True)
    mean_3h = np.mean(g_seq[:, -12:], axis=1, keepdims=True)
    mean_6h = np.mean(g_seq[:, -24:], axis=1, keepdims=True)
    mean_12h = np.mean(g_seq[:, -48:], axis=1, keepdims=True)
    mean_24h = np.mean(g_seq[:, -96:], axis=1, keepdims=True)

    # 3. Causal rolling stds
    std_1h = np.std(g_seq[:, -4:], axis=1, keepdims=True)
    std_3h = np.std(g_seq[:, -12:], axis=1, keepdims=True)
    std_6h = np.std(g_seq[:, -24:], axis=1, keepdims=True)
    std_24h = np.std(g_seq[:, -96:], axis=1, keepdims=True)

    # 4. Extremes
    min_1h = np.min(g_seq[:, -4:], axis=1, keepdims=True)
    max_1h = np.max(g_seq[:, -4:], axis=1, keepdims=True)
    min_24h = np.min(g_seq[:, -96:], axis=1, keepdims=True)
    max_24h = np.max(g_seq[:, -96:], axis=1, keepdims=True)

    # 5. Slopes over past 1h, 2h, 4h
    slope_1h = (g_seq[:, -1:] - g_seq[:, -5:-4]) / 4.0
    slope_2h = (g_seq[:, -1:] - g_seq[:, -9:-8]) / 8.0
    slope_4h = (g_seq[:, -1:] - g_seq[:, -17:-16]) / 16.0

    # 6. Kinematic velocity & accel
    last_vel = X_raw[:, -1:, 1]
    last_acc = X_raw[:, -1:, 2]

    # 7. Circadian features
    sin_hr = X_raw[:, -1:, 10]
    cos_hr = X_raw[:, -1:, 11]
    is_night = X_raw[:, -1:, 12]

    # 8. Pharmacokinetics and Nutrition
    last_iob = X_raw[:, -1:, 16]
    last_cob = X_raw[:, -1:, 19]
    insulin_cum_2h = np.sum(X_raw[:, -8:, 15], axis=1, keepdims=True)
    carbs_cum_2h = np.sum(X_raw[:, -8:, 17], axis=1, keepdims=True)

    feature_list = [
        curr_g, mean_1h, mean_3h, mean_6h, mean_12h, mean_24h,
        std_1h, std_3h, std_6h, std_24h,
        min_1h, max_1h, min_24h, max_24h,
        slope_1h, slope_2h, slope_4h,
        last_vel, last_acc,
        sin_hr, cos_hr, is_night,
        last_iob, last_cob, insulin_cum_2h, carbs_cum_2h
    ]

    if static_raw is not None:
        feature_list.append(static_raw)

    X_summary = np.concatenate(feature_list, axis=1)
    return X_summary.astype(np.float32)


class ClassicalMLForecaster:
    def __init__(self, model_type="ridge", alpha=100.0, horizon=20, clamp_range=(20.0, 600.0)):
        self.model_type = model_type
        self.alpha = alpha
        self.horizon = horizon
        self.clamp_range = clamp_range
        self.name = f"ClassicalML_{model_type.upper()}_alpha_{alpha}"
        
        self.scaler = StandardScaler()
        if model_type == "ridge":
            self.model = Ridge(alpha=alpha, random_state=42)
        else:
            raise ValueError(f"Unsupported model_type: {model_type}")

    def fit(self, X_train_raw, Y_train_traj, static_train_raw=None):
        """
        Fits scaler and multi-output regressor on training data only.
        """
        X_feat = extract_causal_summary_features(X_train_raw, static_train_raw)
        X_scaled = self.scaler.fit_transform(X_feat)
        self.model.fit(X_scaled, Y_train_traj)
        return self

    def predict(self, X_raw, static_raw=None):
        """
        Predicts 20 future glucose steps.
        """
        X_feat = extract_causal_summary_features(X_raw, static_raw)
        X_scaled = self.scaler.transform(X_feat)
        Y_pred = self.model.predict(X_scaled)
        if self.clamp_range is not None:
            Y_pred = np.clip(Y_pred, self.clamp_range[0], self.clamp_range[1])
        return Y_pred.astype(np.float32)
