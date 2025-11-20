"""OCR utilities leveraging Tesseract for ID parsing."""
from __future__ import annotations

import logging
import re
from typing import Dict

from .utils import normalize_text

try:
    import pytesseract
except ImportError:  # pragma: no cover - optional dependency
    pytesseract = None

logger = logging.getLogger(__name__)

# Enhanced regex patterns for Philippine IDs
# Name patterns - supports various formats
_NAME_PATTERN = re.compile(
    r"(full\s*)?name[:\-]?\s*(?P<value>[A-Z][A-Z ,.'-]+)|" 
    r"(?P<value2>[A-Z][A-Z]+,\s*[A-Z][A-Z ]+(?:\s+[A-Z]\.?)?)",  # LASTNAME, FIRSTNAME format
    re.IGNORECASE
)

# Birthday patterns - supports multiple date formats
_BIRTHDAY_PATTERN = re.compile(
    r"(birth|bday|birthday|dob|date\s*of\s*birth)[:\-]?\s*(?P<value>[0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})|"  # MM/DD/YYYY
    r"(?P<value2>[0-9]{4}[\/\-][0-9]{1,2}[\/\-][0-9]{1,2})|"  # YYYY/MM/DD
    r"(?P<value3>(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+[0-9]{1,2},?\s+[0-9]{4})",  # Month DD, YYYY
    re.IGNORECASE
)

# ID Number patterns - supports various Philippine ID formats
_ID_NUMBER_PATTERN = re.compile(
    r"(id|control|philid|philsys|license|passport|umid|sss|tin)\s*(no\.?|number|#)?[:\-]?\s*(?P<value>[A-Z0-9\-]+)|"  # Standard format
    r"(?P<value2>[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4})|"  # PhilSys format: 0000-0000-0000-0000
    r"(?P<value3>[A-Z][0-9]{2}[-\s]?[0-9]{8})",  # Driver's license format
    re.IGNORECASE
)

# Address patterns
_ADDRESS_PATTERN = re.compile(
    r"address[:\-]?\s*(?P<value>[A-Z0-9][^\n]+)|"  # Standard address
    r"(?P<value2>\d+\s+[A-Z][A-Za-z\s,]+(?:city|municipality|province))",  # Philippine address format
    re.IGNORECASE
)

# Additional patterns for Philippine IDs
_SEX_PATTERN = re.compile(r"(sex|gender)[:\-]?\s*(?P<value>m|f|male|female)", re.IGNORECASE)
_NATIONALITY_PATTERN = re.compile(r"nationality[:\-]?\s*(?P<value>[A-Z]+)", re.IGNORECASE)


def extract_id_text(image, id_type: str | None = None) -> Dict[str, str]:
    """Extract key/value pairs from an ID image using OCR.

    Returns a dictionary including the raw OCR text and simple heuristic matches
    for key identity fields. When pytesseract is not available the caller should
    fall back to manual review.
    """

    if pytesseract is None:
        raise ImportError("pytesseract is required for OCR extraction")

    config = "--psm 6"
    raw_text = pytesseract.image_to_string(image, config=config)
    normalized_lines = [normalize_text(line) for line in raw_text.splitlines() if normalize_text(line)]
    normalized_text = "\n".join(normalized_lines)

    extracted: Dict[str, str] = {
        "raw_text": raw_text,
        "id_type": id_type or "",
    }

    extracted.update(_match_pattern(normalized_text, _NAME_PATTERN, "full_name"))
    extracted.update(_match_pattern(normalized_text, _BIRTHDAY_PATTERN, "date_of_birth"))
    extracted.update(_match_pattern(normalized_text, _ID_NUMBER_PATTERN, "id_number"))
    extracted.update(_match_pattern(normalized_text, _ADDRESS_PATTERN, "address"))
    extracted.update(_match_pattern(normalized_text, _SEX_PATTERN, "sex"))
    extracted.update(_match_pattern(normalized_text, _NATIONALITY_PATTERN, "nationality"))

    logger.debug("OCR extracted data: %s", extracted)
    return extracted


def _match_pattern(text: str, pattern: re.Pattern[str], key: str) -> Dict[str, str]:
    """Match pattern and extract value from named groups."""
    match = pattern.search(text)
    if not match:
        return {}
    
    # Try to get value from any named group (value, value2, value3, etc.)
    for group_name in match.groupdict():
        if match.group(group_name):
            value = normalize_text(match.group(group_name))
            if value:  # Only return if value is not empty
                return {key: value}
    
    return {}
