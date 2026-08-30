# GlucoShield — Day 3 Metadata Consistency Audit Report
**Document ID:** `GLUCOSHIELD-AUD-DAY3-META-001`  
**Audit Timestamp:** 2026-08-24T23:24:00Z  
**Auditor Role:** Lead ML & Data Validation Engineer  
**Status:** PASS & CERTIFIED  

---

## 1. Objective of Audit

This audit was conducted to resolve a contradiction identified in `DAY3_NEURAL_FORECASTER_REPORT.md`, where narrative text stated:
> *"the training and validation sets contained 0 T1DM sequences due to dataset source distribution. T1DM performance (37.30 mg/dL RMSE) reflects true zero-shot cross-etiology generalization"*

This statement contradicted the Dataset v1.0 Lock Manifest (`reports/dataset_lock_manifest.json`), which recorded 8 T1DM patients in Train, 2 in Validation, and 2 in Test.

---

## 2. Programmatic Audit Findings (Direct from Frozen Files)

A fresh, independent programmatic audit was executed directly on `data/final/meta_train.csv`, `data/final/meta_val.csv`, and `data/final/meta_test.csv`.

### Split-by-Split Subgroup Breakdown

| Partition | Total Patients | T1DM Patients | T2DM Patients | Total Sequences | T1DM Sequences | T2DM Sequences |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Train** | **78** | **8** ($10.3\%$) | **70** ($89.7\%$) | **19,749** | **2,514** ($12.7\%$) | **17,235** ($87.3\%$) |
| **Validation** | **17** | **2** ($11.8\%$) | **15** ($88.2\%$) | **4,585** | **449** ($9.8\%$) | **4,136** ($90.2\%$) |
| **Test** | **17** | **2** ($11.8\%$) | **15** ($88.2\%$) | **4,113** | **507** ($12.3\%$) | **3,606** ($87.7\%$) |
| **Total Cohort** | **112** | **12** ($10.7\%$) | **100** ($89.3\%$) | **28,447** | **3,470** ($12.2\%$) | **24,977** ($87.8\%$) |

---

## 3. Exact Patient IDs in Subgroups

### Type 1 Diabetes (T1DM) Patients ($N=12$ Total across cohort)
* **Train ($N=8$)**: `1001`, `1002`, `1003`, `1006`, `1009`, `1010`, `1011`, `1012`
* **Validation ($N=2$)**: `1005`, `1008`
* **Test ($N=2$)**: `1004`, `1007`

### Type 2 Diabetes (T2DM) Patients ($N=100$ Total across cohort)
* **Train ($N=70$)**: `2000`, `2003`, `2004`, `2005`, `2006`, `2007`, `2008`, `2009`, `2010`, `2011`, `2012`, `2013`, `2015`, `2016`, `2017`, `2018`, `2019`, `2022`, `2024`, `2025`, `2026`, `2027`, `2028`, `2030`, `2031`, `2033`, `2034`, `2035`, `2036`, `2038`, `2039`, `2040`, `2042`, `2043`, `2044`, `2045`, `2047`, `2049`, `2051`, `2053`, `2055`, `2056`, `2060`, `2062`, `2064`, `2065`, `2066`, `2067`, `2068`, `2069`, `2070`, `2071`, `2072`, `2073`, `2074`, `2078`, `2080`, `2081`, `2082`, `2083`, `2084`, `2085`, `2086`, `2088`, `2091`, `2092`, `2093`, `2094`, `2096`, `2099`
* **Validation ($N=15$)**: `2014`, `2041`, `2046`, `2048`, `2050`, `2054`, `2058`, `2061`, `2076`, `2077`, `2079`, `2089`, `2090`, `2097`, `2098`
* **Test ($N=15$)**: `2001`, `2002`, `2020`, `2021`, `2023`, `2029`, `2032`, `2037`, `2052`, `2057`, `2059`, `2063`, `2075`, `2087`, `2095`

---

## 4. Patient Leakage & Overlap Audit

Cross-set intersection check:
* $\text{Train} \cap \text{Validation} = \emptyset$ ($0$ patients)
* $\text{Train} \cap \text{Test} = \emptyset$ ($0$ patients)
* $\text{Validation} \cap \text{Test} = \emptyset$ ($0$ patients)

**Result:** Patient-level split isolation is **$100\%$ strictly preserved**. Zero leakage detected.

---

## 5. Root Cause Analysis of Reporting Contradiction

1. **Source of the Contradiction**: The Day 3 report drafted a narrative sentence claiming "0 T1DM sequences in train/val" as an incorrect extrapolation of T1DM being a small subset ($12.2\%$ of sequences).
2. **True State of Dataset v1.0**: The dataset is **stratified multi-cohort**, where T1DM represents $10.7\%$ of total patients (8 in Train, 2 in Val, 2 in Test) and $12.2\%$ of total sequences ($2,514$ Train, $449$ Val, $507$ Test).
3. **Correct Interpretation**:
   - The model was exposed to 8 T1DM patients during training.
   - The test set evaluation on Patients `1004` and `1007` represents **cross-patient generalization within an imbalanced T1DM minority class**, NOT "zero-shot cross-disease transfer".
   - The sample size for T1DM testing remains small ($N=2$ patients, $507$ sequences), requiring caution when drawing standalone T1DM subgroup conclusions.

---

## 6. Corrective Actions Taken

1. **Dataset v1.0 Tensors and Splits**: **UNMODIFIED**. All 33 data files, splits, and checkpoints remain locked and untouched.
2. **Report Wording**: `DAY3_NEURAL_FORECASTER_REPORT.md` Section 8 is updated to remove the phrase *"zero-shot cross-etiology generalization"* and correctly state that T1DM was trained on 8 stratified patients and tested on 2 held-out patients.
