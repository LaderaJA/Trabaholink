"""Enhanced OCR with multiple engines and preprocessing for better accuracy."""
from __future__ import annotations

import logging
import re
from typing import Dict, List, Tuple, Optional
import numpy as np

from .utils import normalize_text

# Try to import OCR engines
try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    import easyocr
except ImportError:
    easyocr = None

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from PIL import Image, ImageEnhance, ImageFilter
except ImportError:
    Image = None

logger = logging.getLogger(__name__)


class EnhancedOCR:
    """Enhanced OCR with multiple engines and preprocessing."""
    
    def __init__(self, use_gpu: bool = False):
        """
        Initialize OCR engines.
        
        Args:
            use_gpu: Whether to use GPU for EasyOCR (faster but requires CUDA)
        """
        self.use_gpu = use_gpu
        self.easyocr_reader = None
        
        # Initialize EasyOCR if available
        if easyocr is not None:
            try:
                # Support English and Filipino languages
                self.easyocr_reader = easyocr.Reader(['en', 'tl'], gpu=use_gpu)
                logger.info("EasyOCR initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize EasyOCR: {e}")
        
        # Enhanced regex patterns
        self._name_pattern = re.compile(
            r"(full\s*)?name[:\-]?\s*(?P<value>[A-Z][A-Z ,.'-]+)|"
            r"(?P<value2>[A-Z][A-Z]+,\s*[A-Z][A-Z ]+(?:\s+[A-Z]\.?)?)|"
            r"(?P<value3>^[A-Z][A-Z]+\s+[A-Z][A-Z]+(?:\s+[A-Z][A-Z]+)?$)",  # Standalone name
            re.IGNORECASE | re.MULTILINE
        )
        
        self._birthday_pattern = re.compile(
            r"(birth|bday|birthday|dob|date\s*of\s*birth)[:\-]?\s*(?P<value>[0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})|"
            r"(?P<value2>[0-9]{4}[\/\-][0-9]{1,2}[\/\-][0-9]{1,2})|"
            r"(?P<value3>(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+[0-9]{1,2},?\s+[0-9]{4})",
            re.IGNORECASE
        )
        
        self._id_number_pattern = re.compile(
            r"(id|control|philid|philsys|license|passport|umid|sss|tin)\s*(no\.?|number|#)?[:\-]?\s*(?P<value>[A-Z0-9\-]+)|"
            r"(?P<value2>[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4})|"
            r"(?P<value3>[A-Z][0-9]{2}[-\s]?[0-9]{8})",
            re.IGNORECASE
        )
        
        self._address_pattern = re.compile(
            r"address[:\-]?\s*(?P<value>[A-Z0-9][^\n]+)|"
            r"(?P<value2>\d+\s+[A-Z][A-Za-z\s,]+(?:city|municipality|province))",
            re.IGNORECASE
        )
        
        self._sex_pattern = re.compile(r"(sex|gender)[:\-]?\s*(?P<value>m|f|male|female)", re.IGNORECASE)
        self._nationality_pattern = re.compile(r"nationality[:\-]?\s*(?P<value>[A-Z]+)", re.IGNORECASE)
    
    def preprocess_image(self, image) -> List:
        """
        Apply multiple preprocessing techniques to improve OCR accuracy.
        
        Returns list of preprocessed images to try.
        """
        if cv2 is None or Image is None:
            return [image]
        
        preprocessed_images = [image]  # Original
        
        try:
            # Convert PIL to numpy if needed
            if hasattr(image, 'mode'):
                img_array = np.array(image)
            else:
                img_array = image
            
            # Convert to grayscale
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # 1. Adaptive thresholding (good for varying lighting)
            adaptive = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            preprocessed_images.append(Image.fromarray(adaptive))
            
            # 2. Denoising
            denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
            preprocessed_images.append(Image.fromarray(denoised))
            
            # 3. Contrast enhancement with CLAHE
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            preprocessed_images.append(Image.fromarray(enhanced))
            
            # 4. Morphological operations (remove noise)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            morph = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
            preprocessed_images.append(Image.fromarray(morph))
            
            # 5. Sharpening
            pil_img = Image.fromarray(gray)
            sharpened = pil_img.filter(ImageFilter.SHARPEN)
            preprocessed_images.append(sharpened)
            
            # 6. High contrast
            enhancer = ImageEnhance.Contrast(pil_img)
            high_contrast = enhancer.enhance(2.0)
            preprocessed_images.append(high_contrast)
            
            logger.debug(f"Generated {len(preprocessed_images)} preprocessed versions")
            
        except Exception as e:
            logger.warning(f"Preprocessing failed: {e}")
        
        return preprocessed_images
    
    def extract_with_easyocr(self, image) -> str:
        """Extract text using EasyOCR."""
        if self.easyocr_reader is None:
            return ""
        
        try:
            # Convert PIL to numpy if needed
            if hasattr(image, 'mode'):
                img_array = np.array(image)
            else:
                img_array = image
            
            # EasyOCR returns list of (bbox, text, confidence)
            results = self.easyocr_reader.readtext(img_array)
            
            # Extract text with confidence > 0.3
            texts = [text for (bbox, text, conf) in results if conf > 0.3]
            combined_text = "\n".join(texts)
            
            logger.debug(f"EasyOCR extracted {len(texts)} text blocks")
            return combined_text
            
        except Exception as e:
            logger.warning(f"EasyOCR extraction failed: {e}")
            return ""
    
    def extract_with_tesseract(self, image, psm_mode: int = 6) -> str:
        """Extract text using Tesseract with specific PSM mode."""
        if pytesseract is None:
            return ""
        
        try:
            config = f"--psm {psm_mode}"
            text = pytesseract.image_to_string(image, config=config)
            return text
        except Exception as e:
            logger.warning(f"Tesseract extraction failed (PSM {psm_mode}): {e}")
            return ""
    
    def extract_text_hybrid(self, image) -> Tuple[str, Dict[str, float]]:
        """
        Extract text using hybrid approach (multiple engines and preprocessing).
        
        Returns:
            Tuple of (combined_text, confidence_scores)
        """
        all_texts = []
        confidence_scores = {}
        
        # Preprocess image
        preprocessed_images = self.preprocess_image(image)
        
        # Try EasyOCR on original and best preprocessed version
        if self.easyocr_reader is not None:
            for idx, img in enumerate(preprocessed_images[:3]):  # Try first 3 versions
                text = self.extract_with_easyocr(img)
                if text:
                    all_texts.append(text)
                    confidence_scores[f'easyocr_v{idx}'] = 0.9  # EasyOCR is generally high quality
        
        # Try Tesseract with multiple PSM modes
        if pytesseract is not None:
            psm_modes = [6, 3, 4, 11]  # Different page segmentation modes
            for psm in psm_modes:
                for idx, img in enumerate(preprocessed_images[:2]):  # Try first 2 versions
                    text = self.extract_with_tesseract(img, psm)
                    if text:
                        all_texts.append(text)
                        confidence_scores[f'tesseract_psm{psm}_v{idx}'] = 0.7
        
        # Combine all texts (deduplicate similar lines)
        combined_text = self._combine_texts(all_texts)
        
        logger.info(f"Hybrid OCR extracted from {len(all_texts)} attempts")
        return combined_text, confidence_scores
    
    def _combine_texts(self, texts: List[str]) -> str:
        """Combine multiple OCR results, removing duplicates."""
        if not texts:
            return ""
        
        # Split into lines and normalize
        all_lines = []
        for text in texts:
            lines = [normalize_text(line) for line in text.splitlines()]
            all_lines.extend([line for line in lines if line])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_lines = []
        for line in all_lines:
            line_lower = line.lower()
            if line_lower not in seen:
                seen.add(line_lower)
                unique_lines.append(line)
        
        return "\n".join(unique_lines)
    
    def extract_id_data(self, image, id_type: str | None = None) -> Dict[str, str]:
        """
        Extract structured data from ID image using enhanced OCR.
        
        Args:
            image: PIL Image or numpy array
            id_type: Type of ID (optional)
        
        Returns:
            Dictionary with extracted fields
        """
        # Extract text using hybrid approach
        raw_text, confidence_scores = self.extract_text_hybrid(image)
        
        if not raw_text:
            logger.warning("No text extracted from image")
            return {"raw_text": "", "id_type": id_type or ""}
        
        # Normalize text
        normalized_lines = [normalize_text(line) for line in raw_text.splitlines() if normalize_text(line)]
        normalized_text = "\n".join(normalized_lines)
        
        # Extract structured data
        extracted: Dict[str, str] = {
            "raw_text": raw_text,
            "id_type": id_type or "",
            "ocr_confidence": str(max(confidence_scores.values()) if confidence_scores else 0.0)
        }
        
        # Extract fields using patterns
        extracted.update(self._match_pattern(normalized_text, self._name_pattern, "full_name"))
        extracted.update(self._match_pattern(normalized_text, self._birthday_pattern, "date_of_birth"))
        extracted.update(self._match_pattern(normalized_text, self._id_number_pattern, "id_number"))
        extracted.update(self._match_pattern(normalized_text, self._address_pattern, "address"))
        extracted.update(self._match_pattern(normalized_text, self._sex_pattern, "sex"))
        extracted.update(self._match_pattern(normalized_text, self._nationality_pattern, "nationality"))
        
        # Try to split full name into first/last if found
        if "full_name" in extracted:
            self._split_name(extracted)
        
        logger.debug(f"Enhanced OCR extracted data: {extracted}")
        return extracted
    
    def _match_pattern(self, text: str, pattern: re.Pattern[str], key: str) -> Dict[str, str]:
        """Match pattern and extract value from named groups."""
        match = pattern.search(text)
        if not match:
            return {}
        
        # Try to get value from any named group
        for group_name in match.groupdict():
            if match.group(group_name):
                value = normalize_text(match.group(group_name))
                if value:
                    return {key: value}
        
        return {}
    
    def _split_name(self, extracted: Dict[str, str]) -> None:
        """Try to split full name into first and last name."""
        full_name = extracted.get("full_name", "")
        if not full_name:
            return
        
        # Handle "LASTNAME, FIRSTNAME" format
        if "," in full_name:
            parts = full_name.split(",", 1)
            extracted["last_name"] = normalize_text(parts[0])
            extracted["first_name"] = normalize_text(parts[1])
        else:
            # Handle "FIRSTNAME LASTNAME" format
            parts = full_name.split()
            if len(parts) >= 2:
                extracted["first_name"] = parts[0]
                extracted["last_name"] = " ".join(parts[1:])


# Global instance (lazy initialization)
_ocr_instance: Optional[EnhancedOCR] = None


def get_enhanced_ocr(use_gpu: bool = False) -> EnhancedOCR:
    """Get or create global EnhancedOCR instance."""
    global _ocr_instance
    if _ocr_instance is None:
        _ocr_instance = EnhancedOCR(use_gpu=use_gpu)
    return _ocr_instance


def extract_id_text_enhanced(image, id_type: str | None = None) -> Dict[str, str]:
    """
    Enhanced OCR extraction function (drop-in replacement for extract_id_text).
    
    Uses hybrid approach with EasyOCR and Tesseract, plus advanced preprocessing.
    """
    ocr = get_enhanced_ocr()
    return ocr.extract_id_data(image, id_type)
