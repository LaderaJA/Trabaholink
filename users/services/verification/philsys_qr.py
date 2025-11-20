"""PhilSys QR code extraction and preprocessing utilities."""
from __future__ import annotations

import logging
import json
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

try:
    import cv2
    import numpy as np
except ImportError:  # pragma: no cover
    cv2 = None
    np = None

try:
    from pyzbar.pyzbar import decode as pyzbar_decode
except ImportError:  # pragma: no cover
    pyzbar_decode = None

logger = logging.getLogger(__name__)


@dataclass
class QRExtractionResult:
    """Result of QR code extraction from PhilSys ID."""
    success: bool
    qr_data: Optional[str] = None
    pcn: Optional[str] = None  # PhilSys Card Number
    extracted_fields: Dict[str, str] = None
    error_message: Optional[str] = None
    preprocessing_applied: list = None
    
    def __post_init__(self):
        if self.extracted_fields is None:
            self.extracted_fields = {}
        if self.preprocessing_applied is None:
            self.preprocessing_applied = []


class PhilSysQRExtractor:
    """Extract and decode QR codes from PhilSys ID images."""
    
    def __init__(self):
        """Initialize the QR extractor."""
        if cv2 is None:
            raise ImportError("opencv-python is required for PhilSys QR extraction")
        if pyzbar_decode is None:
            raise ImportError("pyzbar is required for QR decoding")
    
    def extract_qr_from_image(self, image_path: str) -> QRExtractionResult:
        """
        Extract QR code from PhilSys ID image with advanced preprocessing.
        
        Args:
            image_path: Path to the PhilSys ID image
            
        Returns:
            QRExtractionResult with extraction status and data
        """
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                return QRExtractionResult(
                    success=False,
                    error_message="Unable to load image"
                )
            
            # Try multiple preprocessing strategies
            strategies = [
                self._try_direct_decode,
                self._try_grayscale_decode,
                self._try_enhanced_decode,
                self._try_adaptive_threshold_decode,
                self._try_deskewed_decode,
            ]
            
            for strategy in strategies:
                result = strategy(image)
                if result.success:
                    logger.info(f"QR extraction successful using: {strategy.__name__}")
                    return result
            
            # All strategies failed
            return QRExtractionResult(
                success=False,
                error_message="QR code not detected. Please upload a clearer image with visible QR code."
            )
            
        except Exception as e:
            logger.exception(f"Error during QR extraction: {e}")
            return QRExtractionResult(
                success=False,
                error_message=f"QR extraction error: {str(e)}"
            )
    
    def _try_direct_decode(self, image: np.ndarray) -> QRExtractionResult:
        """Try direct QR decoding without preprocessing."""
        decoded_objects = pyzbar_decode(image)
        if decoded_objects:
            return self._process_decoded_qr(decoded_objects[0], ["direct"])
        return QRExtractionResult(success=False)
    
    def _try_grayscale_decode(self, image: np.ndarray) -> QRExtractionResult:
        """Try QR decoding with grayscale conversion."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        decoded_objects = pyzbar_decode(gray)
        if decoded_objects:
            return self._process_decoded_qr(decoded_objects[0], ["grayscale"])
        return QRExtractionResult(success=False)
    
    def _try_enhanced_decode(self, image: np.ndarray) -> QRExtractionResult:
        """Try QR decoding with contrast enhancement and denoising."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(enhanced, None, 10, 7, 21)
        
        decoded_objects = pyzbar_decode(denoised)
        if decoded_objects:
            return self._process_decoded_qr(
                decoded_objects[0], 
                ["grayscale", "clahe", "denoise"]
            )
        return QRExtractionResult(success=False)
    
    def _try_adaptive_threshold_decode(self, image: np.ndarray) -> QRExtractionResult:
        """Try QR decoding with adaptive thresholding."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            blurred, 255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        decoded_objects = pyzbar_decode(thresh)
        if decoded_objects:
            return self._process_decoded_qr(
                decoded_objects[0], 
                ["grayscale", "gaussian_blur", "adaptive_threshold"]
            )
        return QRExtractionResult(success=False)
    
    def _try_deskewed_decode(self, image: np.ndarray) -> QRExtractionResult:
        """Try QR decoding with deskewing correction."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Detect edges
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        # Detect lines using Hough transform
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
        
        if lines is not None and len(lines) > 0:
            # Calculate average angle
            angles = []
            for line in lines[:10]:  # Use first 10 lines
                rho, theta = line[0]
                angle = (theta * 180 / np.pi) - 90
                angles.append(angle)
            
            avg_angle = np.median(angles)
            
            # Rotate image to correct skew
            if abs(avg_angle) > 0.5:  # Only rotate if significant skew
                h, w = gray.shape
                center = (w // 2, h // 2)
                rotation_matrix = cv2.getRotationMatrix2D(center, avg_angle, 1.0)
                deskewed = cv2.warpAffine(gray, rotation_matrix, (w, h), 
                                         flags=cv2.INTER_CUBIC,
                                         borderMode=cv2.BORDER_REPLICATE)
                
                decoded_objects = pyzbar_decode(deskewed)
                if decoded_objects:
                    return self._process_decoded_qr(
                        decoded_objects[0], 
                        ["grayscale", "deskew", f"angle_{avg_angle:.2f}"]
                    )
        
        return QRExtractionResult(success=False)
    
    def _process_decoded_qr(self, decoded_obj, preprocessing: list) -> QRExtractionResult:
        """Process decoded QR object and extract fields."""
        try:
            # Decode QR data
            qr_data = decoded_obj.data.decode("utf-8", errors="ignore")
            
            # Extract fields from QR data
            extracted_fields = self._parse_philsys_qr(qr_data)
            
            # Extract PCN (PhilSys Card Number) if available
            pcn = extracted_fields.get('pcn') or extracted_fields.get('id_number')
            
            return QRExtractionResult(
                success=True,
                qr_data=qr_data,
                pcn=pcn,
                extracted_fields=extracted_fields,
                preprocessing_applied=preprocessing
            )
            
        except Exception as e:
            logger.error(f"Error processing decoded QR: {e}")
            return QRExtractionResult(
                success=False,
                error_message=f"QR decoding error: {str(e)}"
            )
    
    def _parse_philsys_qr(self, qr_data: str) -> Dict[str, str]:
        """
        Parse PhilSys QR code data.
        
        PhilSys QR codes may contain:
        - JSON format
        - Key-value pairs separated by newlines
        - Comma-separated values
        """
        extracted = {}
        
        # Try JSON parsing first
        try:
            json_data = json.loads(qr_data)
            if isinstance(json_data, dict):
                extracted.update(json_data)
                return extracted
        except (json.JSONDecodeError, ValueError):
            pass
        
        # Try key-value pair parsing
        lines = qr_data.split('\n')
        for line in lines:
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()
                extracted[key] = value
            elif '=' in line:
                key, value = line.split('=', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()
                extracted[key] = value
        
        # Try to extract common PhilSys fields
        if not extracted:
            # Store raw data if no structured parsing worked
            extracted['qr_raw'] = qr_data
            
            # Try to extract PCN pattern: 0000-0000-0000-0000
            import re
            pcn_pattern = r'\b\d{4}-\d{4}-\d{4}-\d{4}\b'
            pcn_match = re.search(pcn_pattern, qr_data)
            if pcn_match:
                extracted['pcn'] = pcn_match.group(0)
        
        return extracted


def is_philsys_id(id_type: str) -> bool:
    """Check if the ID type is PhilSys."""
    return id_type and id_type.lower() in ['philsys', 'philsys_id', 'national_id']
