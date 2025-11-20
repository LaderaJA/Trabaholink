"""Enhanced OCR specifically optimized for Philippine PhilSys National ID cards."""
from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional
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
    from PIL import Image, ImageEnhance, ImageFilter
except ImportError:
    Image = None

logger = logging.getLogger(__name__)


class PhilSysOCR:
    """Optimized OCR for PhilSys National ID cards."""
    
    def __init__(self):
        """Initialize PhilSys-specific patterns."""
        # PhilSys IDs have specific layout - name is usually in format: LASTNAME, FIRSTNAME MIDDLENAME
        self._name_pattern = re.compile(
            r"(?P<value>[A-Z]{2,}(?:\s+[A-Z]{2,})*,\s*[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)|"  # LASTNAME, FIRSTNAME format
            r"(?:name|nombre)[:\s]*(?P<value2>[A-Z][A-Z\s,.']+)",  # With label
            re.IGNORECASE
        )
        
        # PhilSys date format is usually: DD MMM YYYY or MM/DD/YYYY
        self._date_pattern = re.compile(
            r"(?:date\s+of\s+birth|birthday|birth\s+date)[:\s]*(?P<value>[0-9]{1,2}[\s\-/][A-Za-z]{3,}[\s\-/][0-9]{4})|"
            r"(?P<value2>[0-9]{1,2}[\s\-/][0-9]{1,2}[\s\-/][0-9]{4})|"
            r"(?P<value3>[0-9]{4}[\s\-/][0-9]{1,2}[\s\-/][0-9]{1,2})",
            re.IGNORECASE
        )
        
        # PhilSys Card Number (PCN): 0000-0000-0000-0000
        self._pcn_pattern = re.compile(
            r"(?:pcn|card\s+no|philsys\s+no)[:\s]*(?P<value>[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4})|"
            r"(?P<value2>[0-9]{4}[-\s][0-9]{4}[-\s][0-9]{4}[-\s][0-9]{4})",
            re.IGNORECASE
        )
        
        # Sex: M or F
        self._sex_pattern = re.compile(
            r"(?:sex|gender)[:\s]*(?P<value>m|f|male|female)",
            re.IGNORECASE
        )
        
        # Address - PhilSys shows full address
        self._address_pattern = re.compile(
            r"(?:address|residence)[:\s]*(?P<value>[A-Z0-9][^\n]{10,})|"
            r"(?P<value2>(?:brgy|barangay)[^\n]+)",
            re.IGNORECASE
        )
    
    def preprocess_philsys_image(self, image) -> List:
        """Apply aggressive preprocessing specifically optimized for PhilSys IDs."""
        if cv2 is None or Image is None:
            return [image]
        
        preprocessed = []
        
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
            
            # STEP 1: Resize if too small (OCR works better with larger images)
            height, width = gray.shape
            if width < 1500:
                scale = 1500 / width
                new_width = int(width * scale)
                new_height = int(height * scale)
                gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
                logger.debug(f"Upscaled image from {width}x{height} to {new_width}x{new_height}")
            
            # STEP 2: Deskew (fix rotation)
            try:
                coords = np.column_stack(np.where(gray > 0))
                if len(coords) > 0:
                    angle = cv2.minAreaRect(coords)[-1]
                    if angle < -45:
                        angle = -(90 + angle)
                    else:
                        angle = -angle
                    
                    if abs(angle) > 0.5:  # Only rotate if angle is significant
                        (h, w) = gray.shape
                        center = (w // 2, h // 2)
                        M = cv2.getRotationMatrix2D(center, angle, 1.0)
                        gray = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                        logger.debug(f"Deskewed image by {angle:.2f} degrees")
            except Exception as e:
                logger.warning(f"Deskew failed: {e}")
            
            # STEP 3: Aggressive denoising
            denoised = cv2.fastNlMeansDenoising(gray, None, h=20, templateWindowSize=7, searchWindowSize=21)
            
            # STEP 4: Best thresholding techniques (reduced from 10 to 4 for speed)
            
            # 4a. Otsu's thresholding (BEST for most cases)
            _, otsu = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            preprocessed.append(Image.fromarray(otsu))
            
            # 4b. CLAHE + Otsu (BEST for low contrast)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(denoised)
            _, clahe_thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            preprocessed.append(Image.fromarray(clahe_thresh))
            
            # 4c. Adaptive Gaussian (BEST for uneven lighting)
            adaptive = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 11
            )
            preprocessed.append(Image.fromarray(adaptive))
            
            # 4d. Morphological cleaned version (BEST for noisy images)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            morph_clean = cv2.morphologyEx(otsu, cv2.MORPH_CLOSE, kernel, iterations=1)
            preprocessed.append(Image.fromarray(morph_clean))
            
            logger.debug(f"Generated {len(preprocessed)} preprocessed versions for PhilSys")
            
        except Exception as e:
            logger.warning(f"PhilSys preprocessing failed: {e}")
            # Fallback to original
            preprocessed.append(image)
        
        return preprocessed
    
    def extract_with_multiple_psm(self, image) -> str:
        """Try multiple Tesseract PSM modes with optimized configuration."""
        if pytesseract is None:
            return ""
        
        all_texts = []
        
        # PSM modes that work well for ID cards:
        # 6: Uniform block of text (default) - BEST for IDs
        # 3: Fully automatic page segmentation
        # 11: Sparse text - good for scattered text
        # Reduced from 7 to 3 modes for faster processing
        psm_modes = [6, 3, 11]
        
        for psm in psm_modes:
            try:
                # Optimized Tesseract configuration for Philippine IDs
                # --oem 1: LSTM + Legacy (better for mixed quality)
                # --dpi 300: Assume 300 DPI for better accuracy
                # Only allow alphanumeric, spaces, and common punctuation
                config = (
                    f"--psm {psm} --oem 1 --dpi 300 "
                    f"-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ,./-# "
                    f"-c preserve_interword_spaces=1 "
                    f"-c tessedit_pageseg_mode={psm}"
                )
                
                text = pytesseract.image_to_string(image, config=config, lang='eng')
                if text.strip() and len(text.strip()) > 10:  # Only keep if meaningful
                    all_texts.append(text)
                    logger.debug(f"PSM {psm} extracted {len(text)} characters")
            except Exception as e:
                logger.warning(f"PSM {psm} failed: {e}")
        
        # Combine all texts
        combined = "\n".join(all_texts)
        return combined
    
    def extract_philsys_data(self, image) -> Dict[str, str]:
        """
        Extract data from PhilSys National ID with optimized preprocessing.
        
        Args:
            image: PIL Image or numpy array of PhilSys ID
        
        Returns:
            Dictionary with extracted fields and metadata
        """
        # Preprocess image
        preprocessed_images = self.preprocess_philsys_image(image)
        
        # Extract text from all preprocessed versions
        all_raw_texts = []
        for idx, img in enumerate(preprocessed_images):
            text = self.extract_with_multiple_psm(img)
            if text:
                all_raw_texts.append(text)
                logger.debug(f"Preprocessed version {idx} extracted {len(text)} chars")
        
        if not all_raw_texts:
            logger.warning("No text extracted from PhilSys ID")
            return {"raw_text": "", "id_type": "philsys", "extraction_quality": "poor"}
        
        # Combine all extracted texts
        combined_text = "\n".join(all_raw_texts)
        
        # Normalize
        normalized_lines = [normalize_text(line) for line in combined_text.splitlines() if normalize_text(line)]
        normalized_text = "\n".join(normalized_lines)
        
        # Extract structured data
        extracted: Dict[str, str] = {
            "raw_text": combined_text[:1000],  # Limit raw text size
            "id_type": "PhilSys National ID",
        }
        
        # Extract fields using PhilSys-specific patterns with field labels
        name_data = self._match_pattern(normalized_text, self._name_pattern, "full_name")
        if name_data:
            extracted.update(name_data)
            extracted["name_source"] = "OCR Pattern Matching"
        
        dob_data = self._match_pattern(normalized_text, self._date_pattern, "date_of_birth")
        if dob_data:
            extracted.update(dob_data)
            extracted["dob_source"] = "OCR Pattern Matching"
        
        pcn_data = self._match_pattern(normalized_text, self._pcn_pattern, "id_number")
        if pcn_data:
            extracted.update(pcn_data)
            extracted["pcn_source"] = "OCR Pattern Matching"
            # Also store as 'pcn' for consistency
            extracted["pcn"] = extracted["id_number"]
        
        sex_data = self._match_pattern(normalized_text, self._sex_pattern, "sex")
        if sex_data:
            extracted.update(sex_data)
            extracted["sex_source"] = "OCR Pattern Matching"
        
        address_data = self._match_pattern(normalized_text, self._address_pattern, "address")
        if address_data:
            extracted.update(address_data)
            extracted["address_source"] = "OCR Pattern Matching"
        
        # Try to extract name from lines if pattern didn't work
        if "full_name" not in extracted:
            name_from_lines = self._extract_name_from_lines(normalized_lines)
            if name_from_lines:
                extracted.update(name_from_lines)
                extracted["name_source"] = "Line-by-line Analysis"
        
        # Try to extract date from lines if pattern didn't work
        if "date_of_birth" not in extracted:
            dob_from_lines = self._extract_date_from_lines(normalized_lines)
            if dob_from_lines:
                extracted.update(dob_from_lines)
                extracted["dob_source"] = "Line-by-line Analysis"
        
        # Calculate extraction quality
        quality = self._calculate_quality(extracted)
        extracted["extraction_quality"] = quality
        
        # Add field count for admin display
        field_count = sum(1 for k in ["full_name", "date_of_birth", "id_number", "address", "sex"] if k in extracted)
        extracted["fields_extracted_count"] = str(field_count)
        
        logger.info(f"PhilSys OCR extracted {field_count} fields: {list(extracted.keys())}")
        return extracted
    
    def _match_pattern(self, text: str, pattern: re.Pattern[str], key: str) -> Dict[str, str]:
        """Match pattern and extract value from named groups."""
        match = pattern.search(text)
        if not match:
            return {}
        
        for group_name in match.groupdict():
            if match.group(group_name):
                value = normalize_text(match.group(group_name))
                if value:
                    return {key: value}
        
        return {}
    
    def _extract_name_from_lines(self, lines: List[str]) -> Dict[str, str]:
        """
        Extract name from lines by looking for LASTNAME, FIRSTNAME pattern.
        PhilSys IDs typically have name in this format near the top.
        """
        for line in lines[:10]:  # Check first 10 lines
            # Look for pattern: LASTNAME, FIRSTNAME MIDDLENAME
            if ',' in line and len(line) > 5:
                parts = line.split(',')
                if len(parts) == 2:
                    lastname = parts[0].strip()
                    firstname = parts[1].strip()
                    # Check if it looks like a name (mostly letters)
                    if (lastname.replace(' ', '').isalpha() and 
                        firstname.replace(' ', '').isalpha() and
                        len(lastname) > 1 and len(firstname) > 1):
                        return {"full_name": line.strip()}
        
        return {}
    
    def _extract_date_from_lines(self, lines: List[str]) -> Dict[str, str]:
        """Extract date of birth from lines."""
        date_keywords = ['birth', 'birthday', 'date of birth', 'dob']
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            # Check if line contains date keyword
            if any(keyword in line_lower for keyword in date_keywords):
                # Check this line and next line for date
                for check_line in lines[i:i+2]:
                    # Look for date patterns
                    date_match = re.search(
                        r'([0-9]{1,2}[\s\-/][A-Za-z]{3,}[\s\-/][0-9]{4})|'
                        r'([0-9]{1,2}[\s\-/][0-9]{1,2}[\s\-/][0-9]{4})|'
                        r'([0-9]{4}[\s\-/][0-9]{1,2}[\s\-/][0-9]{1,2})',
                        check_line
                    )
                    if date_match:
                        date_str = date_match.group(0)
                        return {"date_of_birth": normalize_text(date_str)}
        
        return {}
    
    def _calculate_quality(self, extracted: Dict[str, str]) -> str:
        """Calculate extraction quality based on fields found."""
        required_fields = ["full_name", "date_of_birth", "id_number"]
        optional_fields = ["address", "sex"]
        
        required_count = sum(1 for field in required_fields if field in extracted and extracted[field])
        optional_count = sum(1 for field in optional_fields if field in extracted and extracted[field])
        
        total_score = (required_count / len(required_fields)) * 0.7 + (optional_count / len(optional_fields)) * 0.3
        
        if total_score >= 0.8:
            return "excellent"
        elif total_score >= 0.6:
            return "good"
        elif total_score >= 0.4:
            return "fair"
        else:
            return "poor"


# Global instance
_philsys_ocr: Optional[PhilSysOCR] = None


def get_philsys_ocr() -> PhilSysOCR:
    """Get or create global PhilSysOCR instance."""
    global _philsys_ocr
    if _philsys_ocr is None:
        _philsys_ocr = PhilSysOCR()
    return _philsys_ocr


def extract_philsys_text(image) -> Dict[str, str]:
    """
    Extract text from PhilSys National ID using optimized OCR.
    
    This is a drop-in replacement for extract_id_text() specifically for PhilSys IDs.
    """
    ocr = get_philsys_ocr()
    return ocr.extract_philsys_data(image)
