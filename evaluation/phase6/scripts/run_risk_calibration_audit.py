"""
GlucoShield Phase 6 — Risk Head Evaluation & Calibration Audit
==============================================================
Evaluates discrimination (AUROC, AUPRC), probability quality (Brier Score,
Expected Calibration Error, Maximum Calibration Error), and classification
performance for all 5 acute event risk heads (hypo_1h, hypo_2h, hypo_4h,
hyper_2h, hyper_4h). Generates Figure 4 (Reliability Diagrams).
"""

import os
import sys
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    roc_auc_score, average_precision_score, brier_score_loss,
    confusion_matrix, precision_recall_fscore_support
)

# Force unbuffered output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

BASE_DIR = "D:/ML PROJECT"
DATA_DIR = os.path.join(BASE_DIR, "data", "final")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
OUT_RES_DIR = os.path.join(BASE_DIR, "evaluation", "phase6", "results")
OUT_FIG_DIR = os.path.join(BASE_DIR, "evaluation", "phase6", "figures")

os.makedirs(OUT_RES_DIR, exist_ok=True)
os.makedirs(OUT_FIG_DIR, exist_ok=True)

def compute_ece(y_true, y_prob, n_bins=10):
    """Computes Expected Calibration Error (ECE) and bin statistics."""
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2.0
    
    bin_accs = []
    bin_confs = []
    bin_counts = []
    ece = 0.0
    mce = 0.0
    n_samples = len(y_true)

    for i in range(n_bins):
        b_lo, b_hi = bin_edges[i], bin_edges[i + 1]
        if i == n_bins - 1:
            mask = (y_prob >= b_lo) & (y_prob <= b_hi)
        else:
            mask = (y_prob >= b_lo) & (y_prob < b_hi)
        
        count = int(np.sum(mask))
        bin_counts.append(count)
        if count > 0:
            acc = float(np.mean(y_true[mask]))
            conf = float(np.mean(y_prob[mask]))
            bin_accs.append(acc)
            bin_confs.append(conf)
            diff = abs(acc - conf)
            ece += (count / n_samples) * diff
            if diff > mce:
                mce = diff
        else:
            bin_accs.append(0.0)
            bin_confs.append(bin_centers[i])

    return float(ece), float(mce), bin_confs, bin_accs, bin_counts

def main():
    print("=" * 80)
    print("GLUCOSHIELD PHASE 6 — RISK HEAD EVALUATION & CALIBRATION AUDIT")
    print("=" * 80)

    # 1. Load Risk Targets and Predictions
    risk_names = ["hypo_1h", "hypo_2h", "hypo_4h", "hyper_2h", "hyper_4h"]
    risk_targets = {
        "hypo_1h": np.load(os.path.join(DATA_DIR, "Y_test_hypo_1h.npy")).flatten(),
        "hypo_2h": np.load(os.path.join(DATA_DIR, "Y_test_hypo_2h.npy")).flatten(),
        "hypo_4h": np.load(os.path.join(DATA_DIR, "Y_test_hypo_4h.npy")).flatten(),
        "hyper_2h": np.load(os.path.join(DATA_DIR, "Y_test_hyper_2h.npy")).flatten(),
        "hyper_4h": np.load(os.path.join(DATA_DIR, "Y_test_hyper_4h.npy")).flatten()
    }

    p_gru = np.load(os.path.join(RESULTS_DIR, "neural", "probs_best_neural_test.npy"))
    p_hyb = np.load(os.path.join(RESULTS_DIR, "digital_twin", "probs_risk_hybrid_test.npy"))

    audit_results = {}

    print("\n--- Evaluating 5 Acute Risk Heads on Frozen Test Set (N=4,113) ---")

    for idx, r_name in enumerate(risk_names):
        y_t = risk_targets[r_name]
        pos_count = int(np.sum(y_t))
        neg_count = int(len(y_t) - pos_count)
        prev_pct = float(pos_count / len(y_t) * 100.0)

        # Hybrid Head Probabilities
        prob_h = p_hyb[:, idx]
        prob_g = p_gru[:, idx]

        # Discrimination
        auroc_h = float(roc_auc_score(y_t, prob_h))
        auprc_h = float(average_precision_score(y_t, prob_h))
        brier_h = float(brier_score_loss(y_t, prob_h))
        ece_h, mce_h, confs_h, accs_h, counts_h = compute_ece(y_t, prob_h, n_bins=10)

        auroc_g = float(roc_auc_score(y_t, prob_g))
        auprc_g = float(average_precision_score(y_t, prob_g))
        brier_g = float(brier_score_loss(y_t, prob_g))
        ece_g, mce_g, _, _, _ = compute_ece(y_t, prob_g, n_bins=10)

        # Classification at standard threshold 0.5
        pred_bin_h = (prob_h >= 0.5).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_t, pred_bin_h).ravel()
        sens = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        spec = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
        prec = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        f1 = float(2 * tp / (2 * tp + fp + fn)) if (2 * tp + fp + fn) > 0 else 0.0

        r_dict = {
            "head_name": r_name,
            "positive_events": pos_count,
            "negative_events": neg_count,
            "prevalence_pct": round(prev_pct, 2),
            "hybrid": {
                "AUROC": round(auroc_h, 4),
                "AUPRC": round(auprc_h, 4),
                "Brier_Score": round(brier_h, 4),
                "ECE": round(ece_h, 4),
                "MCE": round(mce_h, 4),
                "Sensitivity": round(sens * 100.0, 2),
                "Specificity": round(spec * 100.0, 2),
                "Precision": round(prec * 100.0, 2),
                "F1_Score": round(f1 * 100.0, 2),
                "TP": int(tp), "FP": int(fp), "TN": int(tn), "FN": int(fn),
                "bin_confs": [round(c, 3) for c in confs_h],
                "bin_accs": [round(a, 3) for a in accs_h],
                "bin_counts": counts_h
            },
            "neural_gru": {
                "AUROC": round(auroc_g, 4),
                "AUPRC": round(auprc_g, 4),
                "Brier_Score": round(brier_g, 4),
                "ECE": round(ece_g, 4),
                "MCE": round(mce_g, 4)
            }
        }
        audit_results[r_name] = r_dict

        print(f"  [{r_name:<8}] Events: {pos_count:>4} ({prev_pct:>5.1f}%) | "
              f"AUROC={auroc_h:.4f} | AUPRC={auprc_h:.4f} | ECE={ece_h:.4f} | Brier={brier_h:.4f} | Sens={sens*100:.1f}% | Spec={spec*100:.1f}% | F1={f1*100:.1f}%")

    # Save to master JSON
    out_json_path = os.path.join(OUT_RES_DIR, "risk_calibration_metrics.json")
    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump(audit_results, f, indent=2)
    print(f"\nSaved risk calibration metrics to: {out_json_path}")

    # =========================================================================
    # PUBLICATION FIGURE 4: RELIABILITY DIAGRAMS (CALIBRATION CURVES)
    # =========================================================================
    print("\n--- Generating Figure 4: Risk Calibration Reliability Diagrams ---")
    sns.set_theme(style="whitegrid", font="sans-serif")
    fig, axes = plt.subplots(1, 5, figsize=(22, 4.5), dpi=300)

    titles = ["A. Hypo (<70) in 1h", "B. Hypo (<70) in 2h", "C. Hypo (<70) in 4h", "D. Hyper (>180) in 2h", "E. Hyper (>180) in 4h"]
    colors = ["#d62728", "#ff7f0e", "#e377c2", "#1f77b4", "#2ca02c"]

    for idx, r_name in enumerate(risk_names):
        ax = axes[idx]
        h_data = audit_results[r_name]["hybrid"]
        confs = h_data["bin_confs"]
        accs = h_data["bin_accs"]

        # Perfect calibration line
        ax.plot([0, 1], [0, 1], "k--", label="Perfect Calibration", linewidth=1.2, alpha=0.7)
        # Model calibration curve
        ax.plot(confs, accs, marker="o", linewidth=2.0, color=colors[idx], label=f"Hybrid (ECE={h_data['ECE']:.3f})")
        ax.fill_between(confs, confs, accs, color=colors[idx], alpha=0.15)

        ax.set_title(titles[idx], fontsize=11, fontweight="bold")
        ax.set_xlabel("Mean Predicted Probability", fontsize=10)
        if idx == 0:
            ax.set_ylabel("Observed Empirical Fraction", fontsize=10)
        ax.set_xlim(-0.02, 1.02)
        ax.set_ylim(-0.02, 1.02)
        ax.legend(loc="upper left", fontsize=9, frameon=True)

    plt.tight_layout()
    fig4_path = os.path.join(OUT_FIG_DIR, "fig4_risk_reliability_diagrams.png")
    plt.savefig(fig4_path, dpi=300)
    plt.close()
    print(f"  Saved Figure 4 to: {fig4_path}")
    print("=" * 80)

if __name__ == "__main__":
    main()
