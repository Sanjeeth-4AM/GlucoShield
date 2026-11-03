"""
GlucoShield — Frozen Model Artifact Integrity Verifier (Phase 16)
=================================================================
Verifies bitwise SHA-256 integrity of all frozen production model weights,
scalers, and configuration files at service startup.

Governance:
  - Ground-truth SHA-256 hashes are immutable.
  - If any artifact fails verification, startup aborts (unless GLUCOSHIELD_DEV_MODE=true).
  - Corrupted artifacts are NEVER silently repaired or overwritten.
"""

import os
import hashlib
import json
from typing import Dict, Any, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Authoritative Frozen SHA-256 Registry (Verified in Phases 13, 14, 15)
FROZEN_ARTIFACT_REGISTRY: Dict[str, Dict[str, Any]] = {
    "v1_neural": {
        "rel_path": "models/glucoshield_neural_best.pt",
        "expected_sha256": "026af3341a91064136c38b0172f2aa6af34806913640a02270c7d82a28ea13fb",
        "category": "model_weights",
        "required_for": ["V1_FROZEN", "PHASE13_VALIDATED"]
    },
    "v1_hybrid": {
        "rel_path": "models/glucoshield_hybrid_best.pt",
        "expected_sha256": "89a67710aa4931246f9097674332cbfd9d1af3d20c722c04d806ef66e47298d1",
        "category": "model_weights",
        "required_for": ["V1_FROZEN"]
    },
    "feature_scaler": {
        "rel_path": "data/metadata/feature_scaler.joblib",
        "expected_sha256": "757f5c99e294dc8c5698a42cee1843853e8506df5203508aa71a1462d545972b",
        "category": "scaler",
        "required_for": ["V1_FROZEN", "V2_FROZEN", "PHASE13_VALIDATED"]
    },
    "static_scaler": {
        "rel_path": "data/metadata/static_scaler.joblib",
        "expected_sha256": "fedc25f67dbcefd2c19ff38375568f3f2bc83ac1fa7c29840e5c81d33b479576",
        "category": "scaler",
        "required_for": ["V1_FROZEN", "V2_FROZEN", "PHASE13_VALIDATED"]
    },
    "v2_hybrid": {
        "rel_path": "models/v2/glucoshield_v2_best.pt",
        "expected_sha256": "fee7c966b41497bcb3bba9bff60bb47ccdab02c15afea8c1c3cb52b74b7abdc2",
        "category": "model_weights",
        "required_for": ["V2_FROZEN", "PHASE13_VALIDATED"]
    },
    "phase13_gate_config": {
        "rel_path": "scratch/phase13_disagreement_gate/frozen_gate_config.json",
        "expected_sha256": "a7d9aaaa908fdfb3667e6285312722ab5e7209286bc070203f48ea507f97964f",
        "category": "configuration",
        "required_for": ["PHASE13_VALIDATED"]
    },
    "phase13_ode_config": {
        "rel_path": "scratch/phase13_patient_specific_ode/ode_adaptation_config.json",
        "expected_sha256": "25617ef1104b32bf24a2ed83db16f679a00e247e02ef846c6e41cd5e184d32d8",
        "category": "configuration",
        "required_for": ["PHASE13_VALIDATED"]
    }
}

def compute_sha256(filepath: str) -> str:
    """Computes hexadecimal SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().lower()

def verify_artifact_integrity(
    target_model: str = "ALL",
    fail_fast: bool = True
) -> Tuple[bool, Dict[str, Any]]:
    """
    Verifies SHA-256 hashes of registered artifacts.
    
    Args:
        target_model: "ALL", "V1_FROZEN", "V2_FROZEN", or "PHASE13_VALIDATED"
        fail_fast: If True, raises RuntimeError immediately on hash mismatch.
        
    Returns:
        (all_passed: bool, report: dict)
    """
    is_dev_mode = os.getenv("GLUCOSHIELD_DEV_MODE", "false").lower() == "true"
    report = {
        "status": "PASS",
        "dev_mode_active": is_dev_mode,
        "target_model": target_model,
        "artifacts": {}
    }
    
    all_passed = True
    failures = []

    for key, spec in FROZEN_ARTIFACT_REGISTRY.items():
        # Filter if target_model specified
        if target_model != "ALL" and target_model not in spec["required_for"]:
            continue

        full_path = os.path.join(BASE_DIR, spec["rel_path"])
        if not os.path.exists(full_path):
            all_passed = False
            report["artifacts"][key] = {
                "path": spec["rel_path"],
                "status": "MISSING",
                "error": f"Artifact file not found: {spec['rel_path']}"
            }
            failures.append(f"MISSING: {spec['rel_path']}")
            continue

        actual_hash = compute_sha256(full_path)
        expected_hash = spec["expected_sha256"]
        match = (actual_hash == expected_hash)

        report["artifacts"][key] = {
            "path": spec["rel_path"],
            "expected_sha256": expected_hash,
            "actual_sha256": actual_hash,
            "status": "PASS" if match else "CORRUPTED",
            "bytes": os.path.getsize(full_path)
        }

        if not match:
            all_passed = False
            failures.append(f"CORRUPTED: {spec['rel_path']} (got {actual_hash[:8]}..., expected {expected_hash[:8]}...)")

    if not all_passed:
        report["status"] = "FAIL"
        report["failures"] = failures
        if fail_fast and not is_dev_mode:
            err_msg = (
                "FATAL: GlucoShield Frozen Artifact Integrity Verification Failed!\n"
                f"Failures:\n  - " + "\n  - ".join(failures) + "\n"
                "The service refuses to activate with modified or unverified model artifacts. "
                "Ensure production artifacts match the registered manifest."
            )
            raise RuntimeError(err_msg)

    return all_passed, report
