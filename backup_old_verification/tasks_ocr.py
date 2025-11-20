"""
Separate Celery task for OCR extraction only.
This runs first to extract and validate data before web verification.
"""
from celery import shared_task
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=2)
def extract_id_data(self, user_id: int) -> Dict[str, Any]:
    """
    Extract data from ID document using OCR.
    This is step 1 of the verification process.
    
    Returns:
        Dict with extracted data and extraction quality score
    """
    from users.models import CustomUser
    from users.services.verification.progress_tracker import VerificationProgressTracker
    from users.services.verification.ocr_philsys import PhilSysOCR
    from users.services.verification.utils import load_image
    from users.services.verification.qr import extract_qr_data
    from PIL import Image
    
    tracker = VerificationProgressTracker(user_id)
    
    try:
        user = CustomUser.objects.get(pk=user_id)
        tracker.update("ocr_extraction", 10, "Loading ID image...")
        
        if not user.id_image:
            raise ValueError("No ID image uploaded")
        
        # Load ID image
        id_image = load_image(user.id_image)
        tracker.update("ocr_extraction", 20, "Preprocessing image...")
        
        # Determine ID type
        id_type = (user.id_type or '').lower()
        is_philsys = id_type in ['philsys', 'philsys_id', 'national_id', 'philsys id', 'national id']
        
        extracted_data = {}
        
        # Extract using appropriate OCR
        # Try improved OCR first (better preprocessing and regex)
        try:
            tracker.update("ocr_extraction", 30, "Extracting data with improved OCR...")
            from users.services.verification.ocr_improved import extract_id_text_improved
            extracted_data = extract_id_text_improved(id_image, user.id_type)
            logger.info(f"Improved OCR extracted {len(extracted_data)} fields for user {user_id}")
            
            # If extraction quality is poor, try specialized OCR
            if extracted_data.get('extraction_quality') == 'poor':
                logger.warning(f"Improved OCR quality poor, trying specialized OCR for user {user_id}")
                if is_philsys:
                    ocr = PhilSysOCR()
                    fallback_data = ocr.extract_philsys_data(id_image)
                    # Merge with improved OCR data (keep best fields)
                    for key, value in fallback_data.items():
                        if value and (key not in extracted_data or not extracted_data.get(key)):
                            extracted_data[key] = value
                    logger.info(f"Merged PhilSys OCR data for user {user_id}")
        except Exception as e:
            logger.warning(f"Improved OCR failed for user {user_id}: {e}, falling back to standard OCR")
            # Fallback to original OCR
            if is_philsys:
                tracker.update("ocr_extraction", 30, "Extracting PhilSys data...")
                ocr = PhilSysOCR()
                extracted_data = ocr.extract_philsys_data(id_image)
                logger.info(f"PhilSys OCR extracted {len(extracted_data)} fields for user {user_id}")
            else:
                tracker.update("ocr_extraction", 30, "Extracting ID data...")
                from users.services.verification.ocr import extract_id_text
                extracted_data = extract_id_text(id_image, user.id_type)
                logger.info(f"Standard OCR extracted {len(extracted_data)} fields for user {user_id}")
        
        # Try QR code extraction
        tracker.update("ocr_extraction", 50, "Scanning QR code...")
        try:
            qr_data = extract_qr_data(id_image)
            if qr_data:
                # Merge QR data with OCR data (QR takes priority)
                extracted_data.update(qr_data)
                logger.info(f"QR code data merged for user {user_id}")
        except Exception as e:
            logger.warning(f"QR extraction failed for user {user_id}: {e}")
        
        # Calculate extraction quality score
        tracker.update("ocr_extraction", 70, "Calculating extraction quality...")
        quality_score = calculate_extraction_quality(extracted_data)
        
        # Clean and normalize extracted data
        tracker.update("ocr_extraction", 80, "Cleaning extracted data...")
        cleaned_data = clean_extracted_data(extracted_data)
        
        # Store extracted data in user model for quick access
        user.ocr_raw_text = cleaned_data.get('raw_text', '')[:5000]  # Limit size
        user.save(update_fields=['ocr_raw_text'])
        
        result = {
            'success': True,
            'user_id': user_id,
            'extracted_data': cleaned_data,
            'quality_score': quality_score,
            'is_philsys': is_philsys,
            'fields_extracted': len([k for k in cleaned_data.keys() if k != 'raw_text' and cleaned_data[k]])
        }
        
        tracker.update("ocr_extraction", 100, f"Extracted {result['fields_extracted']} fields successfully")
        logger.info(f"OCR extraction completed for user {user_id}: quality={quality_score:.2f}, fields={result['fields_extracted']}")
        
        return result
        
    except Exception as e:
        logger.exception(f"OCR extraction failed for user {user_id}")
        tracker.error(f"OCR extraction failed: {str(e)}")
        return {
            'success': False,
            'user_id': user_id,
            'error': str(e)
        }


def calculate_extraction_quality(data: Dict[str, Any]) -> float:
    """
    Calculate quality score of extracted data (0.0 to 1.0).
    
    Checks:
    - Presence of key fields
    - Data format validity
    - Text length and readability
    """
    score = 0.0
    max_score = 0.0
    
    # Key fields for PhilSys
    key_fields = {
        'full_name': 0.25,
        'pcn': 0.20,  # PhilSys Card Number
        'date_of_birth': 0.15,
        'address': 0.15,
        'sex': 0.10,
        'raw_text': 0.15
    }
    
    for field, weight in key_fields.items():
        max_score += weight
        value = data.get(field, '')
        
        if value and str(value).strip():
            # Field exists and has content
            score += weight * 0.5
            
            # Additional quality checks
            if field == 'pcn':
                # PCN should be 16 digits with dashes: 0000-0000-0000-0000
                import re
                if re.match(r'\d{4}-\d{4}-\d{4}-\d{4}', str(value)):
                    score += weight * 0.5
            elif field == 'date_of_birth':
                # Should be a valid date format
                if len(str(value)) >= 8:  # At least YYYYMMDD
                    score += weight * 0.5
            elif field == 'full_name':
                # Should have at least 2 words
                if len(str(value).split()) >= 2:
                    score += weight * 0.5
            elif field == 'raw_text':
                # Should have reasonable length
                if len(str(value)) > 50:
                    score += weight * 0.5
            else:
                score += weight * 0.5
    
    return min(score / max_score, 1.0) if max_score > 0 else 0.0


def clean_extracted_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clean and normalize extracted data.
    Remove garbage characters, normalize spacing, etc.
    """
    import re
    
    cleaned = {}
    
    for key, value in data.items():
        if not value:
            continue
        
        value_str = str(value).strip()
        
        if key == 'raw_text':
            # Keep raw text but limit length
            cleaned[key] = value_str[:5000]
        elif key == 'pcn' or key == 'id_number':
            # Clean PCN/ID: keep only digits and dashes
            id_clean = re.sub(r'[^0-9-]', '', value_str)
            # Format PhilSys PCN if it's 16 digits
            if len(id_clean.replace('-', '')) == 16:
                digits = id_clean.replace('-', '')
                id_clean = f"{digits[0:4]}-{digits[4:8]}-{digits[8:12]}-{digits[12:16]}"
            if id_clean and len(id_clean) >= 8:
                cleaned[key] = id_clean
        elif key == 'full_name':
            # Clean name: remove numbers and special chars, keep letters, spaces, commas, periods
            name_clean = re.sub(r'[^A-Za-z\s,.\-]', '', value_str)
            name_clean = re.sub(r'\s+', ' ', name_clean).strip()
            # Remove if too short or too long (likely OCR garbage)
            if name_clean and 5 <= len(name_clean) <= 100:
                cleaned[key] = name_clean.title()  # Title case for names
        elif key == 'address':
            # Clean address: limit length to reasonable address size
            addr_clean = re.sub(r'[^A-Za-z0-9\s,.\-#/]', '', value_str)
            addr_clean = re.sub(r'\s+', ' ', addr_clean).strip()
            # Limit address to first 200 characters (reasonable address length)
            if addr_clean:
                # Try to extract just the address part (before any garbage)
                lines = addr_clean.split()
                # Take first reasonable chunk (up to 30 words or 200 chars)
                reasonable_addr = ' '.join(lines[:30])[:200]
                if reasonable_addr and len(reasonable_addr) >= 10:
                    cleaned[key] = reasonable_addr.title()
        elif key == 'date_of_birth':
            # Normalize date format
            date_clean = re.sub(r'[^A-Za-z0-9\s,/\-]', '', value_str)
            # Remove if too long (likely garbage)
            if date_clean and len(date_clean) <= 30:
                cleaned[key] = date_clean
        elif key == 'sex':
            # Normalize sex: M/F
            sex_upper = value_str.upper()
            if 'M' in sex_upper or 'MALE' in sex_upper or 'LALAKI' in sex_upper:
                cleaned[key] = 'M'
            elif 'F' in sex_upper or 'FEMALE' in sex_upper or 'BABAE' in sex_upper:
                cleaned[key] = 'F'
        elif key == 'contact_number':
            # Clean phone number: keep only digits, +, and dashes
            phone_clean = re.sub(r'[^0-9+\-]', '', value_str)
            if phone_clean and 7 <= len(phone_clean.replace('-', '').replace('+', '')) <= 15:
                cleaned[key] = phone_clean
        else:
            # Generic cleaning - remove excessive whitespace
            generic_clean = re.sub(r'\s+', ' ', value_str).strip()
            if generic_clean and len(generic_clean) <= 500:  # Prevent garbage
                cleaned[key] = generic_clean
    
    return cleaned
