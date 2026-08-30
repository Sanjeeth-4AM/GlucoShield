"""
GlucoShield Dataset Provenance & Cryptographic Fingerprinter
============================================================
Records file inventories, sizes, and SHA256 checksums for research transparency
without embedding patient-sensitive time series data into version-controlled reports.
"""

import os
import json
import hashlib
from typing import Dict, Any, List, Optional

def compute_file_sha256(file_path: str) -> str:
    """Computes SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def generate_dataset_provenance(
    dataset_root: str,
    dataset_name: str = "OhioT1DM",
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Scans a local dataset directory and records metadata and checksums.
    """
    inventory = []
    total_bytes = 0

    if os.path.exists(dataset_root):
        for root, _, files in os.walk(dataset_root):
            for f in files:
                full_p = os.path.join(root, f)
                rel_p = os.path.relpath(full_p, dataset_root)
                sz = os.path.getsize(full_p)
                sha = compute_file_sha256(full_p)
                total_bytes += sz
                inventory.append({
                    "relative_path": rel_p.replace("\\", "/"),
                    "size_bytes": sz,
                    "sha256": sha
                })

    status = "VERIFIED_PRESENT" if inventory else "PENDING_LOCAL_ACQUISITION"

    provenance = {
        "dataset_name": dataset_name,
        "provenance_status": status,
        "dataset_root": dataset_root.replace("\\", "/"),
        "total_files": len(inventory),
        "total_size_mb": round(total_bytes / (1024 * 1024), 2),
        "file_inventory": inventory
    }

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(provenance, f, indent=2)

    return provenance

if __name__ == "__main__":
    out_dir = "D:/ML PROJECT/activity_telemetry/experiments/results"
    tpl_path = os.path.join(out_dir, "dataset_provenance_template.json")
    prov = generate_dataset_provenance("D:/ML PROJECT/data/raw/OhioT1DM", output_path=tpl_path)
    print(f"Generated provenance record ({prov['provenance_status']}) with {prov['total_files']} files.")
