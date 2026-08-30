"""
GlucoShield Neural Dataset & DataLoader Interface
Provides batching for dynamic sequences, static patient features, trajectory targets, and risk labels.
"""

import os
import numpy as np
import pandas as pd
import torch
from torch.utils.data import TensorDataset, DataLoader

def load_in_memory_dataset(data_dir="data/final", split="train", use_scaled_inputs=True):
    feat_suffix = "scaled" if use_scaled_inputs else "raw"
    X = torch.from_numpy(np.load(os.path.join(data_dir, f"X_{split}_{feat_suffix}.npy"))).float().contiguous()
    static = torch.from_numpy(np.load(os.path.join(data_dir, f"static_{split}_{feat_suffix}.npy"))).float().contiguous()
    Y_traj = torch.from_numpy(np.load(os.path.join(data_dir, f"Y_{split}_trajectory.npy"))).float().contiguous()

    y_h1 = np.load(os.path.join(data_dir, f"Y_{split}_hypo_1h.npy")).astype(np.float32)
    y_h2 = np.load(os.path.join(data_dir, f"Y_{split}_hypo_2h.npy")).astype(np.float32)
    y_h4 = np.load(os.path.join(data_dir, f"Y_{split}_hypo_4h.npy")).astype(np.float32)
    y_hyp2 = np.load(os.path.join(data_dir, f"Y_{split}_hyper_2h.npy")).astype(np.float32)
    y_hyp4 = np.load(os.path.join(data_dir, f"Y_{split}_hyper_4h.npy")).astype(np.float32)

    Y_risk = torch.from_numpy(np.stack([y_h1, y_h2, y_h4, y_hyp2, y_hyp4], axis=1)).float().contiguous()
    return TensorDataset(X, static, Y_traj, Y_risk)

def compute_training_pos_weights(data_dir="data/final"):
    y_h1 = np.load(os.path.join(data_dir, "Y_train_hypo_1h.npy"))
    y_h2 = np.load(os.path.join(data_dir, "Y_train_hypo_2h.npy"))
    y_h4 = np.load(os.path.join(data_dir, "Y_train_hypo_4h.npy"))
    y_hyp2 = np.load(os.path.join(data_dir, "Y_train_hyper_2h.npy"))
    y_hyp4 = np.load(os.path.join(data_dir, "Y_train_hyper_4h.npy"))

    targets = [y_h1, y_h2, y_h4, y_hyp2, y_hyp4]
    pos_weights = []
    for t in targets:
        n_pos = np.sum(t == 1.0)
        n_neg = np.sum(t == 0.0)
        pw = (n_neg / max(n_pos, 1.0))
        smoothed_pw = float(np.sqrt(pw))
        pos_weights.append(smoothed_pw)

    return torch.tensor(pos_weights, dtype=torch.float32)

def get_neural_dataloaders(data_dir="data/final", batch_size=256, num_workers=0):
    train_ds = load_in_memory_dataset(data_dir=data_dir, split="train", use_scaled_inputs=True)
    val_ds = load_in_memory_dataset(data_dir=data_dir, split="val", use_scaled_inputs=True)
    test_ds = load_in_memory_dataset(data_dir=data_dir, split="test", use_scaled_inputs=True)

    use_pin = torch.cuda.is_available()
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, pin_memory=use_pin)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, pin_memory=use_pin)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False, pin_memory=use_pin)

    return train_loader, val_loader, test_loader
