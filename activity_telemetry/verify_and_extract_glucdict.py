"""
GlucoShield — Glucdict Archive Verification, Extraction & Provenance
====================================================================
Verifies archive integrity using inflate64 for Deflate64 compression,
extracts all raw files into data/raw/Glucdict/, computes SHA256 checksums,
and records complete cryptographic provenance and file inventory.
"""

import os
import sys
import zlib
import struct
import zipfile
import hashlib
import json
import zlib
import inflate64
from datetime import datetime

BASE_DIR = "D:/ML PROJECT"
SRC_ZIP = os.path.expanduser("~/Downloads/Glucdict Dataset.zip")
DEST_DIR = os.path.join(BASE_DIR, "data", "raw", "Glucdict")
DEST_ZIP = os.path.join(DEST_DIR, "Glucdict Dataset.zip")
RESULTS_DIR = os.path.join(BASE_DIR, "activity_telemetry", "experiments", "results")

def compute_sha256(filepath: str) -> str:
    print(f"Computing SHA256 for {filepath}...")
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024 * 8):  # 8MB chunks
            h.update(chunk)
    return h.hexdigest()

def decompress_entry(fp, info):
    fp.seek(info.header_offset)
    local_header = fp.read(30)
    if len(local_header) < 30:
        raise ValueError(f"Truncated local header for {info.filename}")
    _, _, _, _, _, _, _, _, name_len, extra_len = struct.unpack('<HHHHHIIIHH', local_header[4:30])
    fp.seek(info.header_offset + 30 + name_len + extra_len)
    compressed_bytes = fp.read(info.compress_size)
    
    if info.compress_type == 0:  # Stored
        decomp = compressed_bytes
    elif info.compress_type == 8:  # Deflate
        decomp = zlib.decompress(compressed_bytes, -15)
    elif info.compress_type == 9:  # Deflate64
        inflater = inflate64.Inflater()
        decomp = inflater.inflate(compressed_bytes)
    else:
        raise NotImplementedError(f"Unsupported compression method {info.compress_type} for {info.filename}")
    
    # Verify CRC32
    crc = zlib.crc32(decomp) & 0xFFFFFFFF
    if crc != info.CRC:
        raise ValueError(f"CRC32 mismatch for {info.filename}: expected {info.CRC}, got {crc}")
    
    return decomp

def main():
    os.makedirs(DEST_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)

    print("=" * 80)
    print("STEP 1: LOCATE & TRANSFER GLUCDICT ZIP ARCHIVE")
    print("=" * 80)
    print(f"Source: {SRC_ZIP}")
    print(f"Destination: {DEST_ZIP}")

    if not os.path.exists(DEST_ZIP) or os.path.getsize(DEST_ZIP) != os.path.getsize(SRC_ZIP):
        import shutil
        print(f"Copying {os.path.getsize(SRC_ZIP) / (1024**3):.2f} GB from Downloads to {DEST_DIR}...")
        shutil.copy2(SRC_ZIP, DEST_ZIP)
        print("Copy completed successfully.")
    else:
        print("Destination ZIP already present with matching size.")

    zip_size = os.path.getsize(DEST_ZIP)
    print(f"Final Raw ZIP Path: {DEST_ZIP}")
    print(f"Exact ZIP Size: {zip_size} bytes ({zip_size / (1024**3):.2f} GB)")

    print("\n" + "=" * 80)
    print("STEP 2: ZIP ARCHIVE INTEGRITY & SHA-256 CHECKSUM")
    print("=" * 80)
    sha256_hash = compute_sha256(DEST_ZIP)
    print(f"SHA-256: {sha256_hash}")

    print("\n" + "=" * 80)
    print("STEP 3: EXTRACT RAW DATASET & TEST INTEGRITY")
    print("=" * 80)
    
    with zipfile.ZipFile(DEST_ZIP, "r") as zf:
        infolist = zf.infolist()
        total_entries = len(infolist)
        print(f"Total entries in archive: {total_entries}")

        extracted_inventory = []
        total_extracted_bytes = 0

        with open(DEST_ZIP, "rb") as fp:
            for idx, info in enumerate(infolist, 1):
                clean_rel_name = info.filename.replace("\\", "/")
                target_path = os.path.join(DEST_DIR, clean_rel_name)

                if info.is_dir() or clean_rel_name.endswith("/"):
                    os.makedirs(target_path, exist_ok=True)
                    continue

                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                
                # Decompress and verify CRC32
                decomp_data = decompress_entry(fp, info)
                
                with open(target_path, "wb") as out_f:
                    out_f.write(decomp_data)

                file_sz = len(decomp_data)
                file_sha = hashlib.sha256(decomp_data).hexdigest()
                total_extracted_bytes += file_sz

                extracted_inventory.append({
                    "relative_path": clean_rel_name,
                    "size_bytes": file_sz,
                    "crc32": info.CRC,
                    "sha256": file_sha
                })

                if idx % 25 == 0 or idx == total_entries:
                    print(f"  [{idx}/{total_entries}] Extracted & Verified: {clean_rel_name} ({file_sz} bytes)")

    print(f"\nExtraction completed successfully!")
    print(f"Total Extracted Files: {len(extracted_inventory)}")
    print(f"Total Extracted Size: {total_extracted_bytes} bytes ({total_extracted_bytes / (1024**3):.2f} GB)")

    provenance = {
        "dataset_name": "Glucdict - Wearable Sensors and CGM",
        "doi": "10.6084/m9.figshare.25939312",
        "associated_publication": "Enhanced blood glucose levels prediction with a smartwatch (PLOS ONE 2024, DOI: 10.1371/journal.pone.0305886)",
        "license": "CC BY 4.0",
        "source_archive_path": SRC_ZIP,
        "raw_archive_path": DEST_ZIP,
        "raw_archive_size_bytes": zip_size,
        "raw_archive_sha256": sha256_hash,
        "archive_integrity_test": f"PASSED ({len(extracted_inventory)} files verified with CRC32 & SHA-256)",
        "extraction_timestamp": datetime.now().isoformat(),
        "extraction_root": DEST_DIR,
        "total_extracted_files": len(extracted_inventory),
        "total_extracted_size_mb": round(total_extracted_bytes / (1024 * 1024), 2),
        "total_extracted_size_gb": round(total_extracted_bytes / (1024**3), 2),
        "file_inventory": extracted_inventory
    }

    manifest_path = os.path.join(RESULTS_DIR, "glucdict_provenance_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(provenance, f, indent=2)

    print(f"Provenance saved to: {manifest_path}")
    print("=" * 80)
    return provenance

if __name__ == "__main__":
    main()
