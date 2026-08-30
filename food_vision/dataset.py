"""
GlucoShield Food Vision Dataset Interface
=========================================
PyTorch Dataset and DataLoader loaders for meal image macronutrient regression.
Provides flexible column mapping for Nutrition5k, NutritionVerse, and custom food datasets.
"""

import os
import pandas as pd
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from PIL import Image
from typing import Dict, List, Optional, Callable, Tuple

class NutritionDataset(Dataset):
    """
    General-purpose food image dataset for multi-macronutrient regression.
    
    Expected targets:
      [carbohydrates_g, protein_g, total_fat_g, calories_kcal]
    """
    def __init__(
        self,
        metadata_df: pd.DataFrame,
        image_dir: str,
        image_col: str = "image_path",
        carb_col: str = "carbs_g",
        protein_col: str = "protein_g",
        fat_col: str = "fat_g",
        calorie_col: str = "calories_kcal",
        transform: Optional[Callable] = None
    ):
        self.df = metadata_df.reset_index(drop=True)
        self.image_dir = image_dir
        self.image_col = image_col
        self.carb_col = carb_col
        self.protein_col = protein_col
        self.fat_col = fat_col
        self.calorie_col = calorie_col
        self.transform = transform

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, str]:
        row = self.df.iloc[idx]
        img_rel_path = str(row[self.image_col])
        full_img_path = os.path.join(self.image_dir, img_rel_path) if not os.path.isabs(img_rel_path) else img_rel_path

        # Load RGB Image
        if os.path.exists(full_img_path):
            img = Image.open(full_img_path).convert("RGB")
        else:
            # Fallback placeholder image (e.g. for mock testing or missing file safety)
            img = Image.new("RGB", (224, 224), color=(128, 128, 128))

        if self.transform:
            img_tensor = self.transform(img)
        else:
            img_tensor = torch.tensor(np.array(img), dtype=torch.float32).permute(2, 0, 1) / 255.0

        # Extract Targets: [carbs, protein, fat, calories]
        targets = np.array([
            float(row[self.carb_col]),
            float(row[self.protein_col]),
            float(row[self.fat_col]),
            float(row[self.calorie_col])
        ], dtype=np.float32)

        target_tensor = torch.tensor(targets, dtype=torch.float32)
        dish_id = str(row.get("dish_id", f"dish_{idx}"))

        return img_tensor, target_tensor, dish_id


def create_food_dataloaders(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    image_dir: str,
    batch_size: int = 32,
    num_workers: int = 0,
    train_transform: Optional[Callable] = None,
    eval_transform: Optional[Callable] = None,
    column_mapping: Optional[Dict[str, str]] = None
) -> Tuple[DataLoader, DataLoader]:
    """
    Factory creating PyTorch DataLoaders for training and evaluation.
    """
    col_map = column_mapping or {
        "image_col": "image_path",
        "carb_col": "carbs_g",
        "protein_col": "protein_g",
        "fat_col": "fat_g",
        "calorie_col": "calories_kcal"
    }

    train_ds = NutritionDataset(
        metadata_df=train_df,
        image_dir=image_dir,
        transform=train_transform,
        **col_map
    )

    val_ds = NutritionDataset(
        metadata_df=val_df,
        image_dir=image_dir,
        transform=eval_transform,
        **col_map
    )

    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True,
        drop_last=True
    )

    val_loader = DataLoader(
        val_ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True
    )

    return train_loader, val_loader
