"""
GlucoShield Physiology Engine - Hybrid Dataset & DataLoader
===========================================================
Provides fast in-memory batches containing paired scaled tensors (for neural models)
and raw physical tensors (for ODE physics models).
"""

import os
import torch
import numpy as np
from torch.utils.data import TensorDataset, DataLoader

def load_hybrid_dataset(data_dir: str = "data/final", split: str = "train"):
    """
    Loads both scaled and raw tensors for the given split.
    Returns:
      TensorDataset yielding:
        0: X_scaled (96, 22)
        1: X_raw (96, 22)
        2: static_scaled (9,)
        3: static_raw (9,)
        4: Y_traj (20,)
        5: Y_risk (5,)
    """
    X_scaled = torch.from_numpy(np.load(os.path.join(data_dir, f"X_{split}_scaled.npy"))).float().contiguous()
    X_raw = torch.from_numpy(np.load(os.path.join(data_dir, f"X_{split}_raw.npy"))).float().contiguous()
    static_scaled = torch.from_numpy(np.load(os.path.join(data_dir, f"static_{split}_scaled.npy"))).float().contiguous()
    static_raw = torch.from_numpy(np.load(os.path.join(data_dir, f"static_{split}_raw.npy"))).float().contiguous()
    Y_traj = torch.from_numpy(np.load(os.path.join(data_dir, f"Y_{split}_trajectory.npy"))).float().contiguous()

    y_h1 = np.load(os.path.join(data_dir, f"Y_{split}_hypo_1h.npy")).astype(np.float32)
    y_h2 = np.load(os.path.join(data_dir, f"Y_{split}_hypo_2h.npy")).astype(np.float32)
    y_h4 = np.load(os.path.join(data_dir, f"Y_{split}_hypo_4h.npy")).astype(np.float32)
    y_hyp2 = np.load(os.path.join(data_dir, f"Y_{split}_hyper_2h.npy")).astype(np.float32)
    y_hyp4 = np.load(os.path.join(data_dir, f"Y_{split}_hyper_4h.npy")).astype(np.float32)
    Y_risk = torch.from_numpy(np.stack([y_h1, y_h2, y_h4, y_hyp2, y_hyp4], axis=1)).float().contiguous()

    return TensorDataset(X_scaled, X_raw, static_scaled, static_raw, Y_traj, Y_risk)

def get_hybrid_dataloaders(data_dir: str = "data/final", batch_size: int = 128):
    """Creates PyTorch DataLoaders for Train, Validation, and Test splits."""
    train_ds = load_hybrid_dataset(data_dir, "train")
    val_ds = load_hybrid_dataset(data_dir, "val")
    test_ds = load_hybrid_dataset(data_dir, "test")

    use_pin = torch.cuda.is_available()
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, pin_memory=use_pin)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, pin_memory=use_pin)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False, pin_memory=use_pin)

    return train_loader, val_loader, test_loader
