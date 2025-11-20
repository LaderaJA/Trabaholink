"""
Enhanced OCR Module V2 for Philippine PhilSys ID Cards
Improved text extraction, preprocessing, and field parsing
"""
import re
import logging
from typing import Dict, Optional, Tuple
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


class PhilSysOCRV2:
    """Enhanced OCR for Philippine PhilSys National ID cards with better accuracy."""
    
    # Field patterns for PhilSys ID
    PATTERNS = {
        'pcn': [
            r'(\d{4})[\s-]?(\d{4})[\s-]?(\d{4})[\s-]?(\d{4})',  # 16-digit PCN
            r'PCN[\s:]*(\d{4})[\s-]?(\d{4})[\s-]?(\d{4})[\s-]?(\d{4})',
        ],
        'date_of_birth': [
            r'(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER|JAN|FEB|MAR|APR|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[\s,]+(\d{1,2})[\s,]+(\d{4})',
            r'(\d{1,2})[\s/-](\d{1,2})[\s/-](\d{4})',  # DD/MM/YYYY
            r'(\d{4})[\s/-](\d{1,2})[\s/-](\d{1,2})',  # YYYY/MM/DD
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
    
    def preprocess_image(self, image: Image.Image) -> Tuple[Image.Image, np.ndarray]:
        """
        Advanced image preprocessing for better OCR accuracy.
        Returns both PIL Image and OpenCV array.
        """
        logger.info("Starting image preprocessing")
        
        # Convert PIL to OpenCV
        img_array = np.array(image)
        
        # Convert to RGB if needed
        if len(img_array.shape) == 2:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)
        elif img_array.shape[2] == 4:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
        
        # Convert to grayscale
        gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
        
        # Resize if image is too small
        height, width = gray.shape
        if width < 1000:
            scale = 1000 / width
            new_width = int(width * scale)
            new_height = int(height * scale)
            gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
            logger.info(f"Resized image from {width}x{height} to {new_width}x{new_height}")
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
        
        # Enhance contrast using CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        
        # Apply adaptive thresholding
        binary = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Morphological operations to remove noise
        kernel = np.ones((1, 1), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
        
        # Convert back to PIL
        processed_pil = Image.fromarray(cleaned)
        
        logger.info("Image preprocessing completed")
        return processed_pil, cleaned
    
    def extract_text(self, image: Image.Image) -> str:
        """Extract raw text from image using multiple OCR configurations."""
        logger.info("Extracting text with Tesseract")
        
        # Preprocess image
        processed_image, _ = self.preprocess_image(image)
        
        # Try multiple PSM (Page Segmentation Mode) configurations
        psm_modes = [
            6,  # Assume a single uniform block of text
            3,  # Fully automatic page segmentation
            11, # Sparse text
        ]
        
        all_text = []
        best_text = ""
        best_confidence = 0
        
        for psm in psm_modes:
            try:
                custom_config = f'--oem 3 --psm {psm} -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-/ ,'
                
                # Get text
                text = pytesseract.image_to_string(processed_image, config=custom_config, lang='eng')
                all_text.append(text)
                
                # Get confidence
                try:
                    data = pytesseract.image_to_data(processed_image, config=custom_config, lang='eng', output_type=pytesseract.Output.DICT)
                    confidences = [int(conf) for conf in data['conf'] if conf != '-1']
                    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                    
                    if avg_confidence > best_confidence:
                        best_confidence = avg_confidence
                        best_text = text
                except Exception as e:
                    logger.debug(f"Could not get confidence for PSM {psm}: {e}")
                
                logger.info(f"PSM {psm}: {len(text)} chars extracted")
            except Exception as e:
                logger.warning(f"PSM {psm} failed: {e}")
        
        # Combine all results
        combined_text = "\n".join(all_text)
        
        logger.info(f"Text extraction complete. Best confidence: {best_confidence:.2f}%")
        logger.info(f"Extracted {len(combined_text)} characters total")
        
        return combined_text if combined_text else best_text
    
    def parse_pcn(self, text: str) -> Optional[str]:
        """Extract and format Philippine Card Number (PCN)."""
        for pattern in self.PATTERNS['pcn']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) == 4:
                    pcn = f"{match.group(1)}-{match.group(2)}-{match.group(3)}-{match.group(4)}"
                    logger.info(f"Extracted PCN: {pcn}")
                    return pcn
        
        logger.warning("PCN not found in text")
        return None
    
    def parse_date_of_birth(self, text: str) -> Optional[str]:
        """Extract and normalize date of birth."""
        # Try month name format first
        for pattern in self.PATTERNS['date_of_birth']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                
                # Month name format
                if groups[0].upper() in self.MONTHS:
                    month = self.MONTHS[groups[0].upper()]
                    day = groups[1].zfill(2)
                    year = groups[2]
                    dob = f"{year}-{month}-{day}"
                    logger.info(f"Extracted DOB: {dob}")
                    return dob
                
                # Numeric format
                elif len(groups) == 3 and groups[0].isdigit():
                    # Try to determine format
                    if int(groups[0]) > 1900:  # YYYY format
                        year, month, day = groups
                    else:  # DD format
                        day, month, year = groups
                    
                    dob = f"{year}-{str(month).zfill(2)}-{str(day).zfill(2)}"
                    logger.info(f"Extracted DOB: {dob}")
                    return dob
        
        logger.warning("Date of birth not found in text")
        return None
    
    def parse_sex(self, text: str) -> Optional[str]:
        """Extract and normalize sex/gender."""
        for pattern in self.PATTERNS['sex']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                sex_value = match.group(1).upper()
                if sex_value in ['M', 'MALE']:
                    logger.info("Extracted sex: Male")
                    return "Male"
                elif sex_value in ['F', 'FEMALE']:
                    logger.info("Extracted sex: Female")
                    return "Female"
        
        logger.warning("Sex not found in text")
        return None
    
    def parse_name(self, text: str) -> Dict[str, str]:
        """
        Extract name components from text.
        PhilSys format usually has: LASTNAME, FIRSTNAME MIDDLENAME
        """
        name_data = {}
        
        # Clean text
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Look for name pattern: uppercase letters only, multiple words
        name_pattern = r'^[A-Z\s,]+$'
        
        potential_names = []
        for i, line in enumerate(lines):
            # Skip if line has numbers or special chars (except comma and space)
            if re.match(name_pattern, line) and len(line) > 3:
                # Skip common non-name words
                if line not in ['REPUBLIC', 'PHILIPPINES', 'PHILSYS', 'MALE', 'FEMALE', 'SEX', 'DATE', 'BIRTH']:
                    potential_names.append((i, line))
        
        # Try to find comma-separated format: LASTNAME, FIRSTNAME MIDDLENAME
        for idx, line in potential_names:
            if ',' in line:
                parts = line.split(',', 1)
                if len(parts) == 2:
                    name_data['last_name'] = parts[0].strip()
                    remaining = parts[1].strip().split()
                    if remaining:
                        name_data['first_name'] = remaining[0]
                    if len(remaining) > 1:
                        name_data['middle_name'] = ' '.join(remaining[1:])
                    
                    full_name = f"{name_data['last_name']}, {name_data.get('first_name', '')} {name_data.get('middle_name', '')}".strip()
                    name_data['full_name'] = full_name
                    logger.info(f"Extracted name: {full_name}")
                    return name_data
        
        # Fallback: Look for consecutive name-like lines
        if len(potential_names) >= 2:
            # Assume first line is last name, second is first name
            name_data['last_name'] = potential_names[0][1]
            name_data['first_name'] = potential_names[1][1].split()[0]
            
            if len(potential_names) >= 3:
                name_data['middle_name'] = potential_names[2][1]
            
            full_name = f"{name_data['last_name']}, {name_data.get('first_name', '')} {name_data.get('middle_name', '')}".strip()
            name_data['full_name'] = full_name
            logger.info(f"Extracted name (fallback): {full_name}")
            return name_data
        
        logger.warning("Could not extract name from text")
        return name_data
    
    def extract_philsys_data(self, image: Image.Image) -> Dict[str, any]:
        """
        Main extraction method for PhilSys ID.
        Returns dictionary with all extracted fields.
        """
        logger.info("Starting PhilSys ID data extraction")
        
        try:
            # Extract raw text
            raw_text = self.extract_text(image)
            
            # Parse fields
            data = {
                'raw_text': raw_text,
                'extraction_method': 'tesseract_v2',
            }
            
            # Extract PCN
            pcn = self.parse_pcn(raw_text)
            if pcn:
                data['pcn'] = pcn
                data['id_number'] = pcn
            
            # Extract DOB
            dob = self.parse_date_of_birth(raw_text)
            if dob:
                data['date_of_birth'] = dob
            
            # Extract sex
            sex = self.parse_sex(raw_text)
            if sex:
                data['sex'] = sex
            
            # Extract name
            name_data = self.parse_name(raw_text)
            data.update(name_data)
            
            # Calculate extraction quality
            required_fields = ['pcn', 'date_of_birth', 'sex', 'full_name']
            extracted_count = sum(1 for field in required_fields if field in data)
            
            data['fields_extracted_count'] = extracted_count
            
            if extracted_count == 4:
                data['extraction_quality'] = 'excellent'
            elif extracted_count >= 3:
                data['extraction_quality'] = 'good'
            elif extracted_count >= 2:
                data['extraction_quality'] = 'fair'
            else:
                data['extraction_quality'] = 'poor'
            
            logger.info(f"Extraction complete: {extracted_count}/4 fields, quality: {data['extraction_quality']}")
            
            return data
            
        except Exception as e:
            logger.exception(f"Error during OCR extraction: {e}")
            return {
                'error': str(e),
                'extraction_quality': 'failed',
                'fields_extracted_count': 0
            }
