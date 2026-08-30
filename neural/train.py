"""
GlucoShield Neural Model Training Engine
Handles multi-task loss computation, learning rate scheduling, early stopping, and validation checkpointing.
"""

import os
import copy
import time
import torch
import torch.nn as nn
import numpy as np
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss

from baselines.evaluate_baselines import evaluate_trajectory, clarke_error_grid

class MultiTaskLoss(nn.Module):
    def __init__(self, traj_loss_type="huber", lambda_traj=1.0, lambda_risk=10.0, pos_weights=None):
        super().__init__()
        self.traj_loss_type = traj_loss_type
        self.lambda_traj = lambda_traj
        self.lambda_risk = lambda_risk
        
        if traj_loss_type == "huber":
            self.traj_crit = nn.SmoothL1Loss(beta=5.0)
        elif traj_loss_type == "mae":
            self.traj_crit = nn.L1Loss()
        elif traj_loss_type == "mse":
            self.traj_crit = nn.MSELoss()
        else:
            raise ValueError(f"Unknown traj_loss_type: {traj_loss_type}")

        if pos_weights is not None:
            self.risk_crit = nn.BCEWithLogitsLoss(pos_weight=pos_weights)
        else:
            self.risk_crit = nn.BCEWithLogitsLoss()

    def forward(self, traj_pred, traj_true, risk_logits, risk_true):
        loss_traj = self.traj_crit(traj_pred, traj_true)
        loss_risk = self.risk_crit(risk_logits, risk_true)
        total_loss = self.lambda_traj * loss_traj + self.lambda_risk * loss_risk
        return total_loss, loss_traj, loss_risk


def train_epoch(model, loader, optimizer, loss_fn, device):
    model.train()
    total_loss, total_traj_loss, total_risk_loss = 0.0, 0.0, 0.0
    n_samples = 0

    for x_seq, static_feat, y_traj, y_risk in loader:
        x_seq = x_seq.to(device)
        static_feat = static_feat.to(device)
        y_traj = y_traj.to(device)
        y_risk = y_risk.to(device)
        batch_size = len(x_seq)

        optimizer.zero_grad()
        out = model(x_seq, static_feat)
        loss, l_traj, l_risk = loss_fn(out["trajectory"], y_traj, out["risk_logits"], y_risk)
        loss.backward()

        # Gradient clipping for stability
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=2.0)
        optimizer.step()

        total_loss += loss.item() * batch_size
        total_traj_loss += l_traj.item() * batch_size
        total_risk_loss += l_risk.item() * batch_size
        n_samples += batch_size

    return {
        "loss": total_loss / n_samples,
        "traj_loss": total_traj_loss / n_samples,
        "risk_loss": total_risk_loss / n_samples
    }


def evaluate_model(model, loader, loss_fn, device, meta_df=None):
    model.eval()
    total_loss, total_traj_loss, total_risk_loss = 0.0, 0.0, 0.0
    n_samples = 0
    
    all_traj_preds = []
    all_traj_trues = []
    all_risk_probs = []
    all_risk_trues = []

    with torch.no_grad():
        for x_seq, static_feat, y_traj, y_risk in loader:
            x_seq = x_seq.to(device)
            static_feat = static_feat.to(device)
            y_traj = y_traj.to(device)
            y_risk = y_risk.to(device)
            batch_size = len(x_seq)

            out = model(x_seq, static_feat)
            loss, l_traj, l_risk = loss_fn(out["trajectory"], y_traj, out["risk_logits"], y_risk)

            total_loss += loss.item() * batch_size
            total_traj_loss += l_traj.item() * batch_size
            total_risk_loss += l_risk.item() * batch_size
            n_samples += batch_size

            all_traj_preds.append(out["trajectory"].cpu().numpy())
            all_traj_trues.append(y_traj.cpu().numpy())
            all_risk_probs.append(out["risk_probs"].cpu().numpy())
            all_risk_trues.append(y_risk.cpu().numpy())

    preds_traj = np.concatenate(all_traj_preds, axis=0)
    trues_traj = np.concatenate(all_traj_trues, axis=0)
    probs_risk = np.concatenate(all_risk_probs, axis=0)
    trues_risk = np.concatenate(all_risk_trues, axis=0)

    # Compute trajectory metrics
    traj_metrics = evaluate_trajectory(preds_traj, trues_traj, meta_df)

    # Compute risk classification metrics for each head:
    # 0: hypo_1h, 1: hypo_2h, 2: hypo_4h, 3: hyper_2h, 4: hyper_4h
    risk_names = ["hypo_1h", "hypo_2h", "hypo_4h", "hyper_2h", "hyper_4h"]
    risk_metrics = {}
    for i, rname in enumerate(risk_names):
        p = probs_risk[:, i]
        y = trues_risk[:, i]
        
        # Binary predictions at threshold 0.5
        bin_p = (p >= 0.5).astype(float)
        
        tp = np.sum((y == 1) & (bin_p == 1))
        fp = np.sum((y == 0) & (bin_p == 1))
        tn = np.sum((y == 0) & (bin_p == 0))
        fn = np.sum((y == 1) & (bin_p == 0))

        sens = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        spec = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
        prec = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        f1 = float(2 * prec * sens / (prec + sens)) if (prec + sens) > 0 else 0.0
        brier = float(brier_score_loss(y, p))

        try:
            auroc = float(roc_auc_score(y, p))
        except:
            auroc = float("nan")
        try:
            auprc = float(average_precision_score(y, p))
        except:
            auprc = float("nan")

        risk_metrics[rname] = {
            "Sensitivity": sens,
            "Specificity": spec,
            "Precision": prec,
            "F1": f1,
            "AUROC": auroc,
            "AUPRC": auprc,
            "Brier": brier
        }

    return {
        "val_loss": total_loss / n_samples,
        "val_traj_loss": total_traj_loss / n_samples,
        "val_risk_loss": total_risk_loss / n_samples,
        "trajectory": traj_metrics,
        "risk": risk_metrics,
        "preds_traj": preds_traj,
        "probs_risk": probs_risk
    }


def train_model(
    model,
    train_loader,
    val_loader,
    meta_val,
    device,
    loss_fn,
    lr=3e-4,
    weight_decay=1e-4,
    max_epochs=25,
    patience=5,
    verbose=False
):
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=2)

    best_val_rmse = float("inf")
    best_model_state = None
    best_val_eval = None
    best_epoch = 0
    epochs_no_improve = 0

    history = {
        "train_loss": [],
        "val_loss": [],
        "val_mae": [],
        "val_rmse": [],
        "val_hypo_4h_auprc": [],
        "val_hypo_4h_sens": []
    }

    t0 = time.time()
    for epoch in range(1, max_epochs + 1):
        tr_stats = train_epoch(model, train_loader, optimizer, loss_fn, device)
        val_stats = evaluate_model(model, val_loader, loss_fn, device, meta_val)

        val_rmse = val_stats["trajectory"]["overall"]["RMSE"]
        val_mae = val_stats["trajectory"]["overall"]["MAE"]
        hypo_4h_auprc = val_stats["risk"]["hypo_4h"]["AUPRC"]
        hypo_4h_sens = val_stats["risk"]["hypo_4h"]["Sensitivity"]

        scheduler.step(val_rmse)

        history["train_loss"].append(tr_stats["loss"])
        history["val_loss"].append(val_stats["val_loss"])
        history["val_mae"].append(val_mae)
        history["val_rmse"].append(val_rmse)
        history["val_hypo_4h_auprc"].append(hypo_4h_auprc)
        history["val_hypo_4h_sens"].append(hypo_4h_sens)

        if verbose:
            print(f"  Epoch {epoch:>2}/{max_epochs}: Train Loss={tr_stats['loss']:.4f} | Val RMSE={val_rmse:.2f} mg/dL | Val MAE={val_mae:.2f} mg/dL | Hypo4h AUPRC={hypo_4h_auprc:.3f}")

        # Check improvement on validation RMSE
        if val_rmse < best_val_rmse - 1e-3:
            best_val_rmse = val_rmse
            best_epoch = epoch
            best_model_state = copy.deepcopy(model.state_dict())
            best_val_eval = val_stats
            epochs_no_improve = 0
        else:
            epochs_no_improve += 1
            if epochs_no_improve >= patience:
                if verbose:
                    print(f"  --> Early stopping triggered at epoch {epoch} (Best epoch: {best_epoch}, Best Val RMSE: {best_val_rmse:.2f} mg/dL)")
                break

    train_time = time.time() - t0
    # Restore best weights
    model.load_state_dict(best_model_state)

    return {
        "model": model,
        "best_epoch": best_epoch,
        "best_val_rmse": best_val_rmse,
        "best_val_eval": best_val_eval,
        "history": history,
        "train_time_sec": train_time
    }
