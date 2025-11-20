"""QR code decoding utilities for Philippine IDs."""
from __future__ import annotations

import logging
from typing import Dict

from .utils import normalize_text

try:
    from pyzbar.pyzbar import decode
except ImportError:  # pragma: no cover - optional dependency
    decode = None

logger = logging.getLogger(__name__)


def extract_qr_data(image) -> Dict[str, str]:
    """Decode QR content from the supplied image (if any)."""
    if decode is None:
        raise ImportError("pyzbar is required for QR extraction")

    decoded_objects = decode(image)
    if not decoded_objects:
        return {}

    # Assume the first decoded object contains relevant data
    result = decoded_objects[0]
    data = result.data.decode("utf-8", errors="ignore")

    # A QR payload may contain JSON or key-value pairs.
    # Attempt basic parsing while leaving detailed parsing to higher layers.
    extracted: Dict[str, str] = {
        "qr_raw": data,
    }

    # Heuristic key extraction
    for token in data.split('\n'):
        token = normalize_text(token)
        if not token or ':' not in token:
            continue
        key, value = token.split(':', 1)
        key = normalize_text(key).lower().replace(' ', '_')
        value = normalize_text(value)
        extracted[key] = value

    logger.debug("QR extracted data: %s", extracted)
    return extracted
