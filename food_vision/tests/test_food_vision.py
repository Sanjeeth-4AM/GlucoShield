"""
GlucoShield Food Vision Automated Unit Tests
============================================
Comprehensive test suite verifying model forward passes, gradient flow,
loss formulations, dataset loaders, baselines, and evaluation metrics.
"""

import os
import sys
import unittest
import torch
import numpy as np
import pandas as pd
from PIL import Image

sys.path.insert(0, "D:/ML PROJECT")
from food_vision.models import MacronutrientRegressor, MultiTaskMacronutrientLoss
from food_vision.transforms import get_train_transforms, get_eval_transforms
from food_vision.dataset import NutritionDataset
from food_vision.baselines import MeanMacronutrientBaseline, MedianMacronutrientBaseline, ColorTextureRidgeBaseline
from food_vision.evaluate import evaluate_macronutrient_predictions, evaluate_uncertainty_calibration

class TestFoodVisionModule(unittest.TestCase):

    def setUp(self):
        torch.manual_seed(42)
        np.random.seed(42)

    def test_01_model_forward_shape_and_non_negativity(self):
        """Test 1: Model outputs shape (B, 4) with physical non-negativity constraint."""
        model = MacronutrientRegressor(backbone_name="mobilenet_v3_large", pretrained=False)
        model.eval()
        dummy_input = torch.randn(4, 3, 224, 224)
        out = model(dummy_input)

        self.assertEqual(out.shape, (4, 4))
        self.assertTrue(torch.all(out >= 0.0), "Predicted macronutrients must be non-negative!")

    def test_02_mc_dropout_uncertainty(self):
        """Test 2: MC-Dropout produces valid mean and positive standard deviation."""
        model = MacronutrientRegressor(backbone_name="mobilenet_v3_large", pretrained=False, dropout_p=0.3)
        dummy_input = torch.randn(2, 3, 224, 224)
        mean_preds, std_preds = model.predict_with_uncertainty(dummy_input, num_mc_samples=5)

        self.assertEqual(mean_preds.shape, (2, 4))
        self.assertEqual(std_preds.shape, (2, 4))
        self.assertTrue(torch.all(std_preds >= 0.0))

    def test_03_multitask_loss_and_gradients(self):
        """Test 3: Loss function computes valid scalar loss and backpropagates gradients."""
        criterion = MultiTaskMacronutrientLoss()
        preds = torch.tensor([[30.0, 15.0, 10.0, 270.0], [50.0, 25.0, 20.0, 480.0]], requires_grad=True)
        targets = torch.tensor([[35.0, 12.0, 8.0, 260.0], [45.0, 30.0, 18.0, 462.0]])

        loss_dict = criterion(preds, targets)
        total_loss = loss_dict["total_loss"]
        
        self.assertTrue(total_loss.item() > 0.0)
        total_loss.backward()
        self.assertIsNotNone(preds.grad)
        self.assertTrue(torch.all(torch.isfinite(preds.grad)))

    def test_04_transforms_pipeline(self):
        """Test 4: Transforms convert PIL Image to normalized (3, 224, 224) float tensor."""
        raw_img = Image.new("RGB", (300, 400), color=(100, 150, 200))
        t_eval = get_eval_transforms(image_size=224)
        tensor_img = t_eval(raw_img)

        self.assertEqual(tensor_img.shape, (3, 224, 224))
        self.assertEqual(tensor_img.dtype, torch.float32)

    def test_05_dataset_interface(self):
        """Test 5: Dataset loads metadata rows and outputs (img, target, id) tuples."""
        df_mock = pd.DataFrame({
            "image_path": ["img1.png", "img2.png"],
            "carbs_g": [45.0, 60.0],
            "protein_g": [20.0, 30.0],
            "fat_g": [15.0, 10.0],
            "calories_kcal": [395.0, 450.0],
            "dish_id": ["dish_1", "dish_2"]
        })

        t_eval = get_eval_transforms(image_size=224)
        ds = NutritionDataset(
            metadata_df=df_mock,
            image_dir="/nonexistent_dir",
            transform=t_eval
        )

        self.assertEqual(len(ds), 2)
        img_t, target_t, dish_id = ds[0]
        self.assertEqual(img_t.shape, (3, 224, 224))
        self.assertEqual(target_t.shape, (4,))
        self.assertEqual(dish_id, "dish_1")
        np.testing.assert_allclose(target_t.numpy(), [45.0, 20.0, 15.0, 395.0])

    def test_06_baselines_functionality(self):
        """Test 6: Baseline models fit and produce accurate shape predictions."""
        y_train = np.array([
            [20.0, 10.0, 5.0, 165.0],
            [40.0, 20.0, 15.0, 375.0],
            [60.0, 30.0, 25.0, 585.0]
        ], dtype=np.float32)

        mean_base = MeanMacronutrientBaseline()
        mean_base.fit(y_train)
        preds_mean = mean_base.predict(2)
        self.assertEqual(preds_mean.shape, (2, 4))
        np.testing.assert_allclose(preds_mean[0], [40.0, 20.0, 15.0, 375.0])

        median_base = MedianMacronutrientBaseline()
        median_base.fit(y_train)
        preds_med = median_base.predict(2)
        np.testing.assert_allclose(preds_med[0], [40.0, 20.0, 15.0, 375.0])

        color_base = ColorTextureRidgeBaseline()
        dummy_imgs = np.random.rand(3, 224, 224, 3).astype(np.float32)
        color_base.fit(dummy_imgs, y_train)
        preds_color = color_base.predict(dummy_imgs)
        self.assertEqual(preds_color.shape, (3, 4))
        self.assertTrue(np.all(preds_color >= 0.0))

    def test_07_evaluation_metrics_and_calibration(self):
        """Test 7: Regression metrics and uncertainty calibration calculations."""
        y_true = np.array([[50.0, 20.0, 10.0, 370.0], [30.0, 10.0, 5.0, 205.0]], dtype=np.float32)
        y_pred = np.array([[52.0, 18.0, 12.0, 388.0], [28.0, 11.0, 6.0, 210.0]], dtype=np.float32)
        y_std = np.array([[2.0, 1.5, 1.0, 10.0], [1.5, 1.0, 0.8, 8.0]], dtype=np.float32)

        eval_res = evaluate_macronutrient_predictions(y_true, y_pred)
        self.assertAlmostEqual(eval_res["carbs"]["MAE"], 2.0)
        self.assertAlmostEqual(eval_res["protein"]["MAE"], 1.5)
        self.assertAlmostEqual(eval_res["fat"]["MAE"], 1.5)
        self.assertAlmostEqual(eval_res["calories"]["MAE"], 11.5)

        calib_res = evaluate_uncertainty_calibration(y_true, y_pred, y_std, z_score=1.96)
        self.assertTrue(0.0 <= calib_res["carbs"]["empirical_coverage_pct"] <= 100.0)

if __name__ == "__main__":
    unittest.main()
