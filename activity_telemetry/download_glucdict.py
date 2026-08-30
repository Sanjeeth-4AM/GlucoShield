"""
GlucoShield Glucdict Dataset Downloader & Provenance Recorder
=============================================================
Downloads the official Glucdict dataset from Figshare (DOI: 10.6084/m9.figshare.25939312),
computes SHA256 cryptographic hashes before and after extraction, records file inventories,
and places files strictly in data/raw/Glucdict/.
"""

import os
import sys
import json
import zipfile
import hashlib
import urllib.request
from datetime import datetime

BASE_DIR = "D:/ML PROJECT"
TARGET_DIR = os.path.join(BASE_DIR, "data", "raw", "Glucdict")
RESULTS_DIR = os.path.join(BASE_DIR, "activity_telemetry", "experiments", "results")

def compute_sha256(file_path: str) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def fetch_figshare_metadata():
    article_id = "25939312"
    url = f"https://api.figshare.com/v2/articles/{article_id}/files"
    req = urllib.request.Request(url, headers={"User-Agent": "GlucoShield-Research/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))

def download_and_extract():
    os.makedirs(TARGET_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)

    print("=" * 80)
    print("GLUCOSHIELD — GLUCDICT DATASET ACQUISITION & PROVENANCE")
    print("=" * 80)

    print("Fetching file manifest from Figshare API (Article 25939312)...")
    files_meta = fetch_figshare_metadata()
    print(f"Found {len(files_meta)} files listed on Figshare.")

    downloaded_files = []
    for item in files_meta:
        fname = item["name"]
        durl = item["download_url"]
        fsize = item.get("size", 0)
        local_path = os.path.join(TARGET_DIR, fname)

        print(f"\nDownloading {fname} ({fsize / (1024*1024):.2f} MB)...")
        req = urllib.request.Request(durl, headers={"User-Agent": "GlucoShield-Research/1.0"})
        with urllib.request.urlopen(req, timeout=120) as resp, open(local_path, "wb") as out_f:
            total_read = 0
            while chunk := resp.read(65536):
                out_f.write(chunk)
                total_read += len(chunk)
        
        sha = compute_sha256(local_path)
        print(f"  --> Download Complete. Size: {os.path.getsize(local_path)} bytes | SHA256: {sha}")
        downloaded_files.append({
            "filename": fname,
            "size_bytes": os.path.getsize(local_path),
            "sha256": sha,
            "download_url": durl
        })

        # Extract if zip
        if fname.endswith(".zip"):
            print(f"Extracting {fname} to {TARGET_DIR}...")
            with zipfile.ZipFile(local_path, "r") as zip_ref:
                zip_ref.extractall(TARGET_DIR)
            print("  --> Extraction Complete.")

    # Record Provenance Manifest
    extracted_inventory = []
    total_extracted_bytes = 0
    for root, _, files in os.walk(TARGET_DIR):
        for f in files:
            full_p = os.path.join(root, f)
            rel_p = os.path.relpath(full_p, TARGET_DIR).replace("\\", "/")
            sz = os.path.getsize(full_p)
            sha = compute_sha256(full_p)
            total_extracted_bytes += sz
            extracted_inventory.append({
                "relative_path": rel_p,
                "size_bytes": sz,
                "sha256": sha
            })

    provenance = {
        "dataset_name": "Glucdict - Wearable Sensors and CGM",
        "doi": "10.6084/m9.figshare.25939312",
        "associated_publication": "Enhanced blood glucose levels prediction with a smartwatch (PLOS ONE 2024, DOI: 10.1371/journal.pone.0305886)",
        "license": "CC BY 4.0",
        "retrieval_timestamp": datetime.now().isoformat(),
        "storage_root": "data/raw/Glucdict/",
        "downloaded_archives": downloaded_files,
        "total_extracted_files": len(extracted_inventory),
        "total_extracted_size_mb": round(total_extracted_bytes / (1024 * 1024), 2),
        "file_inventory": extracted_inventory
    }

    prov_path = os.path.join(RESULTS_DIR, "glucdict_provenance_manifest.json")
    with open(prov_path, "w") as f:
        json.dump(provenance, f, indent=2)

    print(f"\nProvenance Manifest Saved to: {prov_path}")
    print(f"Total extracted files: {len(extracted_inventory)} ({provenance['total_extracted_size_mb']} MB)")
    print("=" * 80)
    return provenance

if __name__ == "__main__":
    download_and_extract()
