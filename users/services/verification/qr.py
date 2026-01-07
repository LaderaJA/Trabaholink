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

    # Try parsing as JSON first (PhilSys QR codes are JSON format)
    import json
    import base64
    
    try:
        json_data = json.loads(data)
        if isinstance(json_data, dict):
            # Check if this is a JWT/signed payload with 'subject' field
            if 'subject' in json_data:
                # PhilSys uses JWT - the 'subject' field contains the actual person data
                logger.info("Detected JWT format QR code with 'subject' field")
                subject_value = json_data['subject']
                
                # Subject might be: 1) JSON string, 2) base64 string, 3) nested dict, 4) plain string
                if isinstance(subject_value, dict):
                    # Already a dict, extract directly
                    logger.info("Subject is already a dict, extracting fields")
                    for key, value in subject_value.items():
                        normalized_key = normalize_text(str(key)).lower().replace(' ', '_').replace('-', '_')
                        normalized_value = normalize_text(str(value)) if value else ''
                        if normalized_key and normalized_value:
                            extracted[normalized_key] = normalized_value
                    logger.info(f"QR parsed JWT subject dict with {len(extracted)-1} fields: {list(extracted.keys())}")
                    return extracted
                    
                elif isinstance(subject_value, str):
                    # Try multiple decoding strategies
                    logger.info(f"Subject is string ({len(subject_value)} chars), attempting to decode")
                    
                    # Strategy 1: Try parsing as JSON directly
                    try:
                        subject_data = json.loads(subject_value)
                        if isinstance(subject_data, dict):
                            for key, value in subject_data.items():
                                normalized_key = normalize_text(str(key)).lower().replace(' ', '_').replace('-', '_')
                                normalized_value = normalize_text(str(value)) if value else ''
                                if normalized_key and normalized_value:
                                    extracted[normalized_key] = normalized_value
                            logger.info(f"QR parsed JWT subject (JSON) with {len(extracted)-1} fields: {list(extracted.keys())}")
                            return extracted
                    except (json.JSONDecodeError, ValueError) as e:
                        logger.debug(f"Subject is not JSON: {e}")
                    
                    # Strategy 2: Try base64 decode
                    try:
                        decoded = base64.b64decode(subject_value).decode('utf-8')
                        subject_data = json.loads(decoded)
                        if isinstance(subject_data, dict):
                            for key, value in subject_data.items():
                                normalized_key = normalize_text(str(key)).lower().replace(' ', '_').replace('-', '_')
                                normalized_value = normalize_text(str(value)) if value else ''
                                if normalized_key and normalized_value:
                                    extracted[normalized_key] = normalized_value
                            logger.info(f"QR parsed JWT subject (base64) with {len(extracted)-1} fields: {list(extracted.keys())}")
                            return extracted
                    except Exception as e:
                        logger.debug(f"Subject is not base64: {e}")
                    
                    # Strategy 3: URL-safe base64
                    try:
                        decoded = base64.urlsafe_b64decode(subject_value + '==').decode('utf-8')
                        subject_data = json.loads(decoded)
                        if isinstance(subject_data, dict):
                            for key, value in subject_data.items():
                                normalized_key = normalize_text(str(key)).lower().replace(' ', '_').replace('-', '_')
                                normalized_value = normalize_text(str(value)) if value else ''
                                if normalized_key and normalized_value:
                                    extracted[normalized_key] = normalized_value
                            logger.info(f"QR parsed JWT subject (urlsafe b64) with {len(extracted)-1} fields: {list(extracted.keys())}")
                            return extracted
                    except Exception as e:
                        logger.debug(f"Subject is not urlsafe base64: {e}")
                    
                    logger.warning(f"Failed to decode JWT subject string, treating as plain text: {subject_value[:100]}")
            
            # Not JWT or JWT parsing failed, extract top-level fields
            for key, value in json_data.items():
                # Skip signature/crypto fields
                if key.lower() in ['signature', 'alg', 'issuer']:
                    continue
                normalized_key = normalize_text(str(key)).lower().replace(' ', '_').replace('-', '_')
                normalized_value = normalize_text(str(value)) if value else ''
                if normalized_key and normalized_value:
                    extracted[normalized_key] = normalized_value
            logger.info(f"QR parsed as JSON with {len(extracted)-1} fields: {list(extracted.keys())}")
            return extracted
    except (json.JSONDecodeError, ValueError) as e:
        logger.debug(f"QR is not JSON format: {e}, trying key-value parsing")

    # Fallback: Heuristic key extraction for key-value format
    for token in data.split('\n'):
        token = normalize_text(token)
        if not token or ':' not in token:
            continue
        key, value = token.split(':', 1)
        key = normalize_text(key).lower().replace(' ', '_')
        value = normalize_text(value)
        if key and value:
            extracted[key] = value

    logger.info(f"QR extracted data ({len(extracted)-1} fields): {list(extracted.keys())}")
    return extracted
