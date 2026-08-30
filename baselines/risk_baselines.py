"""
GlucoShield Risk Baseline Evaluation
Evaluates acute clinical event detection (Hypoglycemia <70 mg/dL, Hyperglycemia >180 mg/dL).
"""

import numpy as np

def calculate_classification_metrics(y_true, y_pred_bin, y_score=None):
    """
    Computes standard clinical risk metrics: Sensitivity, Specificity, Precision, F1, Balanced Accuracy.
    """
    y_true = np.asarray(y_true, dtype=bool)
    y_pred_bin = np.asarray(y_pred_bin, dtype=bool)

    tp = int(np.sum(y_true & y_pred_bin))
    fp = int(np.sum((~y_true) & y_pred_bin))
    tn = int(np.sum((~y_true) & (~y_pred_bin)))
    fn = int(np.sum(y_true & (~y_pred_bin)))

    sens = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    spec = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
    prec = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    f1 = float(2 * prec * sens / (prec + sens)) if (prec + sens) > 0 else 0.0
    bal_acc = float(0.5 * (sens + spec))
    prevalence = float(np.mean(y_true))

    res = {
        "TP": tp, "FP": fp, "TN": tn, "FN": fn,
        "Prevalence": prevalence,
        "Sensitivity": sens,
        "Specificity": spec,
        "Precision": prec,
        "F1": f1,
        "Balanced_Accuracy": bal_acc
    }
    return res


def evaluate_risk_predictions(Y_pred_traj, targets_dict):
    """
    Derives risk events from predicted trajectory and evaluates against true clinical labels.
    
    Args:
        Y_pred_traj: np.ndarray of shape (N, 20)
        targets_dict: dict with keys 'hypo_1h', 'hypo_2h', 'hypo_4h', 'hyper_2h', 'hyper_4h'
    """
    # 1. Hypoglycemia events (< 70 mg/dL)
    pred_hypo_1h = np.min(Y_pred_traj[:, :4], axis=1) < 70.0
    pred_hypo_2h = np.min(Y_pred_traj[:, :8], axis=1) < 70.0
    pred_hypo_4h = np.min(Y_pred_traj[:, :16], axis=1) < 70.0

    # 2. Hyperglycemia events (> 180 mg/dL)
    pred_hyper_2h = np.max(Y_pred_traj[:, :8], axis=1) > 180.0
    pred_hyper_4h = np.max(Y_pred_traj[:, :16], axis=1) > 180.0

    metrics = {
        "hypo_1h": calculate_classification_metrics(targets_dict["hypo_1h"], pred_hypo_1h),
        "hypo_2h": calculate_classification_metrics(targets_dict["hypo_2h"], pred_hypo_2h),
        "hypo_4h": calculate_classification_metrics(targets_dict["hypo_4h"], pred_hypo_4h),
        "hyper_2h": calculate_classification_metrics(targets_dict["hyper_2h"], pred_hyper_2h),
        "hyper_4h": calculate_classification_metrics(targets_dict["hyper_4h"], pred_hyper_4h),
    }
    return metrics
