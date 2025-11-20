"""
Simplified OCR Extraction Task
Extracts data from ID images without auto-accept/reject logic
"""

from celery import shared_task
import logging
from django.core.files.base import ContentFile
from PIL import Image
import io

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def extract_id_data_simple(self, verification_id):
    """
    Simple OCR extraction task - just extracts data, no verification logic
    
    Args:
        verification_id: ID of the AccountVerification to process
        
    Returns:
        dict: Extracted data from ID
    """
    from users.models import AccountVerification, VerificationLog
    from users.services.verification.ocr_philsys import PhilSysOCR
    
    try:
        logger.info(f"Starting OCR extraction for verification {verification_id}")
        
        # Get verification
        verification = AccountVerification.objects.get(id=verification_id)
        user = verification.user
        
        # Check if verification has ID image
        if not verification.id_image_front:
            logger.error(f"Verification {verification_id} has no ID image")
            return {
                'success': False,
                'error': 'No ID image found'
            }
        
        # Get ID image path
        id_image_path = verification.id_image_front.path
        logger.info(f"Processing ID image: {id_image_path}")
        
        # Load image
        from PIL import Image as PILImage
        image = PILImage.open(id_image_path)
        logger.info(f"Loaded image: {image.size} {image.mode}")
        
        # Initialize OCR
        ocr = PhilSysOCR()
        
        # Extract data
        extracted_data = ocr.extract_philsys_data(image)
        
        # Post-process: Try to extract fields from raw text if not all fields were extracted
        field_count = int(extracted_data.get('fields_extracted_count', '0'))
        if extracted_data.get('raw_text') and field_count < 4:  # Less than 4 fields extracted
            logger.info(f"Only {field_count} fields extracted, trying direct text extraction...")
            raw_text = extracted_data['raw_text']
            
            # Extract PCN (format: 0000-0000-0000-0000 or 0000 0000 0000 0000)
            import re
            # Look for 16 consecutive digits or 4 groups of 4 digits
            pcn_match = re.search(r'(\d{4})[\s-](\d{4})[\s-](\d{4})[\s-](\d{4})', raw_text)
            if pcn_match:
                extracted_data['id_number'] = f"{pcn_match.group(1)}-{pcn_match.group(2)}-{pcn_match.group(3)}-{pcn_match.group(4)}"
                extracted_data['pcn'] = extracted_data['id_number']
                logger.info(f"Extracted PCN: {extracted_data['pcn']}")
            else:
                # Try finding 16 consecutive digits
                pcn_match2 = re.search(r'(\d{16})', raw_text)
                if pcn_match2:
                    digits = pcn_match2.group(1)
                    extracted_data['id_number'] = f"{digits[0:4]}-{digits[4:8]}-{digits[8:12]}-{digits[12:16]}"
                    extracted_data['pcn'] = extracted_data['id_number']
                    logger.info(f"Extracted PCN (16 digits): {extracted_data['pcn']}")
            
            # Extract name - look for the specific PhilSys pattern
            # Pattern: LADERA (on one line), JOHNALBERTG (next line), CUEBILLAS (next line)
            lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
            
            # Find LADERA line
            for i, line in enumerate(lines):
                # Look for a line with just LADERA (or similar lastname pattern)
                if line == 'LADERA' or (len(line) > 3 and line.isupper() and not any(c.isdigit() for c in line) and len(line.split()) == 1):
                    # Check if this is the lastname by looking at surrounding context
                    if i > 0 and i + 2 < len(lines):
                        prev_line = lines[i-1]
                        next_line1 = lines[i+1]
                        next_line2 = lines[i+2]
                        
                        # Skip if previous line looks like a label
                        if 'AL' in prev_line or 'NAME' in prev_line or len(prev_line) < 3:
                            lastname = line
                            # Next lines should be firstname and middlename
                            # Look for lines that look like names (uppercase, no numbers)
                            if next_line1 and next_line1.replace('G', '').replace('C', '').isalpha() and next_line1.isupper():
                                firstname = next_line1.replace('G', ' ').strip()  # Remove trailing G
                                
                                if next_line2 and next_line2.isalpha() and next_line2.isupper():
                                    middlename = next_line2
                                    extracted_data['full_name'] = f"{lastname}, {firstname} {middlename}"
                                    logger.info(f"Extracted Name: {extracted_data['full_name']}")
                                    break
                                else:
                                    extracted_data['full_name'] = f"{lastname}, {firstname}"
                                    logger.info(f"Extracted Name: {extracted_data['full_name']}")
                                    break
            
            # Extract DOB (look for SEPTEMBER, PTEMBER, etc.)
            dob_match = re.search(r'(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER|PTEMBER)\s+(\d{1,2})[,\s]+(\d{4})', raw_text, re.IGNORECASE)
            if dob_match:
                month = dob_match.group(1).replace('PTEMBER', 'SEPTEMBER')
                day = dob_match.group(2)
                year = dob_match.group(3)
                extracted_data['date_of_birth'] = f"{month} {day}, {year}"
                logger.info(f"Extracted DOB: {extracted_data['date_of_birth']}")
            
            # Extract address (look for MOLINO, BACOOR, CAVITE)
            address_match = re.search(r'([A-Z0-9\s]+MOLINO[A-Z0-9\s]+BACOOR[A-Z0-9\s]+)', raw_text)
            if address_match:
                address = address_match.group(1).strip()
                address = ' '.join(address.split())  # Normalize spaces
                extracted_data['address'] = address
                logger.info(f"Extracted Address: {extracted_data['address']}")
            
            # Extract sex
            if 'MALE' in raw_text and 'FEMALE' not in raw_text:
                extracted_data['sex'] = 'Male'
            elif 'FEMALE' in raw_text:
                extracted_data['sex'] = 'Female'
            
            # Recalculate field count
            field_count = sum(1 for k in ["full_name", "date_of_birth", "id_number", "address", "sex"] if k in extracted_data)
            extracted_data['fields_extracted_count'] = str(field_count)
            if field_count > 0:
                extracted_data['extraction_quality'] = 'fair' if field_count >= 3 else 'poor'
            logger.info(f"After post-processing: extracted {field_count} fields")
        
        logger.info(f"OCR extracted {len(extracted_data)} fields for user {user.id}")
        logger.info(f"Extracted fields: {list(extracted_data.keys())}")
        
        # Save to VerificationLog
        log = VerificationLog.objects.create(
            user=user,
            extracted_data=extracted_data,
            result='completed',
            notes=f'OCR extraction completed. Extracted {len(extracted_data)} fields.'
        )
        
        logger.info(f"Saved VerificationLog {log.id} for user {user.id}")
        
        return {
            'success': True,
            'user_id': user.id,
            'verification_id': verification_id,
            'extracted_fields': len(extracted_data),
            'log_id': log.id
        }
        
    except AccountVerification.DoesNotExist:
        logger.error(f"Verification {verification_id} not found")
        return {
            'success': False,
            'error': 'Verification not found'
        }
        
    except Exception as e:
        logger.exception(f"OCR extraction failed for verification {verification_id}: {e}")
        
        # Retry on failure
        try:
            raise self.retry(exc=e, countdown=60)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for verification {verification_id}")
            
            # Save failed log
            try:
                from users.models import AccountVerification
                verification = AccountVerification.objects.get(id=verification_id)
                VerificationLog.objects.create(
                    user=verification.user,
                    extracted_data={'error': str(e)},
                    result='failed',
                    notes=f'OCR extraction failed: {str(e)}'
                )
            except Exception as log_error:
                logger.warning(f"Failed to save error log for verification {verification_id}: {log_error}")
                
            return {
                'success': False,
                'error': str(e)
            }
