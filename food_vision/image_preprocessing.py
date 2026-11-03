"""
GlucoShield Food Vision Image Preprocessing
===========================================
Safe decoding, EXIF orientation normalization, proportional resizing, and optimized JPEG encoding
for external vision inference providers (e.g. Hugging Face Inference API).
Guards against decompression bombs, malformed image files, and HTTP 413 Payload Too Large errors.
"""

import io
from typing import Tuple, Dict, Any, Optional
from PIL import Image, ImageOps

MAX_ALLOWED_PIXELS = 25_000_000  # 25 Megapixels (standard safety limit for decoded raster)
DEFAULT_MAX_EDGE = 1024          # Longest edge maximum dimension in pixels
DEFAULT_JPEG_QUALITY = 85        # High-fidelity JPEG compression
MAX_PAYLOAD_BYTES = 2 * 1024 * 1024  # 2 MB safe ceiling for provider inference request

SUPPORTED_FORMATS = {"JPEG", "JPG", "PNG", "WEBP", "BMP", "TIFF", "GIF"}


class ImagePreprocessingError(Exception):
    """Raised when an uploaded meal image fails validation or preprocessing."""
    pass


def preprocess_meal_image(
    image_bytes: bytes,
    max_edge: int = DEFAULT_MAX_EDGE,
    quality: int = DEFAULT_JPEG_QUALITY,
    max_payload_bytes: int = MAX_PAYLOAD_BYTES
) -> Tuple[bytes, Dict[str, Any]]:
    """
    Safely validates, normalizes, resizes, and encodes a meal image for external inference.
    
    Processing steps:
      1. Validates non-empty input bytes.
      2. Validates image format and structure via PIL with decompression bomb guard.
      3. Normalizes orientation using EXIF transpose metadata.
      4. Converts color space to RGB (compositing RGBA/transparency over white background).
      5. Proportionally resizes so longest edge is at most `max_edge` pixels.
      6. Encodes as optimized JPEG with `quality`.
      7. If output exceeds `max_payload_bytes`, adaptively steps down scale and quality.
      8. Returns final optimized JPEG bytes and metadata.
    
    Returns:
        Tuple of (optimized_jpeg_bytes, metadata_dict)
    
    Raises:
        ImagePreprocessingError: If image is invalid, corrupt, unsupported, or exceeds safe limits.
    """
    if not image_bytes or not isinstance(image_bytes, bytes):
        raise ImagePreprocessingError("Image input bytes are empty or invalid.")

    # Guard against decompression bombs
    Image.MAX_IMAGE_PIXELS = MAX_ALLOWED_PIXELS

    try:
        raw_stream = io.BytesIO(image_bytes)
        img = Image.open(raw_stream)
        img.load()  # Verify image data can be fully loaded without syntax or truncation errors
    except Image.DecompressionBombError:
        raise ImagePreprocessingError("Image resolution exceeds safety limits (decompression bomb guard).")
    except Exception as e:
        raise ImagePreprocessingError(
            f"Invalid or corrupted image format. Please upload a valid JPEG, PNG, or WebP photograph."
        )

    raw_format = (img.format or "").upper()
    if raw_format not in SUPPORTED_FORMATS:
        raise ImagePreprocessingError(
            f"Unsupported image format '{raw_format}'. Supported formats: JPEG, PNG, WebP."
        )

    orig_width, orig_height = img.size
    if orig_width <= 0 or orig_height <= 0:
        raise ImagePreprocessingError("Invalid image dimensions (zero or negative width/height).")

    if orig_width * orig_height > MAX_ALLOWED_PIXELS:
        raise ImagePreprocessingError(
            f"Image resolution ({orig_width}x{orig_height}) exceeds maximum allowed 25 megapixels."
        )

    # 1. Orientation correction via EXIF
    orientation_corrected = False
    try:
        transposed = ImageOps.exif_transpose(img)
        if transposed is not None and transposed.size != img.size:
            orientation_corrected = True
        img = transposed or img
    except Exception:
        # Continue with untransposed image if EXIF tag parsing encounters anomalies
        pass

    # 2. Preserve RGB colour (handle transparency on white background)
    if img.mode != "RGB":
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            rgba = img.convert("RGBA")
            bg = Image.new("RGB", rgba.size, (255, 255, 255))
            bg.paste(rgba, mask=rgba.split()[3])
            img = bg
        else:
            img = img.convert("RGB")

    # 3. Proportional resizing: longest edge at most max_edge
    curr_width, curr_height = img.size
    longest_edge = max(curr_width, curr_height)
    resized = False
    if longest_edge > max_edge:
        scale = float(max_edge) / float(longest_edge)
        new_width = max(1, int(round(curr_width * scale)))
        new_height = max(1, int(round(curr_height * scale)))
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        resized = True

    # 4. Optimized JPEG encoding
    current_quality = quality
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=current_quality, optimize=True)
    encoded_bytes = buffer.getvalue()

    # 5. Adaptive step-down if payload still exceeds limit
    step_downs = [
        (75, 1.0),
        (70, 0.75),
        (65, 0.5)
    ]
    step_idx = 0
    while len(encoded_bytes) > max_payload_bytes and step_idx < len(step_downs):
        next_q, scale_factor = step_downs[step_idx]
        step_idx += 1
        current_quality = next_q
        if scale_factor < 1.0:
            w, h = img.size
            nw = max(1, int(round(w * scale_factor)))
            nh = max(1, int(round(h * scale_factor)))
            img = img.resize((nw, nh), Image.Resampling.LANCZOS)
            resized = True
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=current_quality, optimize=True)
        encoded_bytes = buffer.getvalue()

    if len(encoded_bytes) > max_payload_bytes:
        raise ImagePreprocessingError(
            f"Image payload too large after compression ({len(encoded_bytes)} bytes exceeds {max_payload_bytes} limit). "
            "Please upload a smaller photo."
        )

    meta = {
        "original_format": raw_format,
        "original_dimensions": (orig_width, orig_height),
        "original_bytes": len(image_bytes),
        "processed_format": "JPEG",
        "processed_dimensions": img.size,
        "processed_bytes": len(encoded_bytes),
        "orientation_corrected": orientation_corrected,
        "resized": resized,
        "quality_used": current_quality
    }

    return encoded_bytes, meta
