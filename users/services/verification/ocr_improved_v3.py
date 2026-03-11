"""
Improved OCR Module V3 for Philippine ID Cards
Enhanced preprocessing and text extraction with better accuracy
Fixes:
- Better image preprocessing (rotation, perspective, denoising)
- More PSM modes
- Better text cleaning
- Handles low quality images
"""
import re
import logging
from typing import Dict, Optional, Tuple, List
from PIL import Image
import numpy as np
import cv2

logger = logging.getLogger(__name__)

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("pytesseract not available")


class ImprovedIDOCR:
    """Improved OCR for Philippine ID cards with robust preprocessing."""
    
    # Field patterns for Philippine IDs
    PATTERNS = {
        'pcn': [
            r'(\d{4})[\s-]?(\d{4})[\s-]?(\d{4})[\s-]?(\d{4})',  # 16-digit PCN
            r'PCN[\s:]*(\d{4})[\s-]?(\d{4})[\s-]?(\d{4})[\s-]?(\d{4})',
        ],
        'date_of_birth': [
            r'(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER|JAN|FEB|MAR|APR|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[\s,]+(\d{1,2})[\s,]+(\d{4})',
            r'(\d{1,2})[\s/-](\d{1,2})[\s/-](\d{4})',  # DD/MM/YYYY
            r'(\d{4})[\s/-](\d{1,2})[\s/-](\d{1,2})',  # YYYY/MM/DD
            r'DATE\s+OF\s+BIRTH[\s:]*(\d{1,2})[\s/-](\d{1,2})[\s/-](\d{4})',
        ],
        'sex': [
            r'\b(MALE|FEMALE|M|F)\b',
            r'SEX[\s:]*([MF]|MALE|FEMALE)',
        ],
    }
    
    MONTHS = {
        'JANUARY': '01', 'JAN': '01',
        'FEBRUARY': '02', 'FEB': '02',
        'MARCH': '03', 'MAR': '03',
        'APRIL': '04', 'APR': '04',
        'MAY': '05',
        'JUNE': '06', 'JUN': '06',
        'JULY': '07', 'JUL': '07',
        'AUGUST': '08', 'AUG': '08',
        'SEPTEMBER': '09', 'SEP': '09', 'SEPT': '09',
        'OCTOBER': '10', 'OCT': '10',
        'NOVEMBER': '11', 'NOV': '11',
        'DECEMBER': '12', 'DEC': '12',
    }
    
    def __init__(self):
        if not TESSERACT_AVAILABLE:
            raise ImportError("pytesseract is required for OCR")
    
    def detect_and_correct_skew(self, image: np.ndarray) -> np.ndarray:
        """Detect and correct image rotation/skew."""
        try:
            # Make a copy
            img = image.copy()
            
            # Convert to grayscale if needed
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = img.copy()
            
            # Threshold
            thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
            
            # Find contours
            coords = np.column_stack(np.where(thresh > 0))
            
            if len(coords) < 100:  # Not enough points
                return image
            
            # Get rotation angle
            angle = cv2.minAreaRect(coords)[-1]
            
            # Adjust angle
            if angle < -45:
                angle = 90 + angle
            elif angle > 45:
                angle = angle - 90
            
            # Only correct if angle is significant
            if abs(angle) > 0.5:
                logger.info(f"Correcting skew: {angle:.2f} degrees")
                h, w = gray.shape
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                rotated = cv2.warpAffine(image, M, (w, h), 
                                        flags=cv2.INTER_CUBIC,
                                        borderMode=cv2.BORDER_REPLICATE)
                return rotated
            
            return image
        except Exception as e:
            logger.warning(f"Skew correction failed: {e}")
            return image
    
    def enhance_image(self, image: np.ndarray) -> np.ndarray:
        """Apply multiple enhancement techniques."""
        try:
            # Convert to grayscale
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # Upscale if too small (important for quality)
            height, width = gray.shape
            if width < 1500 or height < 1000:
                scale = max(1500 / width, 1000 / height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
                logger.info(f"Upscaled image from {width}x{height} to {new_width}x{new_height}")
            
            # Denoise - stronger denoising
            denoised = cv2.fastNlMeansDenoising(gray, None, h=15, templateWindowSize=7, searchWindowSize=21)
            
            # Enhance contrast with CLAHE
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(denoised)
            
            # Sharpen the image
            kernel_sharpen = np.array([[-1,-1,-1],
                                       [-1, 9,-1],
                                       [-1,-1,-1]])
            sharpened = cv2.filter2D(enhanced, -1, kernel_sharpen)
            
            return sharpened
        except Exception as e:
            logger.error(f"Image enhancement failed: {e}")
            return image
    
    def preprocess_for_ocr(self, image: Image.Image) -> List[Tuple[np.ndarray, str]]:
        """
        Create multiple preprocessed versions of the image for OCR.
        Returns list of (preprocessed_image, description) tuples.
        """
        logger.info("Starting advanced image preprocessing")
        
        # Convert PIL to OpenCV
        img_array = np.array(image)
        
        # Convert to BGR if needed
        if len(img_array.shape) == 2:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)
        elif img_array.shape[2] == 4:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
        
        # Correct skew
        img_array = self.detect_and_correct_skew(img_array)
        
        # Enhance image
        enhanced = self.enhance_image(img_array)
        
        # Create multiple versions for OCR
        versions = []
        
        # Version 1: Adaptive threshold (good for varying lighting)
        adaptive_thresh = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        versions.append((adaptive_thresh, "Adaptive Threshold"))
        
        # Version 2: Otsu's thresholding (good for bimodal images)
        _, otsu_thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        versions.append((otsu_thresh, "Otsu Threshold"))
        
        # Version 3: Enhanced grayscale (no threshold, preserve gray values)
        versions.append((enhanced, "Enhanced Grayscale"))
        
        # Version 4: Inverted (for dark text on light background)
        inverted = cv2.bitwise_not(enhanced)
        versions.append((inverted, "Inverted"))
        
        logger.info(f"Created {len(versions)} preprocessed versions")
        return versions
    
    def extract_text_multi_version(self, image: Image.Image) -> Tuple[str, float]:
        """
        Extract text using multiple preprocessing versions and PSM modes.
        Returns best text and confidence score.
        """
        logger.info("Starting multi-version OCR extraction")
        
        # Get multiple preprocessed versions
        preprocessed_versions = self.preprocess_for_ocr(image)
        
        # PSM modes to try
        psm_modes = [
            6,  # Uniform block of text
            3,  # Fully automatic
            11, # Sparse text
            4,  # Single column of text
            1,  # Automatic with OSD (Orientation and Script Detection)
        ]
        
        all_results = []
        
        for version_img, version_name in preprocessed_versions:
            # Convert to PIL for tesseract
            pil_img = Image.fromarray(version_img)
            
            for psm in psm_modes:
                try:
                    # Less restrictive whitelist - allow more characters
                    custom_config = f'--oem 3 --psm {psm}'
                    
                    # Extract text
                    text = pytesseract.image_to_string(pil_img, config=custom_config, lang='eng')
                    
                    # Get confidence
                    try:
                        data = pytesseract.image_to_data(
                            pil_img, config=custom_config, lang='eng',
                            output_type=pytesseract.Output.DICT
                        )
                        confidences = [int(conf) for conf in data['conf'] if conf != '-1']
                        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                    except:
                        avg_confidence = 0
                    
                    # Calculate quality score based on text length and confidence
                    text_length = len(text.strip())
                    quality_score = (avg_confidence * 0.7) + (min(text_length, 500) / 500 * 30)
                    
                    all_results.append({
                        'text': text,
                        'confidence': avg_confidence,
                        'quality_score': quality_score,
                        'version': version_name,
                        'psm': psm,
                        'length': text_length
                    })
                    
                    logger.debug(f"{version_name} + PSM {psm}: {text_length} chars, conf={avg_confidence:.1f}%, score={quality_score:.1f}")
                    
                except Exception as e:
                    logger.warning(f"OCR failed for {version_name} + PSM {psm}: {e}")
        
        if not all_results:
            logger.error("No OCR results obtained")
            return "", 0.0
        
        # Sort by quality score
        all_results.sort(key=lambda x: x['quality_score'], reverse=True)
        
        # Get best result
        best = all_results[0]
        logger.info(f"Best result: {best['version']} + PSM {best['psm']}, "
                   f"confidence={best['confidence']:.1f}%, "
                   f"quality_score={best['quality_score']:.1f}, "
                   f"length={best['length']} chars")
        
        # Combine top 3 results for better coverage
        combined_texts = []
        for result in all_results[:3]:
            if result['text'].strip():
                combined_texts.append(result['text'])
        
        combined = "\n".join(combined_texts)
        avg_confidence = sum(r['confidence'] for r in all_results[:3]) / min(3, len(all_results))
        
        return combined, avg_confidence
    
    def parse_pcn(self, text: str) -> Optional[str]:
        """Extract and format Philippine Card Number (PCN)."""
        for pattern in self.PATTERNS['pcn']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) == 4:
                    pcn = f"{match.group(1)}-{match.group(2)}-{match.group(3)}-{match.group(4)}"
                    logger.info(f"Extracted PCN: {pcn}")
                    return pcn
                elif len(match.groups()) == 1:
                    pcn = match.group(1)
                    logger.info(f"Extracted PCN: {pcn}")
                    return pcn
        return None
    
    def parse_date_of_birth(self, text: str) -> Optional[str]:
        """Extract and format date of birth."""
        for pattern in self.PATTERNS['date_of_birth']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                
                # Month name format
                if len(groups) == 3 and groups[0].upper() in self.MONTHS:
                    month = self.MONTHS[groups[0].upper()]
                    day = groups[1].zfill(2)
                    year = groups[2]
                    dob = f"{year}-{month}-{day}"
                    logger.info(f"Extracted DOB: {dob}")
                    return dob
                
                # Numeric formats
                elif len(groups) == 3:
                    # Try different orderings
                    if len(groups[0]) == 4:  # YYYY/MM/DD
                        dob = f"{groups[0]}-{groups[1].zfill(2)}-{groups[2].zfill(2)}"
                    else:  # DD/MM/YYYY
                        dob = f"{groups[2]}-{groups[1].zfill(2)}-{groups[0].zfill(2)}"
                    logger.info(f"Extracted DOB: {dob}")
                    return dob
        return None
    
    def parse_sex(self, text: str) -> Optional[str]:
        """Extract sex/gender."""
        for pattern in self.PATTERNS['sex']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                sex_value = match.group(1).upper()
                if sex_value in ['M', 'MALE']:
                    logger.info("Extracted sex: MALE")
                    return 'MALE'
                elif sex_value in ['F', 'FEMALE']:
                    logger.info("Extracted sex: FEMALE")
                    return 'FEMALE'
        return None
    
    def parse_name(self, text: str) -> Optional[Dict[str, str]]:
        """Extract name fields from text."""
        name_data = {}
        
        # Look for common name patterns in Philippine IDs
        # Names are usually in format: LASTNAME, FIRSTNAME MIDDLENAME
        
        # Pattern 1: Comma-separated format
        name_pattern = r'([A-Z]+(?:\s+[A-Z]+)?),\s*([A-Z]+(?:\s+[A-Z]+)?(?:\s+[A-Z]+)?)'
        match = re.search(name_pattern, text)
        if match:
            last_name = match.group(1).strip()
            rest = match.group(2).strip().split()
            
            name_data['last_name'] = last_name
            if len(rest) >= 1:
                name_data['first_name'] = rest[0]
            if len(rest) >= 2:
                name_data['middle_name'] = rest[1]
            
            logger.info(f"Extracted name: {name_data}")
            return name_data
        
        return None
    
    def extract_all_fields(self, image: Image.Image) -> Dict[str, any]:
        """Extract all fields from ID image."""
        logger.info("Starting field extraction from ID")
        
        # Extract text
        text, confidence = self.extract_text_multi_version(image)
        
        if not text:
            logger.warning("No text extracted from image")
            return {'ocr_confidence': 0}
        
        # Parse fields
        result = {
            'ocr_confidence': confidence,
            'raw_text': text
        }
        
        # Extract PCN
        pcn = self.parse_pcn(text)
        if pcn:
            result['pcn'] = pcn
        
        # Extract DOB
        dob = self.parse_date_of_birth(text)
        if dob:
            result['date_of_birth'] = dob
        
        # Extract sex
        sex = self.parse_sex(text)
        if sex:
            result['sex'] = sex
        
        # Extract name
        name_data = self.parse_name(text)
        if name_data:
            result.update(name_data)
        
        logger.info(f"Extraction complete. Found {len(result) - 2} fields (confidence: {confidence:.1f}%)")
        return result


# Main extraction function for compatibility
def extract_improved_id_text(image: Image.Image) -> Dict[str, any]:
    """
    Main function to extract text from ID using improved OCR.
    Compatible with existing pipeline.
    """
    try:
        ocr = ImprovedIDOCR()
        return ocr.extract_all_fields(image)
    except Exception as e:
        logger.error(f"Improved OCR failed: {e}")
        return {'error': str(e)}
