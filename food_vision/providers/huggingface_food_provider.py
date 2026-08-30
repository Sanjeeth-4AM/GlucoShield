"""
GlucoShield Hugging Face Food Recognition Provider
==================================================
Interfaces with Hugging Face serverless food classification models (e.g., Food-101 ViT)
to predict top-K food item candidate labels from meal images.
"""

import os
import json
import urllib.request
from typing import List, Union, Optional
from food_vision.providers.base import BaseFoodRecognitionProvider
from food_vision.schemas import FoodCandidate

class HuggingFaceFoodRecognitionProvider(BaseFoodRecognitionProvider):
    """
    Connects to Hugging Face Inference API for food category classification.
    Uses open food classification models (e.g., 'nateraw/food' fine-tuned on Food-101).
    """
    def __init__(
        self,
        api_token: Optional[str] = None,
        model_id: str = "nateraw/food",
        timeout: int = 10
    ):
        self.api_token = api_token or os.getenv("HUGGINGFACE_API_TOKEN", "")
        self.model_id = model_id
        self.timeout = timeout
        self.api_url = f"https://api-inference.huggingface.co/models/{model_id}"

    @property
    def provider_name(self) -> str:
        return f"huggingface_inference_api ({self.model_id})"

    @property
    def is_available(self) -> bool:
        # Hugging Face serverless inference is available if a token is set or public endpoint accessible
        return True

    def recognize_food(
        self,
        image_input: Union[str, bytes],
        top_k: int = 5
    ) -> List[FoodCandidate]:
        if not self.is_available:
            return []

        # Read binary image data
        if isinstance(image_input, str):
            if not os.path.exists(image_input):
                return []
            with open(image_input, "rb") as f:
                img_data = f.read()
        elif isinstance(image_input, bytes):
            img_data = image_input
        else:
            return []

        headers = {
            "User-Agent": "GlucoShield-FoodVision/1.0"
        }
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        req = urllib.request.Request(self.api_url, data=img_data, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status != 200:
                    return []
                data = json.loads(resp.read().decode("utf-8"))
                
                # Hugging Face image classification output: list of {"label": str, "score": float}
                if not isinstance(data, list):
                    return []

                candidates = []
                for item in data[:top_k]:
                    raw_lbl = item.get("label", "")
                    # Clean food label (e.g., 'french_fries' -> 'French Fries')
                    clean_name = raw_lbl.replace("_", " ").title()
                    score = float(item.get("score", 0.0))
                    candidates.append(FoodCandidate(
                        name=clean_name,
                        confidence=score,
                        source=f"HuggingFace ({self.model_id})",
                        raw_label=raw_lbl
                    ))
                return candidates

        except Exception:
            # Network failure, model loading, or API limit: return empty candidates gracefully
            return []
