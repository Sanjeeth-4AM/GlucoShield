"""
GlucoShield V2 — Multi-Modal Dataset & Batching Engine
========================================================
Handles multi-modal data ingestion:
  - 24-hour dynamic sequence (scaled and raw)
  - 9 static clinical biomarkers (scaled and raw)
  - Physiological telemetry: Exercise, Sleep, Hormones, Circadian
  - Binary validity/missingness masks
  - 20-step continuous future trajectory target
  - 5 acute clinical risk targets
"""

import os
import torch
import numpy as np
import pandas as pd
from torch.utils.data import Dataset, DataLoader
from typing import Optional, Dict, Tuple, Any

from models.v2.context_encoder import PhysiologicalContextBatch

class MultiModalGlucoDatasetV2(Dataset):
    """
    Multi-modal PyTorch dataset supporting both standard historical CGM data
    and multi-factor physiological telemetry with strict missingness masking.
    """
    def __init__(
        self,
        dynamic_scaled: np.ndarray,
        dynamic_raw: np.ndarray,
        static_scaled: np.ndarray,
        static_raw: np.ndarray,
        y_traj: np.ndarray,
        y_risk: Optional[np.ndarray] = None,
        f_exercise: Optional[np.ndarray] = None,
        m_exercise: Optional[np.ndarray] = None,
        f_sleep: Optional[np.ndarray] = None,
        m_sleep: Optional[np.ndarray] = None,
        f_hormonal: Optional[np.ndarray] = None,
        m_hormonal: Optional[np.ndarray] = None,
        f_circadian: Optional[np.ndarray] = None
    ):
        self.N = len(dynamic_scaled)
        self.dynamic_scaled = dynamic_scaled.astype(np.float32)
        self.dynamic_raw = dynamic_raw.astype(np.float32)
        self.static_scaled = static_scaled.astype(np.float32)
        self.static_raw = static_raw.astype(np.float32)
        self.y_traj = y_traj.astype(np.float32)

        if y_risk is not None:
            self.y_risk = y_risk.astype(np.float32)
        else:
            self.y_risk = np.zeros((self.N, 5), dtype=np.float32)

        # Factor arrays with safe default zeros/masks
        self.f_exercise = f_exercise.astype(np.float32) if f_exercise is not None else np.zeros((self.N, 4), dtype=np.float32)
        self.m_exercise = m_exercise.astype(np.float32) if m_exercise is not None else np.zeros((self.N, 1), dtype=np.float32)

        self.f_sleep = f_sleep.astype(np.float32) if f_sleep is not None else np.zeros((self.N, 5), dtype=np.float32)
        self.m_sleep = m_sleep.astype(np.float32) if m_sleep is not None else np.zeros((self.N, 1), dtype=np.float32)

        self.f_hormonal = f_hormonal.astype(np.float32) if f_hormonal is not None else np.zeros((self.N, 3), dtype=np.float32)
        self.m_hormonal = m_hormonal.astype(np.float32) if m_hormonal is not None else np.zeros((self.N, 1), dtype=np.float32)

        # Circadian harmonics extracted from dynamic raw sin_hour (chan 10) & cos_hour (chan 11)
        if f_circadian is not None:
            self.f_circadian = f_circadian.astype(np.float32)
        else:
            # Reconstruct from channel 10 and 11
            sin_24 = self.dynamic_raw[:, -1, 10]
            cos_24 = self.dynamic_raw[:, -1, 11]
            # 12-hour second harmonics: sin(2theta) = 2 sin cos, cos(2theta) = cos^2 - sin^2
            sin_12 = 2.0 * sin_24 * cos_24
            cos_12 = cos_24**2 - sin_24**2
            self.f_circadian = np.stack([sin_24, cos_24, sin_12, cos_12], axis=-1).astype(np.float32)

    def __len__(self) -> int:
        return self.N

    def __getitem__(self, idx: int) -> Dict[str, np.ndarray]:
        return {
            "dynamic_scaled": self.dynamic_scaled[idx],
            "dynamic_raw": self.dynamic_raw[idx],
            "static_scaled": self.static_scaled[idx],
            "static_raw": self.static_raw[idx],
            "y_traj": self.y_traj[idx],
            "y_risk": self.y_risk[idx],
            "f_exercise": self.f_exercise[idx],
            "m_exercise": self.m_exercise[idx],
            "f_sleep": self.f_sleep[idx],
            "m_sleep": self.m_sleep[idx],
            "f_hormonal": self.f_hormonal[idx],
            "m_hormonal": self.m_hormonal[idx],
            "f_circadian": self.f_circadian[idx]
        }


def v2_collate_fn(batch: list) -> Dict[str, Any]:
    """
    Custom collate function packing samples into PyTorch tensors and PhysiologicalContextBatch.
    """
    dyn_s = torch.from_numpy(np.stack([b["dynamic_scaled"] for b in batch], axis=0))
    dyn_r = torch.from_numpy(np.stack([b["dynamic_raw"] for b in batch], axis=0))
    stat_s = torch.from_numpy(np.stack([b["static_scaled"] for b in batch], axis=0))
    stat_r = torch.from_numpy(np.stack([b["static_raw"] for b in batch], axis=0))
    y_traj = torch.from_numpy(np.stack([b["y_traj"] for b in batch], axis=0))
    y_risk = torch.from_numpy(np.stack([b["y_risk"] for b in batch], axis=0))

    f_ex = torch.from_numpy(np.stack([b["f_exercise"] for b in batch], axis=0))
    m_ex = torch.from_numpy(np.stack([b["m_exercise"] for b in batch], axis=0))

    f_sl = torch.from_numpy(np.stack([b["f_sleep"] for b in batch], axis=0))
    m_sl = torch.from_numpy(np.stack([b["m_sleep"] for b in batch], axis=0))

    f_hm = torch.from_numpy(np.stack([b["f_hormonal"] for b in batch], axis=0))
    m_hm = torch.from_numpy(np.stack([b["m_hormonal"] for b in batch], axis=0))

    f_circ = torch.from_numpy(np.stack([b["f_circadian"] for b in batch], axis=0))

    context_batch = PhysiologicalContextBatch(
        f_exercise=f_ex,
        m_exercise=m_ex,
        f_sleep=f_sl,
        m_sleep=m_sl,
        f_hormonal=f_hm,
        m_hormonal=m_hm,
        f_circadian=f_circ
    )

    return {
        "dynamic_scaled": dyn_s,
        "dynamic_raw": dyn_r,
        "static_scaled": stat_s,
        "static_raw": stat_r,
        "context_batch": context_batch,
        "y_traj": y_traj,
        "y_risk": y_risk
    }


def load_v1_partition_as_v2(
    data_dir: str,
    partition: str = "train",
    mmap: bool = False
) -> MultiModalGlucoDatasetV2:
    """
    Helper function to load frozen V1 final data as a V2-compatible dataset.
    """
    m = "r" if mmap else None
    dyn_s = np.load(os.path.join(data_dir, f"X_{partition}_scaled.npy"), mmap_mode=m)
    dyn_r = np.load(os.path.join(data_dir, f"X_{partition}_raw.npy"), mmap_mode=m)
    stat_s = np.load(os.path.join(data_dir, f"static_{partition}_scaled.npy"), mmap_mode=m)
    stat_r = np.load(os.path.join(data_dir, f"static_{partition}_raw.npy"), mmap_mode=m)
    y_traj = np.load(os.path.join(data_dir, f"Y_{partition}_trajectory.npy"), mmap_mode=m)

    # Risk heads
    h1 = np.load(os.path.join(data_dir, f"Y_{partition}_hypo_1h.npy"), mmap_mode=m)
    h2 = np.load(os.path.join(data_dir, f"Y_{partition}_hypo_2h.npy"), mmap_mode=m)
    h4 = np.load(os.path.join(data_dir, f"Y_{partition}_hypo_4h.npy"), mmap_mode=m)
    hy2 = np.load(os.path.join(data_dir, f"Y_{partition}_hyper_2h.npy"), mmap_mode=m)
    hy4 = np.load(os.path.join(data_dir, f"Y_{partition}_hyper_4h.npy"), mmap_mode=m)
    y_risk = np.stack([h1, h2, h4, hy2, hy4], axis=-1)

    return MultiModalGlucoDatasetV2(
        dynamic_scaled=dyn_s,
        dynamic_raw=dyn_r,
        static_scaled=stat_s,
        static_raw=stat_r,
        y_traj=y_traj,
        y_risk=y_risk
    )
