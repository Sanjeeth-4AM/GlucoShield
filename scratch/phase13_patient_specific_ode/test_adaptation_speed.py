"""
Test script to benchmark and verify sequential online ODE parameter adaptation.
"""
import os
import sys
import time
import json
import torch
import numpy as np

BASE_DIR = "D:/ML PROJECT"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from models.v2.neural_forecaster import GlucoShieldNeuralForecasterV2
from models.v2.hybrid_forecaster_v2 import GlucoShieldHybridForecasterV2
from physiology.state import MetabolicState
from physiology.parameters import PhysiologicalParameters
from physiology.integrator import RK4Integrator

def test():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # Load calibration partition
    data_dir = os.path.join(BASE_DIR, "scratch", "phase11_sleep", "data")
    hupa_raw = np.load(os.path.join(data_dir, "hupa_windows_stride4.npz"))
    hupa_feat = np.load(os.path.join(data_dir, "sleep_features.npz"))

    cal_mask = (hupa_feat["partitions"] == "calibration") & hupa_feat["sleep_aligned"]
    pids = hupa_feat["pids"][cal_mask]
    dyn_raw = hupa_raw["dynamic_raw"][cal_mask]
    targets = hupa_raw["targets"][cal_mask]

    N = len(pids)
    print(f"Calibration windows: {N:,}")

    u_pids, p_counts = np.unique(pids, return_counts=True)
    print(f"Unique participants: {len(u_pids)}")

    # Baseline prior parameters for HUPA cohort
    # S_I = 0.002869, G_b = 141.79
    base_si = 0.002869
    base_gb = 141.79

    # Let's inspect the observed CGM trends vs baseline Gb
    # For each participant, what is their mean observed CGM?
    print("\nParticipant empirical mean CGM vs baseline Gb (141.8 mg/dL):")
    for p in u_pids[:10]:
        mask = (pids == p)
        mean_cgm = np.mean(dyn_raw[mask, -1, 0])
        std_cgm = np.std(dyn_raw[mask, -1, 0])
        print(f"  {p}: mean CGM = {mean_cgm:.1f} mg/dL (std: {std_cgm:.1f})")

if __name__ == "__main__":
    test()
