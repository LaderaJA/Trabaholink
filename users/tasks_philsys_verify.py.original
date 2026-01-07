"""
PhilSys web verification task using https://verify.philsys.gov.ph/
This runs AFTER OCR extraction and data validation passes.
"""
from celery import shared_task
from typing import Dict, Any, Optional
import logging
import requests
from datetime import datetime

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=2)
def verify_philsys_web(self, user_id: int, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify PhilSys ID using the official government verification portal.
    
    This is step 3 of verification (after OCR extraction and data validation).
    
    Args:
        user_id: User ID
        extracted_data: Data extracted from OCR
    
    Returns:
        Dict with verification result
    """
    from users.models import CustomUser
    from users.services.verification.progress_tracker import VerificationProgressTracker
    
    tracker = VerificationProgressTracker(user_id)
    
    try:
        user = CustomUser.objects.get(pk=user_id)
        tracker.update("philsys_verification", 85, "Connecting to PhilSys verification portal...")
        
        # Extract required fields
        pcn = extracted_data.get('pcn', '')
        full_name = extracted_data.get('full_name', '')
        date_of_birth = extracted_data.get('date_of_birth', '')
        
        if not pcn:
            logger.warning(f"No PCN found for user {user_id}, skipping PhilSys web verification")
            return {
                'success': False,
                'verified': False,
                'reason': 'No PCN extracted from ID',
                'skipped': True
            }
        
        # Check if user has consented to PhilSys verification
        if not getattr(user, 'philsys_verification_consent', False):
            logger.info(f"User {user_id} has not consented to PhilSys web verification")
            return {
                'success': True,
                'verified': None,
                'reason': 'User has not consented to web verification',
                'skipped': True
            }
        
        tracker.update("philsys_verification", 87, "Submitting verification request...")
        
        # Perform PhilSys web verification
        verification_result = verify_with_philsys_portal(
            pcn=pcn,
            full_name=full_name,
            date_of_birth=date_of_birth
        )
        
        tracker.update("philsys_verification", 95, "Processing verification response...")
        
        # Log the result
        logger.info(
            f"PhilSys web verification for user {user_id}: "
            f"verified={verification_result.get('verified')}, "
            f"confidence={verification_result.get('confidence')}"
        )
        
        result = {
            'success': True,
            'user_id': user_id,
            'verified': verification_result.get('verified', False),
            'confidence': verification_result.get('confidence', 0.0),
            'response_data': verification_result.get('response_data', {}),
            'verified_at': datetime.now().isoformat(),
            'reason': verification_result.get('reason', '')
        }
        
        tracker.update("philsys_verification", 100, "PhilSys verification completed")
        
        return result
        
    except Exception as e:
        logger.exception(f"PhilSys web verification failed for user {user_id}")
        tracker.error(f"PhilSys verification failed: {str(e)}")
        return {
            'success': False,
            'user_id': user_id,
            'verified': False,
            'error': str(e)
        }


def verify_with_philsys_portal(
    pcn: str,
    full_name: str,
    date_of_birth: str,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Verify PhilSys ID with the official government portal.
    
    Args:
        pcn: PhilSys Card Number (0000-0000-0000-0000)
        full_name: Full name as on ID
        date_of_birth: Date of birth
        timeout: Request timeout in seconds
    
    Returns:
        Dict with verification result
    """
    PHILSYS_VERIFY_URL = "https://verify.philsys.gov.ph/api/verify"
    
    try:
        # Prepare verification payload
        payload = {
            'pcn': pcn,
            'full_name': full_name.upper(),
            'date_of_birth': normalize_date_for_api(date_of_birth)
        }
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'TrabahoLink-Verification/1.0',
            'Accept': 'application/json'
        }
        
        logger.info(f"Sending PhilSys verification request for PCN: {pcn[:4]}****{pcn[-4:]}")
        
        # Make API request
        response = requests.post(
            PHILSYS_VERIFY_URL,
            json=payload,
            headers=headers,
            timeout=timeout,
            verify=True  # Verify SSL certificate
        )
        
        # Check response status
        if response.status_code == 200:
            data = response.json()
            
            # Parse response
            is_verified = data.get('verified', False)
            confidence = data.get('confidence', 0.0)
            
            return {
                'verified': is_verified,
                'confidence': confidence,
                'response_data': data,
                'reason': data.get('message', 'Verification completed')
            }
        
        elif response.status_code == 404:
            # PCN not found in PhilSys database
            return {
                'verified': False,
                'confidence': 0.0,
                'response_data': {},
                'reason': 'PCN not found in PhilSys database'
            }
        
        elif response.status_code == 400:
            # Invalid request
            return {
                'verified': False,
                'confidence': 0.0,
                'response_data': {},
                'reason': 'Invalid verification request format'
            }
        
        else:
            # Other error
            logger.error(f"PhilSys API returned status {response.status_code}: {response.text}")
            return {
                'verified': False,
                'confidence': 0.0,
                'response_data': {},
                'reason': f'API error: {response.status_code}'
            }
    
    except requests.exceptions.Timeout:
        logger.error("PhilSys verification request timed out")
        return {
            'verified': False,
            'confidence': 0.0,
            'response_data': {},
            'reason': 'Verification request timed out'
        }
    
    except requests.exceptions.ConnectionError:
        logger.error("Failed to connect to PhilSys verification portal")
        return {
            'verified': False,
            'confidence': 0.0,
            'response_data': {},
            'reason': 'Could not connect to verification portal'
        }
    
    except Exception as e:
        logger.exception("PhilSys verification request failed")
        return {
            'verified': False,
            'confidence': 0.0,
            'response_data': {},
            'reason': f'Verification error: {str(e)}'
        }


def normalize_date_for_api(date_str: str) -> str:
    """
    Normalize date string to format expected by PhilSys API (YYYY-MM-DD).
    
    Handles various input formats:
    - MM/DD/YYYY
    - DD/MM/YYYY
    - Month DD, YYYY
    - YYYY-MM-DD
    """
    import re
    from dateutil import parser
    
    if not date_str:
        return ''
    
    try:
        # Try to parse the date
        parsed_date = parser.parse(date_str, fuzzy=True)
        return parsed_date.strftime('%Y-%m-%d')
    except (ValueError, TypeError, AttributeError):
        # If parsing fails, try regex patterns
        # Pattern: YYYY-MM-DD
        match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', date_str)
        if match:
            return f"{match.group(1)}-{match.group(2).zfill(2)}-{match.group(3).zfill(2)}"
        
        # Pattern: MM/DD/YYYY
        match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', date_str)
        if match:
            return f"{match.group(3)}-{match.group(1).zfill(2)}-{match.group(2).zfill(2)}"
        
        # Return as-is if can't parse
        logger.warning(f"Could not normalize date: {date_str}")
        return date_str
