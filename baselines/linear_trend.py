"""
GlucoShield Baseline B: Causal Linear Trend Forecaster
Fits a linear slope over past W timesteps of glucose and extrapolates forward 20 timesteps.
"""

import numpy as np

class LinearTrendForecaster:
    def __init__(self, lookback_steps=4, horizon=20, glucose_idx=0, clamp_range=(20.0, 600.0)):
        """
        Args:
            lookback_steps: Number of past timesteps used to compute trend (e.g. 4 = 1h, 8 = 2h, 16 = 4h).
            horizon: Number of future steps to forecast (default: 20 = 5h).
            glucose_idx: Feature index of glucose in input tensor.
            clamp_range: (min_val, max_val) to avoid unphysical unbounded extrapolation.
        """
        self.lookback_steps = lookback_steps
        self.horizon = horizon
        self.glucose_idx = glucose_idx
        self.clamp_range = clamp_range
        self.name = f"LinearTrend_Lookback_{lookback_steps}steps"

    def fit(self, X_train, Y_train=None):
        # Non-parametric / closed-form OLS per sample
        return self

    def predict(self, X):
        """
        Args:
            X: np.ndarray of shape (N, T_in, F)
        Returns:
            Y_pred: np.ndarray of shape (N, horizon)
        """
        N, T_in, _ = X.shape
        W = self.lookback_steps
        assert T_in >= W, f"Input sequence length {T_in} is smaller than lookback {W}"

        # Extract glucose slice over lookback window
        # shape: (N, W)
        glucose_window = X[:, -W:, self.glucose_idx]
        
        # Time steps: 0, 1, ..., W-1
        tau = np.arange(W, dtype=np.float32)
        tau_mean = np.mean(tau)
        tau_diff = tau - tau_mean
        denom = np.sum(tau_diff ** 2)

        # Vectorized OLS slope computation across N samples
        g_mean = np.mean(glucose_window, axis=1, keepdims=True)  # (N, 1)
        g_diff = glucose_window - g_mean                        # (N, W)
        slope = np.sum(g_diff * tau_diff, axis=1) / denom       # (N,)

        last_glucose = glucose_window[:, -1]                     # (N,)

        # Extrapolate for k = 1, 2, ..., horizon
        k_steps = np.arange(1, self.horizon + 1, dtype=np.float32) # (horizon,)
        # Broadcast: (N, 1) + (N, 1) * (1, horizon) -> (N, horizon)
        Y_pred = last_glucose[:, np.newaxis] + slope[:, np.newaxis] * k_steps[np.newaxis, :]

        if self.clamp_range is not None:
            Y_pred = np.clip(Y_pred, self.clamp_range[0], self.clamp_range[1])

        return Y_pred.astype(np.float32)
