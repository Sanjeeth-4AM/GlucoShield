"""
GlucoShield OhioT1DM Data Readiness Checker
===========================================
Audits local environment for OhioT1DM dataset availability, validates schemas,
and generates a structured readiness report without fabricating missing data.
"""

import os
import sys
import json
import pandas as pd
from typing import Dict, Any, List

# Ensure project root is in sys.path
BASE_DIR = "D:/ML PROJECT"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from activity_telemetry.ohio_adapter import OhioT1DMAdapter
from activity_telemetry.ohio_schema import OhioT1DMConfig

def check_ohiot1dm_readiness() -> Dict[str, Any]:
    raw_ohio_dir = os.path.join(BASE_DIR, "data", "raw", "OhioT1DM")
    results_dir = os.path.join(BASE_DIR, "activity_telemetry", "validation", "results")
    os.makedirs(results_dir, exist_ok=True)
    report_path = os.path.join(results_dir, "ohiot1dm_readiness_report.json")

    print("=" * 80)
    print("GLUCOSHIELD — OHIOT1DM DATA READINESS AUDIT")
    print("=" * 80)

    # 1. Check if directory exists and contains data
    if not os.path.exists(raw_ohio_dir) or not os.listdir(raw_ohio_dir):
        print(f"\n[STATUS] OhioT1DM dataset directory is NOT present locally: {raw_ohio_dir}")
        print("\nExpected Directory Structure for Real Dataset:")
        print("  D:\\ML PROJECT\\data\\raw\\OhioT1DM\\")
        print("  |-- 2018\\")
        print("  |   |-- train\\ (e.g. 559-ws-training.xml, 563-ws-training.xml, ...)")
        print("  |   \\-- test\\  (e.g. 559-ws-testing.xml, ...)")
        print("  \\-- 2020\\")
        print("      |-- train\\")
        print("      \\-- test\\")
        print("\nRequired Action:")
        print("  1. Submit academic DUA request to Prof. Razvan Bunescu (rbunescu@charlotte.edu).")
        print("  2. Place decrypted XML files in data/raw/OhioT1DM/.")
        print("  3. Re-run this checker to validate schemas and participant coverage.")

        report = {
            "status": "DATASET_NOT_PRESENT",
            "is_ready_for_ablation": False,
            "target_directory": "data/raw/OhioT1DM/",
            "participants_found": 0,
            "participant_ids": [],
            "missing_required_actions": [
                "Submit DUA request to Ohio University",
                "Place decrypted XML files in data/raw/OhioT1DM/",
                "Re-run readiness validation"
            ]
        }
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        print("\nReadiness Report Saved: activity_telemetry/validation/results/ohiot1dm_readiness_report.json")
        print("=" * 80)
        return report

    # 2. If present, run full schema validation
    adapter = OhioT1DMAdapter()
    pids = adapter.list_participants(raw_ohio_dir)
    print(f"\nFound {len(pids)} participants in {raw_ohio_dir}: {pids}")

    participant_reports = []
    all_valid = True

    for pid in pids:
        try:
            df = adapter.load_participant_telemetry(pid, raw_ohio_dir)
            val_rep = adapter.validator.validate_participant_dataframe(df, expected_participant_id=pid)
            participant_reports.append(val_rep.to_dict())
            if not val_rep.is_valid:
                all_valid = False
        except Exception as e:
            participant_reports.append({
                "participant_id": pid,
                "is_valid": False,
                "errors": [str(e)]
            })
            all_valid = False

    status = "DATA_READY" if all_valid and len(pids) >= 8 else ("DATA_INCOMPLETE" if pids else "DATA_REJECTED")

    report = {
        "status": status,
        "is_ready_for_ablation": (status == "DATA_READY"),
        "target_directory": raw_ohio_dir,
        "participants_found": len(pids),
        "participant_ids": pids,
        "cohort_reports": participant_reports
    }
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nFinal Readiness Status: {status}")
    print("=" * 80)
    return report

if __name__ == "__main__":
    check_ohiot1dm_readiness()
