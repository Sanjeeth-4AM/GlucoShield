"""
GlucoShield PyTorch Dataset & DataLoader Interface
Provides clean, leakage-safe dataset classes and dataloaders for the final processed tensors.
"""

import os
import json
import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader

class GlucoShieldDataset(Dataset):
    """
    Leakage-safe PyTorch Dataset for GlucoShield multi-horizon forecasting & event classification.
    """
    def __init__(self, data_dir="data/final", split="train", scaled=True, target_type="both"):
        """
        Args:
            data_dir: Path to directory containing final split tensors.
            split: 'train', 'val', or 'test'.
            scaled: If True, loads RobustScaler-normalized features; else raw features.
            target_type: 'trajectory' (continuous curve), 'events' (binary hypo/hyper), or 'both'.
        """
        self.split = split
        self.target_type = target_type

        feat_suffix = "scaled" if scaled else "raw"
        x_path = os.path.join(data_dir, f"X_{split}_{feat_suffix}.npy")
        static_path = os.path.join(data_dir, f"static_{split}_{feat_suffix}.npy")
        traj_path = os.path.join(data_dir, f"Y_{split}_trajectory.npy")
        h1_path = os.path.join(data_dir, f"Y_{split}_hypo_1h.npy")
        h2_path = os.path.join(data_dir, f"Y_{split}_hypo_2h.npy")
        h4_path = os.path.join(data_dir, f"Y_{split}_hypo_4h.npy")
        hyper4_path = os.path.join(data_dir, f"Y_{split}_hyper_4h.npy")
        meta_path = os.path.join(data_dir, f"meta_{split}.csv")

        if not os.path.exists(x_path):
            raise FileNotFoundError(f"Tensor file not found: {x_path}. Ensure build_final_dataset.py has been run.")

        self.X = np.load(x_path)
        self.static = np.load(static_path)
        self.Y_traj = np.load(traj_path)
        self.Y_hypo_1h = np.load(h1_path)
        self.Y_hypo_2h = np.load(h2_path)
        self.Y_hypo_4h = np.load(h4_path)
        self.Y_hyper_4h = np.load(hyper4_path)
        self.meta = pd.read_csv(meta_path)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        x_seq = torch.tensor(self.X[idx], dtype=torch.float32)
        static_feat = torch.tensor(self.static[idx], dtype=torch.float32)
        y_traj = torch.tensor(self.Y_traj[idx], dtype=torch.float32)
        y_hypo_4h = torch.tensor(self.Y_hypo_4h[idx], dtype=torch.float32)
        y_hyper_4h = torch.tensor(self.Y_hyper_4h[idx], dtype=torch.float32)

        if self.target_type == "trajectory":
            return x_seq, static_feat, y_traj
        elif self.target_type == "events":
            return x_seq, static_feat, torch.stack([y_hypo_4h, y_hyper_4h])
        else:
            return {
                "x_seq": x_seq,
                "static": static_feat,
                "trajectory": y_traj,
                "hypo_4h": y_hypo_4h,
                "hyper_4h": y_hyper_4h
            }


def get_dataloaders(data_dir="data/final", batch_size=64, scaled=True, target_type="both", num_workers=0):
    """
    Creates train, validation, and test PyTorch DataLoaders with zero data leakage.
    """
    train_ds = GlucoShieldDataset(data_dir=data_dir, split="train", scaled=scaled, target_type=target_type)
    val_ds = GlucoShieldDataset(data_dir=data_dir, split="val", scaled=scaled, target_type=target_type)
    test_ds = GlucoShieldDataset(data_dir=data_dir, split="test", scaled=scaled, target_type=target_type)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=num_workers)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers)

    return train_loader, val_loader, test_loader


if __name__ == "__main__":
    print("Testing GlucoShield PyTorch Dataset & DataLoader Interface...")
    tr_loader, v_loader, te_loader = get_dataloaders(data_dir="D:/ML PROJECT/data/final", batch_size=32)
    sample_batch = next(iter(tr_loader))
    print("Sample Train Batch:")
    print("  x_seq shape     :", sample_batch["x_seq"].shape)
    print("  static shape    :", sample_batch["static"].shape)
    print("  trajectory shape:", sample_batch["trajectory"].shape)
    print("  hypo_4h shape   :", sample_batch["hypo_4h"].shape)
    print("DataLoader interface verified successfully!")