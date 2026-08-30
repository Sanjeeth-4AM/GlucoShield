# GlucoShield — Research Reproducibility Guide
**Project Root:** `D:/ML PROJECT`  
**Dataset Version:** `Dataset v1.0 (Locked, 28,447 sequences, 112 patients)`  
**Hardware Tested:** NVIDIA GeForce RTX 4050 Laptop GPU (CUDA 12.6, Driver 581.86)  
**Python Runtime:** `3.12.3` (64-bit AMD64)  
**PyTorch Version:** `2.13.0+cu126`  

---

## 1. Quick Verification & Reproduction Commands

To reproduce the entire Phase 6 research-grade evaluation and verification suite from scratch using the locked frozen checkpoints and data:

```powershell
# 1. Run Pre-Flight Integrity Audit (SHA256 Hashes, Shapes, Leakage Check)
& "C:\Users\sanje\AppData\Local\Programs\Python\Python312\python.exe" "D:/ML PROJECT/evaluation/phase6/scripts/audit_and_manifest.py"

# 2. Run Patient-Level Statistical Validation & 10,000 Bootstrap Resamples
& "C:\Users\sanje\AppData\Local\Programs\Python\Python312\python.exe" "D:/ML PROJECT/evaluation/phase6/scripts/run_statistical_validation.py"

# 3. Run 20-Horizon, Clinical Range, Velocity Trend & Subgroup Analysis
& "C:\Users\sanje\AppData\Local\Programs\Python\Python312\python.exe" "D:/ML PROJECT/evaluation/phase6/scripts/run_horizon_and_range_analysis.py"

# 4. Run Risk Head Discrimination & Reliability Calibration Audit
& "C:\Users\sanje\AppData\Local\Programs\Python\Python312\python.exe" "D:/ML PROJECT/evaluation/phase6/scripts/run_risk_calibration_audit.py"

# 5. Run Controlled Inference-Only Robustness Stress Testing
& "C:\Users\sanje\AppData\Local\Programs\Python\Python312\python.exe" "D:/ML PROJECT/evaluation/phase6/scripts/run_robustness_stress_tests.py"

# 6. Generate 6-Panel Failure & Success Case Studies Figure
& "C:\Users\sanje\AppData\Local\Programs\Python\Python312\python.exe" "D:/ML PROJECT/evaluation/phase6/scripts/plot_case_studies.py"

# 7. Execute Automated Unit Test Suite (7 / 7 Tests)
& "C:\Users\sanje\AppData\Local\Programs\Python\Python312\python.exe" "D:/ML PROJECT/evaluation/phase6/tests/test_phase6_pipeline.py"
```

---

## 2. Determinism & Random Seeds

| Component | Random Seed | Determinism Level |
|---|:---:|---|
| Dataset Split Allocation | Fixed in `meta_train.csv`, `meta_val.csv`, `meta_test.csv` | $100\%$ Bitwise Deterministic |
| Model Initialization & Training | Seeds 42, 123, 7 (Winner Seed 7 locked in `.pt`) | $100\%$ Fixed Checkpoints |
| Patient Bootstrap Resampling | `seed=42` ($10,000$ iterations) | $100\%$ Deterministic under NumPy `2.5.2` |
| Gaussian Noise Robustness | `seed=42` | $100\%$ Deterministic |
| Decision Engine Unit Tests | Deterministic unit assertions | $100\%$ Deterministic ($5/5$ Pass) |
| Physiology Core Unit Tests | Deterministic unit assertions | $100\%$ Deterministic ($20/20$ Pass) |

---

## 3. Cryptographic Verification of Frozen Checkpoints

Verify that the frozen weights are bitwise intact by checking their SHA256 hashes:
* `models/glucoshield_hybrid_best.pt`: `89a67710aa4931248c894819d9b626e254848a858602b93ff558832a8cb59a5c`
* `models/glucoshield_neural_best.pt`: `026af3341a9106410ea80b06b761df9bb4a45749326e6d15b0267c7e6c0c20a4`

---
*Certified for research replication.*
