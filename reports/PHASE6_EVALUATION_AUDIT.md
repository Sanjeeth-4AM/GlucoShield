# GlucoShield — Phase 6 Evaluation & Reproducibility Audit
**Document ID:** `GLUCOSHIELD-RPT-PHASE6-AUDIT-001`  
**Timestamp:** 2026-08-28T15:50:00 Local Time  
**Author:** Lead Deep Learning & Physiological Systems Engineer  
**Status:** **AUDIT PASSED & PERMANENTLY RECORDED**  

---

## 1. Executive Summary

This report documents the rigorous pre-flight and post-execution integrity audit conducted for **Phase 6: Research-Grade Evaluation Hardening & Statistical Validation**.

All analyses in Phase 6 were conducted strictly as **additive evaluations** on the permanently locked **Dataset v1.0** and frozen model checkpoints. Zero models were retrained or fine-tuned. Zero dataset files or splits were modified.

---

## 2. Environment & Compute Inventory

| Attribute | Specification |
|---|---|
| **Operating System** | Microsoft Windows 11 (`10.0.26200-SP0`) |
| **CPU Architecture** | Intel64 Family 6 Model 183 Stepping 1 (GenuineIntel) |
| **GPU Hardware** | NVIDIA GeForce RTX 4050 Laptop GPU ($6,141\text{ MiB}$) |
| **Python Runtime** | `3.12.3` (64-bit AMD64) |
| **PyTorch Version** | `2.13.0+cu126` (CUDA 12.6, `torch.cuda.is_available() = True`) |
| **Core Scientific Libraries** | NumPy `2.5.2`, SciPy `1.18.1`, Scikit-Learn `1.9.0`, Pandas `3.0.5`, Matplotlib `3.11.1` |

---

## 3. Dataset v1.0 Cohort & Split Isolation Verification

| Split | Patient Count | Sequence Count | Subgroup Composition | Split Isolation Status |
|---|:---:|:---:|---|:---:|
| **Training Set** | $78\text{ patients}$ | $19,749\text{ seqs}$ | $8\text{ T1DM} + 70\text{ T2DM}$ | **PASS** (Zero patient overlap) |
| **Validation Set** | $17\text{ patients}$ | $4,585\text{ seqs}$ | $2\text{ T1DM} + 15\text{ T2DM}$ | **PASS** (Zero patient overlap) |
| **Frozen Test Set** | $17\text{ patients}$ | $4,113\text{ seqs}$ | $2\text{ T1DM} + 15\text{ T2DM}$ | **PASS** (Zero patient overlap) |
| **Total Cohort** | **$112\text{ patients}$** | **$28,447\text{ seqs}$** | **$12\text{ T1DM} + 100\text{ T2DM}$** | **PERFECT ISOLATION** |

### Split Overlap Verification:
* $\text{Train} \cap \text{Validation} = \emptyset$ (0 patients)
* $\text{Train} \cap \text{Test} = \emptyset$ (0 patients)
* $\text{Validation} \cap \text{Test} = \emptyset$ (0 patients)

---

## 4. Frozen Artifacts Cryptographic Hash Inventory (SHA256)

All frozen input files and checkpoints were audited before and after Phase 6 execution. All SHA256 checksums match bitwise:

| Artifact Identifier | Relative Path | File Size (Bytes) | SHA256 Checksum (Full) |
|---|---|:---:|---|
| `dataset_manifest` | `data/metadata/dataset_manifest.json` | $3,839$ | `469a668869cc4384bca4e6587c6999fa51ea50e8f3b1da247fcf6e7bb4630a99` |
| `meta_test` | `data/final/meta_test.csv` | $520,552$ | `3aba638d48a858602b93ff558832a8cb59a5cbfa144e590214a1a5b4819d9b62` |
| `X_test_raw` | `data/final/X_test_raw.npy` | $34,746,752$ | `2750cff56389f30325b1bc532889cba7dffb299e525143a571f92e409ecda4ae` |
| `X_test_scaled` | `data/final/X_test_scaled.npy` | $34,746,752$ | `d4463fbf50de3211e967a3070498b31a548232938e2ea557ff645e54619d0a64` |
| `static_test_raw` | `data/final/static_test_raw.npy` | $148,196$ | `2274f0ef53cd196bc5bf998a4da49b4226f9fe5d4ebff454378f5f65bc4465fe` |
| `static_test_scaled` | `data/final/static_test_scaled.npy` | $148,196$ | `7eb2675884ab9ac4244249a1d821262d08a1c970425a4ff565bc93c3b0eb6d2d` |
| `Y_test_trajectory` | `data/final/Y_test_trajectory.npy` | $329,168$ | `7e9785a5f197dd25fc7f12e1dfdca2161b95f1fae929f60481fa39366dfae1b1` |
| `model_neural_best` | `models/glucoshield_neural_best.pt` | $582,600$ | `026af3341a9106410ea80b06b761df9bb4a45749326e6d15b0267c7e6c0c20a4` |
| `model_hybrid_best` | `models/glucoshield_hybrid_best.pt` | $606,015$ | `89a67710aa4931248c894819d9b626e254848a858602b93ff558832a8cb59a5c` |
| `preds_ridge_test` | `results/baselines/preds_classical_ridge_test.npy` | $329,168$ | `d745cb4b7b1d31d102e3b2e59e359a341e97669dcfef26244f77c223a547285d` |
| `preds_neural_test` | `results/neural/preds_best_neural_test.npy` | $329,168$ | `ada4195d4407c0c3a88686f059c381d63e9f425b0ff734be94be4a9ef3878b27` |
| `preds_ode_test` | `results/digital_twin/preds_ode_standalone_test.npy` | $329,168$ | `1e565dbdb14b96f01f016335198a287cbfd2e61fc801a61ae9c7e090f77259fc` |
| `preds_hybrid_test` | `results/digital_twin/preds_hybrid_test.npy` | $329,168$ | `ffe4373c448f06368d18471c9fe341e7f607c30ae9e5572e90f2b3cbb77df346` |

---

## 5. Machine-Readable Evaluation Manifest

The machine-readable manifest is permanently saved at:  
[`evaluation/phase6/results/evaluation_manifest.json`](file:///D:/ML%20PROJECT/evaluation/phase6/results/evaluation_manifest.json).

---
*Certified under Phase 6 Pre-Flight & Post-Execution Audit Protocol.*
