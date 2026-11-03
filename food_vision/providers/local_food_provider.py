"""
GlucoShield Local Food Recognition Provider
===========================================
Executes local PyTorch inference for food category classification using a fine-tuned
Food-101 Vision Transformer (ViT) model (nateraw/food).
Runs on local CUDA GPU if available (e.g., NVIDIA RTX), otherwise falls back to CPU.
Weights and preprocessor configs are cached locally in models/food101/.
"""

import os
import io
import logging
from typing import List, Union, Optional, Dict, Any
from pathlib import Path
from PIL import Image

import torch
from transformers import AutoImageProcessor, AutoModelForImageClassification

from food_vision.providers.base import BaseFoodRecognitionProvider
from food_vision.schemas import FoodCandidate
from food_vision.image_preprocessing import preprocess_meal_image, ImagePreprocessingError

logger = logging.getLogger(__name__)

# Module-level model and processor cache to prevent reloading weights on every request
_CACHED_PROCESSOR = None
_CACHED_MODEL = None
_CACHED_DEVICE = None
_CACHED_MODEL_PATH = None


class LocalFoodRecognitionProvider(BaseFoodRecognitionProvider):
    """
    Local food recognition provider running on PyTorch + Transformers.
    Performs genuine top-K classification over the 101 Food-101 classes.
    """

    def __init__(
        self,
        model_dir: Optional[Union[str, Path]] = None,
        device: Optional[str] = None
    ):
        """
        Args:
            model_dir: Path to directory containing Food-101 model weights and configs.
                       Defaults to project root 'models/food101'.
            device: 'cuda', 'cpu', or None (auto-detect).
        """
        if model_dir is None:
            # Default to <project_root>/models/food101
            project_root = Path(__file__).resolve().parent.parent.parent
            self.model_dir = str(project_root / "models" / "food101")
        else:
            self.model_dir = str(model_dir)

        # Device determination
        if device is not None:
            self.device_str = device
        elif torch.cuda.is_available():
            self.device_str = "cuda"
        else:
            self.device_str = "cpu"

        self.device = torch.device(self.device_str)
        self.last_error: Optional[str] = None
        self.last_image_meta: Optional[Dict[str, Any]] = None
        self.last_inference_device: Optional[str] = None

    @property
    def provider_name(self) -> str:
        return f"Local Food-101 ViT ({self.device_str})"

    @property
    def is_available(self) -> bool:
        """Returns True if local model checkpoint files exist."""
        p = Path(self.model_dir)
        has_config = (p / "config.json").is_file()
        has_weights = (
            (p / "pytorch_model.bin").is_file()
            or (p / "model.safetensors").is_file()
        )
        return has_config and has_weights

    def _ensure_loaded(self) -> bool:
        """
        Loads processor and model into memory if not already cached.
        Returns True if loaded, False if files are missing or loading failed.
        """
        global _CACHED_PROCESSOR, _CACHED_MODEL, _CACHED_DEVICE, _CACHED_MODEL_PATH

        if (
            _CACHED_MODEL is not None
            and _CACHED_PROCESSOR is not None
            and _CACHED_MODEL_PATH == self.model_dir
            and _CACHED_DEVICE == self.device_str
        ):
            return True

        if not self.is_available:
            self.last_error = (
                f"Local Food-101 model files not found in '{self.model_dir}'. "
                "Ensure config.json and pytorch_model.bin (or model.safetensors) are present."
            )
            return False

        try:
            logger.info("Loading local Food-101 processor from %s", self.model_dir)
            processor = AutoImageProcessor.from_pretrained(self.model_dir)

            logger.info("Loading local Food-101 model onto %s from %s", self.device_str, self.model_dir)
            model = AutoModelForImageClassification.from_pretrained(self.model_dir)
            model.to(self.device)
            model.eval()

            _CACHED_PROCESSOR = processor
            _CACHED_MODEL = model
            _CACHED_DEVICE = self.device_str
            _CACHED_MODEL_PATH = self.model_dir
            logger.info("Local Food-101 model loaded successfully on %s", self.device_str)
            return True
        except Exception as e:
            self.last_error = f"Failed to load local Food-101 model: {str(e)}"
            logger.error(self.last_error, exc_info=True)
            return False

    def recognize_food(
        self,
        image_input: Union[str, bytes],
        top_k: int = 5
    ) -> List[FoodCandidate]:
        """
        Performs local ViT inference on meal image input.
        Returns ranked list of FoodCandidate objects with genuine probabilities.
        """
        self.last_error = None
        self.last_image_meta = None
        self.last_inference_device = None

        # 1. Read binary image data
        if isinstance(image_input, str):
            if not os.path.exists(image_input):
                self.last_error = f"Image file not found: {image_input}"
                return []
            with open(image_input, "rb") as f:
                img_data = f.read()
        elif isinstance(image_input, bytes):
            img_data = image_input
        else:
            self.last_error = "Invalid image input format. Expected file path or raw bytes."
            return []

        if not img_data:
            self.last_error = "Image input bytes are empty."
            return []

        # 2. Safe image preprocessing
        try:
            processed_data, meta = preprocess_meal_image(img_data)
            self.last_image_meta = meta
        except ImagePreprocessingError as e:
            self.last_error = str(e)
            return []
        except Exception as e:
            self.last_error = f"Image validation error: {str(e)}"
            return []

        # 3. Ensure model is loaded
        if not self._ensure_loaded():
            return []

        global _CACHED_PROCESSOR, _CACHED_MODEL

        # 4. Convert processed JPEG bytes to PIL RGB image
        try:
            pil_image = Image.open(io.BytesIO(processed_data)).convert("RGB")
        except Exception as e:
            self.last_error = f"Failed to decode preprocessed image: {str(e)}"
            return []

        # 5. Run processor and forward pass
        try:
            inputs = _CACHED_PROCESSOR(images=pil_image, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = _CACHED_MODEL(**inputs)
                logits = outputs.logits
                probs = torch.softmax(logits, dim=-1)[0]

            self.last_inference_device = str(self.device)

            # 6. Extract top-k candidates
            k = min(top_k, probs.size(0))
            top_probs, top_indices = torch.topk(probs, k=k)

            candidates: List[FoodCandidate] = []
            id2label = _CACHED_MODEL.config.id2label

            for prob, idx in zip(top_probs, top_indices):
                idx_int = idx.item()
                raw_label = id2label.get(idx_int, id2label.get(str(idx_int), f"class_{idx_int}"))
                clean_name = raw_label.replace("_", " ").title()
                score = round(float(prob.item()), 4)

                candidates.append(FoodCandidate(
                    name=clean_name,
                    confidence=score,
                    source=f"Local Food-101 ViT ({self.device_str})",
                    raw_label=raw_label
                ))

            return candidates

        except Exception as e:
            self.last_error = f"Local visual inference error: {str(e)}"
            logger.error(self.last_error, exc_info=True)
            return []
