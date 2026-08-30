"""
GlucoShield — Official 13-Fold LOOCV Manifest Generator (Protocol v2.1.0)
========================================================================
Generates and certifies the deterministic 13-fold participant-disjoint partitions.
"""

import os
import json
import sys

BASE_DIR = "D:/ML PROJECT"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from activity_telemetry.experiments.participant_split import generate_kfold_participant_splits

def main():
    users = ["User1", "User3", "User4", "User5", "User6", "User7", "User8", "User9", "User10", "User12", "User13", "User14", "User15"]
    out_path = os.path.join(BASE_DIR, "activity_telemetry", "experiments", "results", "participant_kfold_manifest.json")
    
    manifest = generate_kfold_participant_splits(users, n_splits=13, seed=42, output_path=out_path)
    
    print("=" * 80)
    print("GLUCOSHIELD PROTOCOL v2.1.0 — 13-FOLD LOOCV PARTITION MANIFEST")
    print("=" * 80)
    print(f"Total Participants: {manifest['total_participants']}")
    print(f"Total Folds:        {len(manifest['folds'])}")
    print(f"Random Seed:        {manifest['random_seed']}\n")

    for f in manifest["folds"]:
        f_idx = f["fold_index"]
        tr_cnt = f["train_count"]
        val_p = f["validation_participants"]
        tst_p = f["test_participants"]
        print(f"  Fold {f_idx:02d}: Train ({tr_cnt:2d} pts) | Val ({len(val_p)} pt: {val_p[0]:6s}) | Test ({len(tst_p)} pt: {tst_p[0]:6s})")

    print(f"\nManifest certified and saved to: {out_path}")
    print("=" * 80)
    return manifest

if __name__ == "__main__":
    main()
