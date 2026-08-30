"""
GlucoShield Baseline A: Naive Persistence Forecaster
Predicts future 20 glucose steps by repeating the last observed glucose reading.
"""

import numpy as np

class PersistenceForecaster:
    def __init__(self, horizon=20, glucose_idx=0):
        self.horizon = horizon
        self.glucose_idx = glucose_idx
        self.name = "Persistence"

    def fit(self, X_train, Y_train=None):
        # Persistence has no parameters to fit
        return self

    def predict(self, X):
        """
        Args:
            X: np.ndarray of shape (N, T_in, F)
        Returns:
            Y_pred: np.ndarray of shape (N, horizon)
        """
        # Extract last observed glucose reading
        last_glucose = X[:, -1, self.glucose_idx]  # shape (N,)
        # Broadcast across horizon
        Y_pred = np.repeat(last_glucose[:, np.newaxis], self.horizon, axis=1)
        return Y_pred.astype(np.float32)
