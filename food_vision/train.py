"""
GlucoShield Food Vision Training Pipeline
=========================================
Modular PyTorch training pipeline for Multi-Macronutrient Regression.
Supports:
  - MobileNetV3-Large & EfficientNet-B0 backbones
  - Automatic Mixed Precision (AMP FP16)
  - AdamW Optimizer + Cosine Annealing Learning Rate Scheduler
  - Multi-Task Huber Loss with target scale balancing
  - Validation tracking, early stopping, and checkpointing
"""

import os
import time
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from typing import Dict, Any, Optional
from food_vision.models import MacronutrientRegressor, MultiTaskMacronutrientLoss

def train_epoch(
    model: nn.Module,
    dataloader: DataLoader,
    optimizer: torch.optim.Optimizer,
    criterion: nn.Module,
    scaler: Optional[torch.amp.GradScaler],
    device: torch.device
) -> Dict[str, float]:
    """Runs one training epoch."""
    model.train()
    total_loss = 0.0
    total_carb_l = 0.0
    total_prot_l = 0.0
    total_fat_l = 0.0
    total_cal_l = 0.0
    n_batches = len(dataloader)

    for images, targets, _ in dataloader:
        images = images.to(device, non_blocking=True)
        targets = targets.to(device, non_blocking=True)

        optimizer.zero_grad(set_to_none=True)

        if scaler is not None and device.type == "cuda":
            with torch.amp.autocast(device_type="cuda"):
                preds = model(images)
                loss_dict = criterion(preds, targets)
                loss = loss_dict["total_loss"]
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
        else:
            preds = model(images)
            loss_dict = criterion(preds, targets)
            loss = loss_dict["total_loss"]
            loss.backward()
            optimizer.step()

        total_loss += float(loss.item())
        total_carb_l += float(loss_dict["loss_carbs"].item())
        total_prot_l += float(loss_dict["loss_protein"].item())
        total_fat_l  += float(loss_dict["loss_fat"].item())
        total_cal_l  += float(loss_dict["loss_calories"].item())

    return {
        "train_loss": total_loss / max(1, n_batches),
        "train_carb_loss": total_carb_l / max(1, n_batches),
        "train_prot_loss": total_prot_l / max(1, n_batches),
        "train_fat_loss": total_fat_l / max(1, n_batches),
        "train_cal_loss": total_cal_l / max(1, n_batches)
    }

def validate_epoch(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    device: torch.device
) -> Dict[str, float]:
    """Runs one validation epoch and computes validation losses and MAE."""
    model.eval()
    total_loss = 0.0
    all_preds = []
    all_targets = []

    with torch.no_grad():
        for images, targets, _ in dataloader:
            images = images.to(device, non_blocking=True)
            targets = targets.to(device, non_blocking=True)

            preds = model(images)
            loss_dict = criterion(preds, targets)
            total_loss += float(loss_dict["total_loss"].item())

            all_preds.append(preds.cpu())
            all_targets.append(targets.cpu())

    n_batches = len(dataloader)
    cat_preds = torch.cat(all_preds, dim=0).numpy()
    cat_targets = torch.cat(all_targets, dim=0).numpy()
    diff = cat_preds - cat_targets

    return {
        "val_loss": total_loss / max(1, n_batches),
        "val_carb_mae": float(np_mean_abs(diff[:, 0])),
        "val_prot_mae": float(np_mean_abs(diff[:, 1])),
        "val_fat_mae":  float(np_mean_abs(diff[:, 2])),
        "val_cal_mae":  float(np_mean_abs(diff[:, 3])),
        "val_overall_mae": float(np_mean_abs(diff))
    }

def np_mean_abs(arr):
    import numpy as np
    return np.mean(np.abs(arr))

def train_food_vision_model(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    num_epochs: int = 30,
    learning_rate: float = 1e-3,
    weight_decay: float = 1e-4,
    patience: int = 7,
    save_path: str = "food_vision/checkpoints/food_vision_best.pt",
    device: Optional[torch.device] = None
) -> Dict[str, Any]:
    """
    Main training loop for food vision macronutrient regression.
    """
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)

    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=num_epochs, eta_min=1e-6)
    criterion = MultiTaskMacronutrientLoss()
    scaler = torch.amp.GradScaler("cuda") if device.type == "cuda" else None

    best_val_loss = float("inf")
    patience_counter = 0
    history = []

    print(f"Starting Food Vision Training on: {device} ({num_epochs} epochs)...")
    start_time = time.time()

    for epoch in range(1, num_epochs + 1):
        ep_start = time.time()
        train_metrics = train_epoch(model, train_loader, optimizer, criterion, scaler, device)
        val_metrics = validate_epoch(model, val_loader, criterion, device)
        scheduler.step()

        ep_duration = time.time() - ep_start
        epoch_info = {
            "epoch": epoch,
            "lr": optimizer.param_groups[0]["lr"],
            "duration_s": round(ep_duration, 2),
            **train_metrics,
            **val_metrics
        }
        history.append(epoch_info)

        print(f"Epoch {epoch:>2}/{num_epochs} [{ep_duration:>4.1f}s]: "
              f"Train Loss={train_metrics['train_loss']:.4f} | "
              f"Val Loss={val_metrics['val_loss']:.4f} | "
              f"Val Carb MAE={val_metrics['val_carb_mae']:.2f}g | "
              f"Val Cal MAE={val_metrics['val_cal_mae']:.1f}kcal")

        # Checkpoint Best Model based on Validation Loss
        if val_metrics["val_loss"] < best_val_loss:
            best_val_loss = val_metrics["val_loss"]
            patience_counter = 0
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "config": {
                    "backbone_name": getattr(model, "backbone_name", "mobilenet_v3_large"),
                    "num_targets": getattr(model, "num_targets", 4)
                },
                "best_val_metrics": val_metrics
            }, save_path)
            print(f"  --> Saved new best checkpoint to: {save_path}")
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"Early stopping triggered at epoch {epoch} (patience={patience}).")
                break

    total_training_time = time.time() - start_time
    print(f"Training Complete in {total_training_time:.2f}s! Best Val Loss: {best_val_loss:.4f}")

    return {
        "best_val_loss": best_val_loss,
        "total_training_time_s": total_training_time,
        "history": history
    }
