"""
GlucoShield Hugging Face Food Recognition Provider
==================================================
Interfaces with Hugging Face serverless food classification models (e.g., Food-101 ViT)
to predict top-K food item candidate labels from meal images.
"""

import os
import json
import urllib.request
import urllib.error
from typing import List, Union, Optional, Dict, Any
from food_vision.providers.base import BaseFoodRecognitionProvider
from food_vision.schemas import FoodCandidate
from food_vision.image_preprocessing import preprocess_meal_image, ImagePreprocessingError

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
        self.api_url = f"https://router.huggingface.co/hf-inference/models/{model_id}"
        self.last_error: Optional[str] = None
        self.last_image_meta: Optional[Dict[str, Any]] = None

    @property
    def provider_name(self) -> str:
        return f"huggingface_inference_api ({self.model_id})"

    @property
    def is_available(self) -> bool:
        # Hugging Face serverless inference via modern router requires an API token
        return bool(self.api_token)

    def recognize_food(
        self,
        image_input: Union[str, bytes],
        top_k: int = 5
    ) -> List[FoodCandidate]:
        self.last_error = None
        self.last_image_meta = None

        if not self.api_token:
            self.last_error = "HUGGINGFACE_API_TOKEN is not configured. Serverless vision inference requires an API key."
            return []

        # Read binary image data
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

        # Safe image preprocessing: orientation correction, proportional resize (<= 1024px),
        # color space preservation (RGB), and bounded JPEG compression
        try:
            processed_data, meta = preprocess_meal_image(img_data)
            self.last_image_meta = meta
        except ImagePreprocessingError as e:
            self.last_error = str(e)
            return []
        except Exception as e:
            self.last_error = f"Image validation error: {str(e)}."
            return []

        headers = {
            "User-Agent": "GlucoShield-FoodVision/1.0",
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "image/jpeg"
        }

        req = urllib.request.Request(self.api_url, data=processed_data, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status != 200:
                    self.last_error = f"Hugging Face returned HTTP status {resp.status}."
                    return []
                data = json.loads(resp.read().decode("utf-8"))
                
                # Hugging Face image classification output: list of {"label": str, "score": float}
                if not isinstance(data, list):
                    self.last_error = f"Unexpected response format from Hugging Face: {type(data).__name__}."
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

        except urllib.error.HTTPError as e:
            if e.code == 401:
                self.last_error = "Hugging Face authentication failed (401 Unauthorized). Verify HUGGINGFACE_API_TOKEN."
            elif e.code == 413:
                self.last_error = "Hugging Face payload too large (413 Payload Too Large). Image exceeds provider size limit."
            elif e.code == 503:
                self.last_error = "Hugging Face model is currently loading (503 Service Unavailable). Please retry in a few moments."
            elif e.code == 429:
                self.last_error = "Hugging Face rate limit exceeded (429 Too Many Requests)."
            else:
                self.last_error = f"Hugging Face API HTTP error ({e.code}): {e.reason}."
            return []
        except urllib.error.URLError as e:
            self.last_error = f"Network connection to Hugging Face failed: {e.reason}."
            return []
        except Exception as e:
            self.last_error = f"Visual inference error: {str(e)}."
            return []
