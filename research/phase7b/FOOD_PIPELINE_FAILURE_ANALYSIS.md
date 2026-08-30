# GlucoShield — Food Vision & Nutrition Pipeline Failure Taxonomy
**Document ID:** `GLUCOSHIELD-RPT-PHASE7B-FAIL-001`  
**Timestamp:** 2026-08-28T17:00:00 Local Time  
**Author:** Lead Deep Learning & Physiological Systems Engineer  
**Status:** **FAILURE TAXONOMY CERTIFIED**  

---

## 1. Executive Overview

This document establishes a rigorous **9-category failure taxonomy** for real-world automated and semi-automated dietary analysis in diabetes management.

Each failure category is analyzed for:
* **Clinical Severity (1-10):** Glycemic impact on insulin dosing and glucose prediction.
* **Automated Detection Feasibility:** Can algorithms flag this failure autonomously?
* **Mitigation Strategy:** Technical safeguards to prevent clinical risk.
* **Role of Human Confirmation:** Does human-in-the-loop oversight resolve the error?

---

## 2. The 9 Failure Taxonomy Categories

| # | Failure Mode | Real-World Scenario / Example | Clinical Glycemic Severity (1-10) | Auto-Detection Possible? | Mitigation Strategy | Human Confirmation Solves It? |
|:---:|---|---|:---:|:---:|---|:---:|
| **1** | **Visual Recognition Failure** | Steamed Idli misclassified as a coconut dumpling or steamed bao bun. | **7.5 / 10** | **YES** (Low softmax probability or high entropy). | Present top-K candidate chips; provide 1-tap search bar fallback. | **YES** (User selects or searches correct food). |
| **2** | **Candidate Ranking Failure** | Correct dish is present in Top-5, but ranked 3rd or 4th behind generic labels. | **5.0 / 10** | **PARTIALLY** (Ambiguity delta $|p_1 - p_2| < 0.15$). | Render visual candidate chips with high UI prominence; do not auto-select. | **YES** (User taps the correct chip). |
| **3** | **Synonym / Naming Mismatch** | User searches "Roti", but database indexes "Chapati" or "Whole Wheat Flatbread". | **4.0 / 10** | **YES** (Fuzzy string matching / Levenshtein distance). | Multi-synonym lookup dictionary; alias mapping table. | **YES** (User picks closest synonym). |
| **4** | **Database Nutrient Mismatch** | Database returns dry uncooked flour density ($72\text{g carbs}/100\text{g}$) instead of cooked dish ($28\text{g}/100\text{g}$). | **8.5 / 10** | **YES** (Detect "raw/uncooked/flour/mix" keyword flags). | Filter out raw/dry entries; require explicit "Cooked" tag verification. | **YES** (User checks per-100g reasonableness). |
| **5** | **Portion Estimation Error** | User logs 1 large samosa ($110\text{g}$) as $60\text{g}$ ($-45\%$ error), underestimating carbs by $16.5\text{g}$. | **9.0 / 10** (Highest Common Error) | **NO** (Without depth/reference object, camera is scale-blind). | Visual portion reference guides (e.g. "Size of tennis ball $\approx 80\text{g}$"); default serving buttons. | **PARTIALLY** (Requires user portion literacy). |
| **6** | **Composite Dish Ambiguity** | Vegetable Biryani with varying ratios of rice vs potato vs paneer. | **6.5 / 10** | **PARTIALLY** (Multi-label segmentation). | Display standard composite recipe assumptions; allow ingredient breakdown. | **YES** (User refines component ratios). |
| **7** | **Hidden Ingredients / Oils** | Restaurant curry prepared with $30\text{g}$ of hidden cream/sugar syrup vs homemade. | **8.5 / 10** | **NO** (Hidden solutes are visually invisible in RGB). | Add "Restaurant / Rich Preparation" toggle (+20% fat/carb adjustment). | **YES** (User specifies dining context). |
| **8** | **API / Network Failure** | Offline mode, cellular dead zone, or USDA / Hugging Face rate limit. | **6.0 / 10** | **YES** (HTTP status codes / timeouts). | Fall back to local SQLite offline nutrition cache and local MobileNetV3. | **YES** (User enters manual carb estimate). |
| **9** | **Complete Missed Meal Logging** | Patient eats without opening the app or logging meal. | **10.0 / 10** (Phase 6 #1 Failure) | **NO** (No telemetry received). | Digital Twin anomaly detector flags unexpected glucose surge and prompts user: "Did you just eat?". | **YES** (Post-hoc confirmation). |

---

## 3. Fundamental Clinical Governance Conclusion

```
+-----------------------------------------------------------------------------+
| KEY SCIENTIFIC TAKEAWAY:                                                    |
| Portion misestimation (Failure #5) and hidden ingredients (Failure #7)      |
| are responsible for larger carbohydrate errors than visual classification.  |
|                                                                             |
| An AI model that accurately identifies a plate as "Rice" but applies an     |
| incorrect portion (e.g. 100g vs 250g) introduces a 42.3g carbohydrate error!|
|                                                                             |
| Therefore, GlucoShield enforces:                                            |
| 1. Mandatory Human Confirmation                                             |
| 2. Visual Portion Size Reference Guides                                      |
| 3. Explicit Uncertainty Bounds (95% Confidence Intervals)                   |
+-----------------------------------------------------------------------------+
```

---
*Certified for Phase 7B failure analysis.*
