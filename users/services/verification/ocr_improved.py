"""
Improved OCR with better preprocessing and regex patterns.
Addresses common issues with Tesseract extraction and parsing.
"""
from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Tuple
import numpy as np

from .utils import normalize_text

try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps
except ImportError:
    Image = None

logger = logging.getLogger(__name__)


class ImprovedOCR:
    """
    Improved OCR with enhanced preprocessing and better regex patterns.
    
    Key improvements:
    1. Multiple preprocessing strategies
    2. Flexible regex patterns with fuzzy matching
    3. Post-processing to clean OCR errors
    4. Multiple extraction attempts with different configs
    """
    
    def __init__(self):
        """Initialize improved patterns with common OCR error handling."""
        
        # Name patterns - handles OCR errors like 0->O, 1->I, etc.
        self._name_patterns = [
            # Standard format with label
            re.compile(r"(?:full\s*)?(?:name|nombre|pangalan)[:\-\s]*(?P<value>[A-Z][A-Za-z\s,.']+(?:[A-Z][A-Za-z\s,.']){2,})", re.IGNORECASE),
            # LASTNAME, FIRSTNAME format
            re.compile(r"(?P<value>[A-Z]{2,}(?:\s+[A-Z]{2,})*,\s*[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)", re.IGNORECASE),
            # Without label - 3+ capitalized words
            re.compile(r"(?P<value>[A-Z][a-z]+(?:\s+[A-Z][a-z]+){2,})", re.IGNORECASE),
        ]
        
        # Date patterns - multiple formats
        self._date_patterns = [
            # With label
            re.compile(r"(?:date\s*of\s*birth|birthday|birth\s*date|dob|bday)[:\-\s]*(?P<value>[0-9]{1,2}[\s\-/\.][A-Za-z]{3,}[\s\-/\.][0-9]{4})", re.IGNORECASE),
            re.compile(r"(?:date\s*of\s*birth|birthday|birth\s*date|dob|bday)[:\-\s]*(?P<value>[0-9]{1,2}[\s\-/\.][0-9]{1,2}[\s\-/\.][0-9]{2,4})", re.IGNORECASE),
            # Without label - standalone dates
            re.compile(r"(?P<value>[0-9]{1,2}[\s\-/\.][A-Za-z]{3,}[\s\-/\.][0-9]{4})", re.IGNORECASE),
            re.compile(r"(?P<value>[0-9]{1,2}[\s\-/\.][0-9]{1,2}[\s\-/\.][0-9]{4})", re.IGNORECASE),
            re.compile(r"(?P<value>[0-9]{4}[\s\-/\.][0-9]{1,2}[\s\-/\.][0-9]{1,2})", re.IGNORECASE),
        ]
        
        # ID Number patterns - PhilSys, SSS, TIN, etc.
        self._id_patterns = [
            # PhilSys PCN: 0000-0000-0000-0000
            re.compile(r"(?:pcn|card\s*no|philsys)[:\-\s]*(?P<value>[0-9]{4}[\s\-]?[0-9]{4}[\s\-]?[0-9]{4}[\s\-]?[0-9]{4})", re.IGNORECASE),
            # Standalone 16-digit number
            re.compile(r"(?P<value>[0-9]{4}[\s\-][0-9]{4}[\s\-][0-9]{4}[\s\-][0-9]{4})"),
            # SSS/TIN format: 00-0000000-0
            re.compile(r"(?:sss|tin|gsis)[:\-\s]*(?P<value>[0-9]{2}[\s\-][0-9]{7}[\s\-][0-9])", re.IGNORECASE),
            # Driver's License: A00-00-000000
            re.compile(r"(?:license|lic)[:\-\s]*(?P<value>[A-Z][0-9]{2}[\s\-][0-9]{2}[\s\-][0-9]{6})", re.IGNORECASE),
            # Generic ID number
            re.compile(r"(?:id|control|number|no)[:\-\s]*(?P<value>[A-Z0-9\-]{8,})", re.IGNORECASE),
        ]
        
        # Address patterns
        self._address_patterns = [
            re.compile(r"(?:address|residence|tirahan)[:\-\s]*(?P<value>[A-Z0-9][^\n]{15,})", re.IGNORECASE),
            re.compile(r"(?P<value>(?:brgy|barangay|blk|block|lot|street|st\.)[^\n]{10,})", re.IGNORECASE),
        ]
        
        # Sex/Gender patterns
        self._sex_patterns = [
            re.compile(r"(?:sex|gender|kasarian)[:\-\s]*(?P<value>m|f|male|female|lalaki|babae)", re.IGNORECASE),
            re.compile(r"\b(?P<value>male|female)\b", re.IGNORECASE),
        ]
        
        # Nationality patterns
        self._nationality_patterns = [
            re.compile(r"(?:nationality|citizen|citizenship)[:\-\s]*(?P<value>filipino|philippine|pilipino)", re.IGNORECASE),
            re.compile(r"\b(?P<value>filipino|philippine)\b", re.IGNORECASE),
        ]
    
    def preprocess_image_advanced(self, image) -> List:
        """
        Apply multiple preprocessing strategies to handle various ID conditions.
        
        Returns list of preprocessed images to try OCR on.
        """
        if cv2 is None or Image is None:
            return [image]
        
        preprocessed_images = []
        
        try:
            # Convert to numpy array
            if hasattr(image, 'mode'):
                img_array = np.array(image)
            else:
                img_array = image
            
            # Convert to grayscale
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # Strategy 1: High contrast with denoising
            denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            enhanced = clahe.apply(denoised)
            _, binary1 = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            preprocessed_images.append(binary1)
            
            # Strategy 2: Adaptive thresholding
            adaptive = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            preprocessed_images.append(adaptive)
            
            # Strategy 3: Morphological operations to clean up
            kernel = np.ones((2,2), np.uint8)
            morph = cv2.morphologyEx(binary1, cv2.MORPH_CLOSE, kernel)
            preprocessed_images.append(morph)
            
            # Strategy 4: Upscale for better OCR
            height, width = gray.shape
            if width < 2000:
                scale = 2000 / width
                new_size = (int(width * scale), int(height * scale))
                upscaled = cv2.resize(gray, new_size, interpolation=cv2.INTER_CUBIC)
                _, binary_upscaled = cv2.threshold(upscaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                preprocessed_images.append(binary_upscaled)
            
            # Strategy 5: Sharpen image
            pil_img = Image.fromarray(gray)
            sharpened = pil_img.filter(ImageFilter.SHARPEN)
            preprocessed_images.append(np.array(sharpened))
            
            logger.info(f"Generated {len(preprocessed_images)} preprocessed versions")
            
        except Exception as e:
            logger.warning(f"Preprocessing failed: {e}, using original image")
            preprocessed_images = [image]
        
        return preprocessed_images
    
    def extract_with_multiple_configs(self, image) -> str:
        """
        Extract text using multiple Tesseract configurations.
        
        Returns combined text from all successful extractions.
        """
        if pytesseract is None:
            raise ImportError("pytesseract is required")
        
        all_texts = []
        
        # Config 1: Default (PSM 6 - Uniform block of text)
        try:
            text1 = pytesseract.image_to_string(image, config='--psm 6')
            if text1.strip():
                all_texts.append(text1)
        except Exception as e:
            logger.warning(f"PSM 6 failed: {e}")
        
        # Config 2: PSM 3 - Fully automatic page segmentation
        try:
            text2 = pytesseract.image_to_string(image, config='--psm 3')
            if text2.strip():
                all_texts.append(text2)
        except Exception as e:
            logger.warning(f"PSM 3 failed: {e}")
        
        # Config 3: PSM 11 - Sparse text
        try:
            text3 = pytesseract.image_to_string(image, config='--psm 11')
            if text3.strip():
                all_texts.append(text3)
        except Exception as e:
            logger.warning(f"PSM 11 failed: {e}")
        
        # Config 4: With character whitelist for IDs
        try:
            config = '--psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789,.-/# '
            text4 = pytesseract.image_to_string(image, config=config)
            if text4.strip():
                all_texts.append(text4)
        except Exception as e:
            logger.warning(f"Whitelist config failed: {e}")
        
        # Combine all texts
        combined = "\n".join(all_texts)
        return combined
    
    def clean_ocr_errors(self, text: str) -> str:
        """
        Fix common OCR errors.
        
        Common mistakes:
        - 0 (zero) -> O (letter O)
        - 1 (one) -> I or l
        - 5 -> S
        - 8 -> B
        """
        # This is context-dependent, so we'll be conservative
        cleaned = text
        
        # Fix common spacing issues
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Fix common punctuation issues
        cleaned = cleaned.replace('|', 'I')
        cleaned = cleaned.replace('!', 'I')
        
        return cleaned
    
    def extract_field_with_patterns(self, text: str, patterns: List[re.Pattern], field_name: str) -> Optional[str]:
        """
        Try multiple patterns to extract a field.
        
        Returns the first successful match.
        """
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                for group_name in match.groupdict():
                    value = match.group(group_name)
                    if value:
                        cleaned = normalize_text(value)
                        if cleaned and len(cleaned) > 2:  # Minimum length check
                            logger.debug(f"Extracted {field_name}: {cleaned}")
                            return cleaned
        return None
    
    def extract_id_data(self, image, id_type: str = None) -> Dict[str, str]:
        """
        Extract ID data using improved preprocessing and multiple extraction attempts.
        
        Returns:
            Dict with extracted fields and metadata
        """
        if pytesseract is None:
            raise ImportError("pytesseract is required for OCR")
        
        # Step 1: Preprocess image with multiple strategies
        preprocessed_images = self.preprocess_image_advanced(image)
        
        # Step 2: Extract text from all preprocessed versions
        all_raw_texts = []
        for idx, prep_img in enumerate(preprocessed_images):
            try:
                text = self.extract_with_multiple_configs(prep_img)
                if text.strip():
                    all_raw_texts.append(text)
                    logger.debug(f"Preprocessed version {idx} extracted {len(text)} chars")
            except Exception as e:
                logger.warning(f"Extraction failed for version {idx}: {e}")
        
        if not all_raw_texts:
            logger.error("No text extracted from any preprocessing strategy")
            return {
                "raw_text": "",
                "id_type": id_type or "",
                "extraction_quality": "failed"
            }
        
        # Step 3: Combine all extracted texts
        combined_text = "\n".join(all_raw_texts)
        cleaned_text = self.clean_ocr_errors(combined_text)
        
        # Step 4: Extract fields using patterns
        extracted = {
            "raw_text": combined_text,
            "id_type": id_type or "",
        }
        
        # Extract each field
        full_name = self.extract_field_with_patterns(cleaned_text, self._name_patterns, "full_name")
        if full_name:
            extracted["full_name"] = full_name
        
        date_of_birth = self.extract_field_with_patterns(cleaned_text, self._date_patterns, "date_of_birth")
        if date_of_birth:
            extracted["date_of_birth"] = date_of_birth
        
        id_number = self.extract_field_with_patterns(cleaned_text, self._id_patterns, "id_number")
        if id_number:
            extracted["id_number"] = id_number
        
        address = self.extract_field_with_patterns(cleaned_text, self._address_patterns, "address")
        if address:
            extracted["address"] = address
        
        sex = self.extract_field_with_patterns(cleaned_text, self._sex_patterns, "sex")
        if sex:
            extracted["sex"] = sex
        
        nationality = self.extract_field_with_patterns(cleaned_text, self._nationality_patterns, "nationality")
        if nationality:
            extracted["nationality"] = nationality
        
        # Calculate extraction quality
        fields_extracted = len([k for k in extracted.keys() if k not in ['raw_text', 'id_type', 'extraction_quality']])
        if fields_extracted >= 4:
            extracted["extraction_quality"] = "good"
        elif fields_extracted >= 2:
            extracted["extraction_quality"] = "fair"
        else:
            extracted["extraction_quality"] = "poor"
        
        logger.info(f"Extracted {fields_extracted} fields with quality: {extracted['extraction_quality']}")
        
        return extracted


# Singleton instance
_improved_ocr = None

def get_improved_ocr() -> ImprovedOCR:
    """Get singleton instance of ImprovedOCR."""
    global _improved_ocr
    if _improved_ocr is None:
        _improved_ocr = ImprovedOCR()
    return _improved_ocr


def extract_id_text_improved(image, id_type: str = None) -> Dict[str, str]:
    """
    Extract ID text using improved OCR with better preprocessing and regex.
    
    This is a drop-in replacement for the standard extract_id_text function.
    """
    ocr = get_improved_ocr()
    return ocr.extract_id_data(image, id_type)
