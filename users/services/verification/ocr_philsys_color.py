"""
Enhanced OCR specifically for PhilSys IDs with color/hologram overlays.

This module handles the rainbow hologram security feature on PhilSys IDs
that interferes with standard grayscale OCR.
"""
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
    from PIL import Image
except ImportError:
    Image = None

logger = logging.getLogger(__name__)


class PhilSysColorOCR:
    """OCR optimized for PhilSys IDs with rainbow hologram overlays."""
    
    def __init__(self):
        """Initialize patterns for PhilSys ID."""
        # PhilSys Card Number (PCN): 0000-0000-0000-0000
        self._pcn_pattern = re.compile(
            r'([0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4})',
            re.IGNORECASE
        )
        
        # Name patterns - PhilSys format
        self._lastname_pattern = re.compile(
            r'(?:Apelyido|Last\s+Name)[:\s]*([A-Z][A-Z\s]+)',
            re.IGNORECASE
        )
        self._firstname_pattern = re.compile(
            r'(?:Mga\s+Pangalan|Given\s+Names)[:\s]*([A-Z][A-Z\s]+)',
            re.IGNORECASE
        )
        self._middlename_pattern = re.compile(
            r'(?:Gitnang\s+Apelyido|Middle\s+Name)[:\s]*([A-Z][A-Z\s]+)',
            re.IGNORECASE
        )
        
        # Date pattern - PhilSys shows: SEPTEMBER 01, 1995
        self._date_pattern = re.compile(
            r'(?:Petsa\s+ng\s+Kapanganakan|Date\s+of\s+Birth)[:\s]*'
            r'([A-Z]+\s+[0-9]{1,2},?\s+[0-9]{4})',
            re.IGNORECASE
        )
        
        # Address pattern
        self._address_pattern = re.compile(
            r'(?:Tirahan|Address)[:\s]*([#0-9][^\n]+)',
            re.IGNORECASE
        )
    
    def preprocess_color_philsys(self, image) -> List:
        """
        Preprocess PhilSys ID with rainbow hologram overlay.
        
        Strategy:
        1. Extract individual color channels (R, G, B)
        2. Try each channel separately (hologram affects channels differently)
        3. Use color-based segmentation to isolate text
        4. Apply aggressive thresholding
        """
        if cv2 is None or Image is None:
            return [image]
        
        preprocessed = []
        
        try:
            # Convert to numpy array
            if hasattr(image, 'mode'):
                img_array = np.array(image)
            else:
                img_array = image
            
            # Ensure RGB
            if len(img_array.shape) == 2:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB)
            elif img_array.shape[2] == 4:  # RGBA
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
            
            height, width = img_array.shape[:2]
            
            # STEP 1: Upscale if needed
            if width < 2000:
                scale = 2000 / width
                new_width = int(width * scale)
                new_height = int(height * scale)
                img_array = cv2.resize(img_array, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
                logger.debug(f"Upscaled to {new_width}x{new_height}")
            
            # STEP 2: Extract color channels
            # Red channel often has best contrast for dark text
            b_channel, g_channel, r_channel = cv2.split(img_array)
            
            # STEP 3: Process RED channel (usually best for dark text)
            # Red text shows up dark in red channel
            red_inv = cv2.bitwise_not(r_channel)  # Invert so red text is white
            
            # Denoise
            red_denoised = cv2.fastNlMeansDenoising(red_inv, None, h=15, templateWindowSize=7, searchWindowSize=21)
            
            # CLAHE for contrast
            clahe = cv2.createCLAHE(clipLimit=5.0, tileGridSize=(8, 8))
            red_enhanced = clahe.apply(red_denoised)
            
            # Threshold
            _, red_thresh = cv2.threshold(red_enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            preprocessed.append(Image.fromarray(red_thresh))
            logger.debug("Added red channel processed")
            
            # STEP 4: Process BLUE channel (good for black text)
            blue_denoised = cv2.fastNlMeansDenoising(b_channel, None, h=15, templateWindowSize=7, searchWindowSize=21)
            blue_enhanced = clahe.apply(blue_denoised)
            _, blue_thresh = cv2.threshold(blue_enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            preprocessed.append(Image.fromarray(blue_thresh))
            logger.debug("Added blue channel processed")
            
            # STEP 5: Process GREEN channel
            green_denoised = cv2.fastNlMeansDenoising(g_channel, None, h=15, templateWindowSize=7, searchWindowSize=21)
            green_enhanced = clahe.apply(green_denoised)
            _, green_thresh = cv2.threshold(green_enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            preprocessed.append(Image.fromarray(green_thresh))
            logger.debug("Added green channel processed")
            
            # STEP 6: Convert to grayscale and process
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            gray_denoised = cv2.fastNlMeansDenoising(gray, None, h=20, templateWindowSize=7, searchWindowSize=21)
            
            # Multiple thresholds on grayscale
            _, gray_otsu = cv2.threshold(gray_denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            preprocessed.append(Image.fromarray(gray_otsu))
            
            gray_adaptive = cv2.adaptiveThreshold(
                gray_denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 11
            )
            preprocessed.append(Image.fromarray(gray_adaptive))
            
            # STEP 7: Color-based text extraction
            # Red text on pink background - extract red
            hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
            
            # Mask for red text (hue around 0/180)
            lower_red1 = np.array([0, 50, 50])
            upper_red1 = np.array([10, 255, 255])
            lower_red2 = np.array([170, 50, 50])
            upper_red2 = np.array([180, 255, 255])
            
            mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)
            mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
            mask_red = cv2.bitwise_or(mask_red1, mask_red2)
            
            # Invert mask (we want text as white)
            mask_red_inv = cv2.bitwise_not(mask_red)
            preprocessed.append(Image.fromarray(mask_red_inv))
            logger.debug("Added red color mask")
            
            # Mask for black text
            lower_black = np.array([0, 0, 0])
            upper_black = np.array([180, 255, 100])
            mask_black = cv2.inRange(hsv, lower_black, upper_black)
            preprocessed.append(Image.fromarray(mask_black))
            logger.debug("Added black color mask")
            
            # STEP 8: Morphological operations to clean up best result
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            morph_close = cv2.morphologyEx(red_thresh, cv2.MORPH_CLOSE, kernel, iterations=1)
            preprocessed.append(Image.fromarray(morph_close))
            
            logger.info(f"Generated {len(preprocessed)} preprocessed versions for color PhilSys")
            
        except Exception as e:
            logger.exception(f"Color PhilSys preprocessing failed: {e}")
            preprocessed.append(image)
        
        return preprocessed
    
    def extract_with_optimized_config(self, image) -> str:
        """Extract text with configuration optimized for PhilSys IDs."""
        if pytesseract is None:
            return ""
        
        all_texts = []
        
        # PSM modes that work for structured IDs
        psm_modes = [6, 4, 3, 11]
        
        for psm in psm_modes:
            try:
                # Optimized for PhilSys text
                config = (
                    f"--psm {psm} --oem 3 --dpi 300 "
                    f"-c preserve_interword_spaces=1 "
                    f"-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789,.-/# "
                )
                
                text = pytesseract.image_to_string(image, config=config, lang='eng')
                if text.strip() and len(text.strip()) > 15:
                    all_texts.append(text)
                    logger.debug(f"PSM {psm} extracted {len(text)} chars")
            except Exception as e:
                logger.warning(f"PSM {psm} failed: {e}")
        
        combined = "\n".join(all_texts)
        return combined
    
    def extract_philsys_color_data(self, image) -> Dict[str, str]:
        """
        Extract data from PhilSys ID with color/hologram overlay.
        
        Args:
            image: PIL Image of PhilSys ID
        
        Returns:
            Dictionary with extracted fields
        """
        # Preprocess with color-aware techniques
        preprocessed_images = self.preprocess_color_philsys(image)
        
        # Extract text from all versions
        all_texts = []
        for idx, img in enumerate(preprocessed_images):
            text = self.extract_with_optimized_config(img)
            if text:
                all_texts.append(text)
                logger.debug(f"Color version {idx}: {len(text)} chars")
        
        if not all_texts:
            logger.warning("No text extracted from color PhilSys ID")
            return {"raw_text": "", "id_type": "philsys"}
        
        # Combine all texts
        combined_text = "\n".join(all_texts)
        
        # Extract structured data
        extracted: Dict[str, str] = {
            "raw_text": combined_text[:2000],
            "id_type": "philsys",
        }
        
        # Extract PCN (most reliable)
        pcn_match = self._pcn_pattern.search(combined_text)
        if pcn_match:
            extracted["id_number"] = normalize_text(pcn_match.group(1))
            logger.info(f"Extracted PCN: {extracted['id_number']}")
        
        # Extract name parts
        lastname_match = self._lastname_pattern.search(combined_text)
        if lastname_match:
            lastname = normalize_text(lastname_match.group(1))
            extracted["last_name"] = lastname
        
        firstname_match = self._firstname_pattern.search(combined_text)
        if firstname_match:
            firstname = normalize_text(firstname_match.group(1))
            extracted["first_name"] = firstname
        
        middlename_match = self._middlename_pattern.search(combined_text)
        if middlename_match:
            middlename = normalize_text(middlename_match.group(1))
            extracted["middle_name"] = middlename
        
        # Combine name if we have parts
        if "last_name" in extracted and "first_name" in extracted:
            full_name = f"{extracted['last_name']}, {extracted['first_name']}"
            if "middle_name" in extracted:
                full_name += f" {extracted['middle_name']}"
            extracted["full_name"] = full_name
        
        # Extract date
        date_match = self._date_pattern.search(combined_text)
        if date_match:
            extracted["date_of_birth"] = normalize_text(date_match.group(1))
        
        # Extract address
        address_match = self._address_pattern.search(combined_text)
        if address_match:
            extracted["address"] = normalize_text(address_match.group(1))
        
        # Fallback: try to find name in format "LASTNAME, FIRSTNAME"
        if "full_name" not in extracted:
            name_lines = [line for line in combined_text.split('\n') if ',' in line]
            for line in name_lines:
                if len(line) > 5 and len(line) < 100:
                    parts = line.split(',')
                    if len(parts) >= 2:
                        lastname = parts[0].strip()
                        firstname = parts[1].strip()
                        if lastname.replace(' ', '').isalpha() and firstname.replace(' ', '').isalpha():
                            extracted["full_name"] = normalize_text(line)
                            break
        
        logger.info(f"Color PhilSys OCR extracted: {list(extracted.keys())}")
        return extracted


# Global instance
_philsys_color_ocr: Optional[PhilSysColorOCR] = None


def get_philsys_color_ocr() -> PhilSysColorOCR:
    """Get or create global PhilSysColorOCR instance."""
    global _philsys_color_ocr
    if _philsys_color_ocr is None:
        _philsys_color_ocr = PhilSysColorOCR()
    return _philsys_color_ocr


def extract_philsys_color_text(image) -> Dict[str, str]:
    """
    Extract text from PhilSys ID with color/hologram overlay.
    
    Use this for PhilSys IDs with rainbow hologram security features.
    """
    ocr = get_philsys_color_ocr()
    return ocr.extract_philsys_color_data(image)
