"""Shared helper functions for eKYC verification."""
from __future__ import annotations

import io
import logging
import os
from typing import Dict, Tuple, Optional

from PIL import Image

logger = logging.getLogger(__name__)


def load_image(image_field) -> Image.Image:
    """Load a Django `ImageFieldFile` into a PIL image."""
    if not image_field:
        raise ValueError("No image provided")

    image_field.open()
    try:
        image = Image.open(image_field)
        image = image.convert("RGB")
        return image
    finally:
        image_field.close()


def save_temp_image(image: Image.Image) -> Tuple[str, str]:
    """Persist PIL image to a temporary file and return path and format."""
    buffer = io.BytesIO()
    image_format = image.format or "JPEG"
    image.save(buffer, format=image_format)
    temp_path = os.path.join("/tmp", f"ekyc_{os.getpid()}_{id(image)}.{image_format.lower()}")

    with open(temp_path, "wb") as temp_file:
        temp_file.write(buffer.getvalue())

    return temp_path, image_format


def normalize_text(value: str) -> str:
    """Standardize text extracted from OCR/QR pipelines."""
    if value is None:
        return ""
    return " ".join(value.split()).strip()


def merge_data(primary: Dict[str, str], secondary: Dict[str, str]) -> Dict[str, str]:
    """Merge extracted data dicts favouring primary values."""
    merged = dict(secondary)
    merged.update({k: v for k, v in primary.items() if v})
    return merged
