"""
GlucoShield Reproducible Participant Split & K-Fold Generator
=============================================================
Generates deterministic, patient-disjoint partitions and 6-fold cross-validation
schemes for multimodal ablation experiments.
"""

import os
import json
import numpy as np
from typing import List, Dict, Tuple, Optional, Any

def generate_kfold_participant_splits(
    participant_ids: List[str],
    n_splits: int = 6,
    seed: int = 42,
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generates deterministic, patient-disjoint 6-fold cross-validation splits.
    
    Guarantees:
      1. Every participant appears as a held-out test participant in EXACTLY ONE fold.
      2. In each fold of a 12-subject cohort: Exactly 8 Train, 2 Val, 2 Test.
      3. Zero participant overlap between train, val, and test partitions within any fold.
      4. 100% deterministic reproducibility across runs and environments.
    """
    if not participant_ids or len(participant_ids) < n_splits:
        raise ValueError(f"Participant list must contain at least {n_splits} participants.")

    sorted_pids = sorted(list(set(participant_ids)))
    n = len(sorted_pids)

    rng = np.random.RandomState(seed)
    shuffled_indices = rng.permutation(n)
    shuffled_pids = [sorted_pids[i] for i in shuffled_indices]

    # Split into n_splits roughly equal chunks
    chunks = np.array_split(shuffled_pids, n_splits)
    chunks = [list(c) for c in chunks]

    folds = []
    all_test_pids = []

    for fold_idx in range(n_splits):
        test_pids = sorted(chunks[fold_idx])
        val_idx = (fold_idx + 1) % n_splits
        val_pids = sorted(chunks[val_idx])
        
        # Train participants are all other chunks
        train_pids = []
        for i in range(n_splits):
            if i != fold_idx and i != val_idx:
                train_pids.extend(chunks[i])
        train_pids = sorted(train_pids)

        # Strict disjointness assertions per fold
        set_tr = set(train_pids)
        set_va = set(val_pids)
        set_te = set(test_pids)
        assert len(set_tr.intersection(set_va)) == 0, f"Fold {fold_idx}: Train and Val share participants!"
        assert len(set_tr.intersection(set_te)) == 0, f"Fold {fold_idx}: Train and Test share participants!"
        assert len(set_va.intersection(set_te)) == 0, f"Fold {fold_idx}: Val and Test share participants!"

        all_test_pids.extend(test_pids)

        folds.append({
            "fold_index": fold_idx,
            "train_count": len(train_pids),
            "val_count": len(val_pids),
            "test_count": len(test_pids),
            "train_participants": train_pids,
            "validation_participants": val_pids,
            "test_participants": test_pids
        })

    # Assert complete test coverage (every participant tested exactly once)
    assert len(all_test_pids) == n, "Test participant count does not match total cohort!"
    assert len(set(all_test_pids)) == n, "Some participants tested multiple times or omitted!"

    manifest = {
        "kfold_version": "2.0.0",
        "cross_validation_strategy": "6_fold_participant_disjoint_cv",
        "random_seed": seed,
        "total_participants": n,
        "number_of_folds": n_splits,
        "test_coverage_complete": True,
        "out_of_fold_test_pairs_n": n,
        "folds": folds
    }

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(manifest, f, indent=2)

    return manifest


def generate_participant_split(
    participant_ids: List[str],
    train_ratio: float = 8 / 12,
    val_ratio: float = 2 / 12,
    test_ratio: float = 2 / 12,
    seed: int = 42,
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    """Generates a single deterministic patient-disjoint train/val/test split."""
    if not participant_ids:
        raise ValueError("Participant list cannot be empty.")

    sorted_pids = sorted(list(set(participant_ids)))
    n = len(sorted_pids)

    rng = np.random.RandomState(seed)
    shuffled_indices = rng.permutation(n)
    shuffled_pids = [sorted_pids[i] for i in shuffled_indices]

    if n >= 12:
        n_train = 8
        n_val = 2
        n_test = n - n_train - n_val
    else:
        n_train = max(1, int(round(n * train_ratio)))
        n_val = max(1, int(round(n * val_ratio)))
        if n_train + n_val >= n:
            n_train = max(1, n - 2)
            n_val = 1
        n_test = n - n_train - n_val

    train_pids = sorted(shuffled_pids[:n_train])
    val_pids = sorted(shuffled_pids[n_train : n_train + n_val])
    test_pids = sorted(shuffled_pids[n_train + n_val :])

    set_tr = set(train_pids)
    set_va = set(val_pids)
    set_te = set(test_pids)
    assert len(set_tr.intersection(set_va)) == 0, "Train and Validation share participants!"
    assert len(set_tr.intersection(set_te)) == 0, "Train and Test share participants!"
    assert len(set_va.intersection(set_te)) == 0, "Validation and Test share participants!"

    manifest = {
        "split_version": "1.0.0",
        "random_seed": seed,
        "total_participants": n,
        "train_count": len(train_pids),
        "val_count": len(val_pids),
        "test_count": len(test_pids),
        "train_participants": train_pids,
        "validation_participants": val_pids,
        "test_participants": test_pids,
        "disjoint_isolation_verified": True
    }

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(manifest, f, indent=2)

    return manifest

if __name__ == "__main__":
    sample_pids = [f"User{i}" for i in range(1, 13)]
    res_path = "D:/ML PROJECT/activity_telemetry/experiments/results/participant_kfold_manifest.json"
    manifest = generate_kfold_participant_splits(sample_pids, n_splits=6, seed=42, output_path=res_path)
    print(f"Generated 6-Fold Cross-Validation: {len(manifest['folds'])} folds for {manifest['total_participants']} participants.")
    for f in manifest["folds"]:
        print(f"  Fold {f['fold_index']}: Train={f['train_count']}, Val={f['val_count']}, Test={f['test_count']} -> Test IDs: {f['test_participants']}")
