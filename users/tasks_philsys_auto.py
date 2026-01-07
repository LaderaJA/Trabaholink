"""
Automatic PhilSys verification task with retry logic and auto-decision.
Runs when a PhilSys ID is submitted and automatically verifies with government portal.
"""
from celery import shared_task
import logging
from typing import Dict, Any
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger(__name__)


@shared_task
def scan_pending_philsys_verifications():
    """
    Scan all pending PhilSys verifications and queue them for auto-verification.
    This runs on Celery startup and can be scheduled periodically.
    """
    from users.models import AccountVerification, CustomUser
    
    logger.info("Scanning for pending PhilSys verifications...")
    
    # Find all pending verifications with PhilSys ID type
    pending_verifications = AccountVerification.objects.filter(
        status='pending',
        id_type='philsys',
        id_image_back__isnull=False
    ).select_related('user')
    
    count = pending_verifications.count()
    logger.info(f"Found {count} pending PhilSys verifications")
    
    queued = 0
    for verification in pending_verifications:
        try:
            # Check if already processed (has PhilSys data in log)
            from users.models import VerificationLog
            existing_log = VerificationLog.objects.filter(
                user=verification.user,
                extracted_data__has_key='philsys_web'
            ).exists()
            
            if existing_log:
                logger.info(f"Verification {verification.id} already has PhilSys data, skipping")
                continue
            
            # Queue for auto-verification
            logger.info(f"Queueing auto-verification for verification {verification.id} (user: {verification.user.username})")
            auto_verify_philsys.delay(verification_id=verification.id)
            queued += 1
            
        except Exception as e:
            logger.error(f"Error queueing verification {verification.id}: {e}")
    
    logger.info(f"Queued {queued} PhilSys verifications for auto-processing")
    
    return {
        'total_pending': count,
        'queued': queued,
        'skipped': count - queued
    }


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=1800,  # Max 30 minutes between retries
    max_retries=5,  # Retry up to 5 times for network issues
)
def auto_verify_philsys(self, verification_id: int) -> Dict[str, Any]:
    """
    Automatically verify PhilSys ID with government portal and auto-accept/reject.
    
    Flow:
    1. Check if ID type is PhilSys
    2. Upload ID back image to verify.philsys.gov.ph
    3. Extract data from verification result
    4. Compare with user's form input
    5. Auto-accept if match, auto-reject if mismatch
    6. Retry if portal is down/busy
    
    Args:
        verification_id: AccountVerification ID
        
    Returns:
        Dict with verification result
    """
    from users.models import AccountVerification, VerificationLog, CustomUser
    from notifications.models import Notification
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    import re
    
    try:
        verification = AccountVerification.objects.get(id=verification_id)
        user = verification.user
        
        logger.info(f"Starting auto PhilSys verification for user {user.id}, verification {verification_id}")
        
        # Check if this is a PhilSys ID
        if verification.id_type != 'philsys':
            logger.info(f"Verification {verification_id} ID type is {verification.id_type}, skipping PhilSys verification")
            return {
                'success': True,
                'skipped': True,
                'reason': 'Not a PhilSys ID'
            }
        
        # Check if ID back image exists
        if not verification.id_image_back:
            logger.warning(f"Verification {verification_id} has no ID back image")
            return {
                'success': False,
                'error': 'No ID back image found'
            }
        
        id_back_path = verification.id_image_back.path
        
        # Check file size
        import os
        if os.path.exists(id_back_path):
            file_size = os.path.getsize(id_back_path)
            file_size_mb = file_size / (1024 * 1024)
            logger.info(f"ID back image path: {id_back_path}, size: {file_size_mb:.2f} MB")
            
            # If file is too large (>10MB), log warning
            if file_size_mb > 10:
                logger.warning(f"Large file size ({file_size_mb:.2f} MB) may cause upload timeout")
        else:
            logger.error(f"ID back image file not found: {id_back_path}")
            return {
                'success': False,
                'verified': False,
                'data': {},
                'retry_later': False,
                'error': 'ID back image file not found'
            }
        
        # NEW: Use offline verification (QR + OCR + Face matching)
        # No longer uses Playwright automation to comply with verify.philsys.gov.ph terms
        from users.verification_new import verify_philsys_id_offline
        
        # Prepare user data for comparison
        user_data = {
            'full_name': verification.full_name or user.get_full_name(),
            'date_of_birth': verification.date_of_birth,
            'gender': verification.gender,
            'address': getattr(user, 'address', None) or verification.notes,
        }
        
        # Get paths
        id_front_path = verification.id_image_front.path if verification.id_image_front else None
        selfie_path = verification.selfie_image.path if verification.selfie_image else None
        
        if not id_front_path or not selfie_path:
            logger.error(f"Missing required images: front={bool(id_front_path)}, selfie={bool(selfie_path)}")
            verification.status = 'pending'
            verification.save()
            return {
                'success': False,
                'error': 'Missing required images (front or selfie)'
            }
        
        # Run offline verification
        philsys_result = verify_philsys_id_offline(
            id_front_path=id_front_path,
            id_back_path=id_back_path,
            selfie_path=selfie_path,
            user_data=user_data
        )
        
        # Check if verification failed
        # Note: No more retry_later since we're not using portal automation
        
        # If verification failed
        if not philsys_result['success']:
            logger.error(f"Offline verification failed: {philsys_result.get('error')}")
            # Mark for manual review
            verification.status = 'pending'
            verification.save()
            
            # Create log
            VerificationLog.objects.create(
                user=user,
                extracted_data={'offline_verification': philsys_result},
                process_type='auto',
                result='manual_review',
                notes=f"Offline auto-verification failed: {philsys_result.get('error')}"
            )
            
            return philsys_result
        
        # Get decision from offline verification
        decision = philsys_result.get('decision', 'pending')
        overall_score = philsys_result.get('overall_score', 0.0)
        
        # Build match result for logging
        match_result = {
            'overall_match': decision == 'approved',
            'match_score': overall_score,
            'matches': philsys_result.get('matches', []),
            'mismatches': philsys_result.get('mismatches', []),
            'match_summary': f"Score: {overall_score:.1%}, Face: {philsys_result.get('face_match_score', 0):.1%}, Data: {philsys_result.get('data_match_score', 0):.1%}",
            'mismatch_details': ', '.join(philsys_result.get('mismatches', []))
        }
        
        # Save offline verification data to log
        log = VerificationLog.objects.filter(user=user).order_by('-created_at').first()
        if log:
            log.extracted_data = log.extracted_data or {}
            log.extracted_data['offline_verification'] = philsys_result
            log.extracted_data['match_result'] = match_result
            log.save()
        else:
            log = VerificationLog.objects.create(
                user=user,
                extracted_data={
                    'offline_verification': philsys_result,
                    'match_result': match_result
                },
                process_type='auto',
                result='pending',
                notes='Offline auto-verification completed (QR + OCR + Face)'
            )
        
        # Auto-decision based on score and decision
        if decision == 'approved':
            # AUTO-ACCEPT
            logger.info(f"Auto-accepting verification {verification_id} - data matches")
            
            with transaction.atomic():
                verification.status = 'approved'
                verification.reviewed_at = timezone.now()
                verification.save(update_fields=['status', 'reviewed_at'])
                
                user.identity_verification_status = 'verified'
                user.verification_status = 'verified'  # Fix conflicting status
                user.is_verified = True
                user.is_verified_philsys = True
                user.save(update_fields=['identity_verification_status', 'verification_status', 'is_verified', 'is_verified_philsys'])
                
                log.result = 'verified'
                log.notes += f"\n\nAuto-approved: {match_result['match_summary']}"
                log.save(update_fields=['result', 'notes'])
                
                # Notify user
                Notification.objects.create(
                    user=user,
                    message=f"✅ Your PhilSys ID has been verified! Verification score: {overall_score:.0%}. Your account is now verified.",
                    notif_type="verification_approved"
                )
            
            return {
                'success': True,
                'decision': 'approved',
                'match_score': match_result['match_score'],
                'reason': match_result['match_summary']
            }
        
        elif decision == 'rejected':
            # AUTO-REJECT
            logger.info(f"Auto-rejecting verification {verification_id} - low score: {overall_score:.1%}")
            
            with transaction.atomic():
                verification.status = 'rejected'
                verification.rejection_reason = f"Data mismatch: {match_result['mismatch_details']}"
                verification.reviewed_at = timezone.now()
                verification.save(update_fields=['status', 'rejection_reason', 'reviewed_at'])
                
                user.identity_verification_status = 'failed'
                user.verification_status = 'failed'  # Fix conflicting status
                user.save(update_fields=['identity_verification_status', 'verification_status'])
                
                log.result = 'failed'
                log.notes += f"\n\nAuto-rejected: {match_result['mismatch_details']}"
                log.save(update_fields=['result', 'notes'])
                
                # Notify user
                Notification.objects.create(
                    user=user,
                    message=f"❌ ID Verification Failed: Verification score too low ({overall_score:.0%}). Issues: {match_result['mismatch_details']}. Please ensure your photos are clear and information is correct, then submit a new verification request.",
                    notif_type="verification_rejected"
                )
            
            return {
                'success': True,
                'decision': 'rejected',
                'match_score': match_result['match_score'],
                'reason': match_result['mismatch_details']
            }
        
    except AccountVerification.DoesNotExist:
        logger.error(f"Verification {verification_id} not found")
        return {
            'success': False,
            'error': 'Verification not found'
        }
    
    except Exception as e:
        logger.exception(f"Auto PhilSys verification failed for {verification_id}: {e}")
        
        # Check if this is a retryable error
        if 'timeout' in str(e).lower() or 'network' in str(e).lower() or 'connection' in str(e).lower():
            logger.warning(f"Network error, will retry: {e}")
            raise self.retry(countdown=300)  # Retry after 5 minutes
        
        # Non-retryable error - mark for manual review
        try:
            verification = AccountVerification.objects.get(id=verification_id)
            verification.status = 'pending'
            verification.save()
        except AccountVerification.DoesNotExist:
            logger.warning(f"Verification {verification_id} not found when trying to mark for manual review")
        
        return {
            'success': False,
            'error': str(e)
        }

# 
# # def verify_with_philsys_portal(id_back_path: str, user_id: int) -> Dict[str, Any]:
# #     """
# #     Verify ID with PhilSys government portal using Playwright.
# #     
# #     Returns:
# #         Dict with success, data, and retry_later flag
# #     """
# #     from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
# #     import re
# #     
# #     result = {
# #         'success': False,
# #         'verified': False,
# #         'data': {},
# #         'retry_later': False,
# #         'error': None
# #     }
# #     
# #     try:
# #         with sync_playwright() as p:
# #             browser = p.chromium.launch(headless=True)
# #             context = browser.new_context(
# #                 viewport={'width': 1920, 'height': 1080},
# #                 user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
# #             )
# #             page = context.new_page()
# #             
# #             logger.info("Navigating to PhilSys portal...")
# #             
# #             # Navigate with retry
# #             try:
# #                 page.goto('https://verify.philsys.gov.ph/', wait_until='load', timeout=60000)
# #             except PlaywrightTimeout:
# #                 try:
# #                     page.goto('https://verify.philsys.gov.ph/', wait_until='domcontentloaded', timeout=60000)
# #                 except Exception as e:
# #                     logger.error(f"Portal navigation failed: {e}")
# #                     browser.close()
# #                     result['retry_later'] = True
# #                     result['error'] = 'PhilSys portal is unreachable or down'
# #                     return result
# #             
# #             page.wait_for_load_state('domcontentloaded')
# #             page.wait_for_timeout(2000)
# #             
# #             # Click scan image
# #             try:
# #                 scan_image = page.locator('img[alt="scan-image"].scanImg')
# #                 if scan_image.count() == 0:
# #                     scan_image = page.locator('img[src*="scan2.png"]')
# #                 scan_image.click()
# #                 page.wait_for_timeout(1000)
# #             except Exception as e:
# #                 logger.error(f"Failed to click scan image: {e}")
# #                 browser.close()
# #                 result['error'] = 'Portal UI changed or unavailable'
# #                 result['retry_later'] = True
# #                 return result
# #             
# #             # Click Camera button
# #             try:
# #                 camera_button = page.locator('button.swal2-confirm:has-text("Camera")')
# #                 if camera_button.count() == 0:
# #                     camera_button = page.locator('button.swal2-confirm.swal2-styled')
# #                 camera_button.click()
# #                 page.wait_for_timeout(2000)
# #             except Exception as e:
# #                 logger.error(f"Failed to click Camera: {e}")
# #                 browser.close()
# #                 result['error'] = 'Portal UI changed'
# #                 result['retry_later'] = True
# #                 return result
# #             
# #             # Click "Scan an Image File"
# #             try:
# #                 scan_file_link = page.locator('#reader__dashboard_section_swaplink')
# #                 if scan_file_link.count() == 0:
# #                     scan_file_link = page.locator('a[href="#scan-using-file"]')
# #                 scan_file_link.click()
# #                 page.wait_for_timeout(1000)
# #             except Exception as e:
# #                 logger.error(f"Failed to click scan file link: {e}")
# #                 browser.close()
# #                 result['error'] = 'Portal UI changed'
# #                 result['retry_later'] = True
# #                 return result
# #             
# #             # Upload file
# #             try:
# #                 logger.info(f"Looking for file upload input...")
# #                 upload_input = page.locator('#reader__filescan_input')
# #                 if upload_input.count() == 0:
# #                     upload_input = page.locator('input[type="file"][accept="image/*"]')
# #                 
# #                 logger.info(f"Uploading file: {id_back_path}")
# #                 # Increase timeout to 60 seconds for slow uploads
# #                 upload_input.set_input_files(id_back_path, timeout=60000)
# #                 logger.info(f"File uploaded, waiting for processing...")
# #                 page.wait_for_timeout(5000)
# #             except Exception as e:
# #                 logger.error(f"Failed to upload file: {e}")
# #                 # Take screenshot for debugging
# #                 try:
# #                     page.screenshot(path=f'/tmp/philsys_upload_error_{user_id}.png', full_page=True)
# #                     logger.info(f"Error screenshot saved to /tmp/philsys_upload_error_{user_id}.png")
# #                 except:
# #                     pass
# #                 browser.close()
# #                 result['error'] = f'File upload failed: {str(e)}'
# #                 return result
# #             
# #             # Wait for result to load
# #             page.wait_for_timeout(3000)
# #             
# #             # Check for verification result using better selectors
# #             page_text = page.inner_text('body')
# #             
# #             logger.info(f"PhilSys portal response preview: {page_text[:500]}")
# #             
# #             # Check if verified
# #             if 'verified' in page_text.lower() or 'valid' in page_text.lower():
# #                 result['verified'] = True
# #                 result['success'] = True
# #                 
# #                 # Extract all data fields using Playwright selectors
# #                 result['data'] = extract_philsys_data_from_page(page)
# #                 
# #                 logger.info(f"PhilSys verification successful for user {user_id}")
# #                 logger.info(f"Extracted data: {result['data']}")
# #             else:
# #                 result['verified'] = False
# #                 result['success'] = True
# #                 result['error'] = 'ID not verified by portal'
# #             
# #             # Take screenshot for debugging
# #             try:
# #                 screenshot_path = f'/tmp/philsys_auto_{user_id}_{datetime.now().strftime("%Y%m%d%H%M%S")}.png'
# #                 page.screenshot(path=screenshot_path, full_page=True)
# #                 if 'data' not in result:
# #                     result['data'] = {}
# #                 result['data']['screenshot'] = screenshot_path
# #                 logger.info(f"Screenshot saved to: {screenshot_path}")
# #             except Exception as e:
# #                 logger.warning(f"Failed to save screenshot: {e}")
# #             
# #             browser.close()
# #             
# #     except PlaywrightTimeout as e:
# #         logger.error(f"Playwright timeout: {e}")
# #         result['retry_later'] = True
# #         result['error'] = 'Portal timeout - will retry'
# #     
# #     except Exception as e:
# #         logger.exception(f"PhilSys portal verification error: {e}")
# #         result['error'] = str(e)
# #         # Check if it's a network issue
# #         if 'network' in str(e).lower() or 'connection' in str(e).lower():
# #             result['retry_later'] = True
# #     
# #     return result
# # 
# # 
# def extract_philsys_data_from_page(page) -> Dict[str, str]:
#     """
#     Extract PhilSys data from verification page using Playwright selectors.
#     This is more reliable than regex on HTML.
#     """
#     import re
#     
#     data = {}
#     
#     try:
#         # Get the full text content of the page
#         page_text = page.inner_text('body')
#         
#         # Use regex on clean text (not HTML)
#         patterns = {
#             'last_name': r'Last\s*Name[:\s]*([^\n]+)',
#             'first_name': r'First\s*Name[:\s]*([^\n]+)',
#             'middle_name': r'Middle\s*Name[:\s]*([^\n]+)',
#             'suffix': r'Suffix[:\s]*([^\n]+?)(?:\s*SEX:|$)',  # Stop at SEX: or end of line
#             'sex': r'(?:SEX|Sex)[:\s]*([^\n]+)',
#             'date_of_birth': r'Date\s*of\s*Birth[:\s]*([^\n]+)',
#             'place_of_birth': r'Place\s*of\s*Birth[:\s]*([^\n]+)',
#             'pcn': r'(?:Philsys\s*Card\s*Number|PCN)[:\s]*([0-9\-]+)',
#             'date_of_issuance': r'Date\s*of\s*Issuance[:\s]*([^\n]+)',
#         }
#         
#         for field, pattern in patterns.items():
#             match = re.search(pattern, page_text, re.IGNORECASE)
#             if match:
#                 value = match.group(1).strip()
#                 # Clean up the value
#                 value = re.sub(r'\s+', ' ', value)  # Normalize whitespace
#                 
#                 # Additional cleanup for suffix field
#                 if field == 'suffix':
#                     # Remove "SEX:" and anything after it if it got captured
#                     value = re.sub(r'\s*SEX:.*$', '', value, flags=re.IGNORECASE)
#                     value = value.strip()
#                 
#                 if value and value not in ['', '-', 'N/A']:
#                     data[field] = value
#                     logger.info(f"Extracted {field}: {value}")
#         
#         # Construct full name properly (without including suffix if it's empty or contains SEX)
#         if data.get('first_name') and data.get('last_name'):
#             name_parts = [data['last_name'], data['first_name']]
#             if data.get('middle_name'):
#                 name_parts.append(data['middle_name'])
#             # Only add suffix if it's a real suffix (not empty and doesn't contain SEX)
#             if data.get('suffix') and 'SEX' not in data['suffix'].upper():
#                 name_parts.append(data['suffix'])
#             data['name'] = ', '.join([name_parts[0], ' '.join(name_parts[1:])])
#             logger.info(f"Constructed full name: {data['name']}")
#         
#         return data
#         
#     except Exception as e:
#         logger.error(f"Error extracting PhilSys data from page: {e}")
#         return {}
# 
# 
# def extract_philsys_data(page_html: str) -> Dict[str, str]:
#     """
#     DEPRECATED: Extract all PhilSys data fields from verification result HTML.
#     Use extract_philsys_data_from_page instead for better reliability.
#     """
#     import re
#     
#     data = {}
#     
#     # Extract each field using regex
#     fields = {
#         'last_name': r'<strong>Last Name:\s*</strong>([^<]*)',
#         'first_name': r'<strong>First Name:\s*</strong>([^<]*)',
#         'middle_name': r'<strong>Middle Name:\s*</strong>([^<]*)',
#         'suffix': r'<strong>Suffix:\s*</strong>([^<]*)',
#         'sex': r'<strong>Sex:\s*</strong>([^<]*)',
#         'date_of_birth': r'<strong>Date of Birth:\s*</strong>([^<]*)',
#         'place_of_birth': r'<strong>Place of Birth:\s*</strong>([^<]*)',
#         'pcn': r'<strong>Philsys Card Number \(PCN\):\s*</strong>([^<]*)',
#         'date_of_issuance': r'<strong>Date of Issuance:\s*</strong>([^<]*)',
#         'best_capture_finger': r'<strong>Best Capture Finger:\s*</strong>([^<]*)',
#     }
#     
#     for field, pattern in fields.items():
#         match = re.search(pattern, page_html, re.IGNORECASE)
#         if match:
#             value = match.group(1).strip()
#             if value:
#                 data[field] = value
#     
#     # Construct full name
#     if data.get('first_name') and data.get('last_name'):
#         name_parts = [data['last_name'], data['first_name']]
#         if data.get('middle_name'):
#             name_parts.append(data['middle_name'])
#         if data.get('suffix'):
#             name_parts.append(data['suffix'])
#         data['name'] = ', '.join([name_parts[0], ' '.join(name_parts[1:])])
#     
#     return data
# 
# 
# def compare_verification_data(user, verification, verified_data: Dict[str, str]) -> Dict[str, Any]:
#     """
#     Compare user's form input with PhilSys verified data.
#     
#     Returns match result with score and details.
#     """
#     matches = []
#     mismatches = []
#     
#     # Compare full name (most important)
#     if verified_data.get('name'):
#         user_name = verification.full_name or user.get_full_name()
#         verified_name = verified_data['name']
#         
#         logger.info(f"Comparing names:")
#         logger.info(f"  User name: '{user_name}'")
#         logger.info(f"  Verified name: '{verified_name}'")
#         
#         # Calculate similarity on full names
#         name_similarity = calculate_similarity(user_name.upper(), verified_name.upper())
#         logger.info(f"  Full name similarity: {name_similarity:.2%}")
#         
#         # Also check component-by-component (more lenient for middle initials)
#         user_name_clean = normalize_name_for_comparison(user_name)
#         verified_name_clean = normalize_name_for_comparison(verified_name)
#         
#         component_similarity = calculate_similarity(user_name_clean, verified_name_clean)
#         logger.info(f"  Component similarity: {component_similarity:.2%}")
#         
#         # Accept if either full name or component comparison passes
#         best_similarity = max(name_similarity, component_similarity)
#         
#         if best_similarity >= 0.75:  # 75% match threshold (more lenient)
#             matches.append(f"Name matches ({int(best_similarity*100)}%)")
#             logger.info(f"  ✅ Name matches!")
#         else:
#             mismatches.append(f"Name mismatch: '{user_name}' vs '{verified_name}'")
#             logger.info(f"  ❌ Name mismatch!")
#     
#     # Compare date of birth
#     if verified_data.get('date_of_birth') and verification.date_of_birth:
#         user_dob = str(verification.date_of_birth)
#         verified_dob = verified_data['date_of_birth']
#         
#         logger.info(f"Comparing dates of birth:")
#         logger.info(f"  User DOB: '{user_dob}'")
#         logger.info(f"  Verified DOB: '{verified_dob}'")
#         
#         # Normalize dates for comparison
#         normalized_user_dob = normalize_date(user_dob)
#         normalized_verified_dob = normalize_date(verified_dob)
#         logger.info(f"  Normalized User DOB: '{normalized_user_dob}'")
#         logger.info(f"  Normalized Verified DOB: '{normalized_verified_dob}'")
#         
#         if normalized_user_dob == normalized_verified_dob:
#             matches.append("Date of birth matches")
#             logger.info(f"  ✅ DOB matches!")
#         else:
#             mismatches.append(f"DOB mismatch: '{user_dob}' vs '{verified_dob}'")
#             logger.info(f"  ❌ DOB mismatch!")
#     
#     # Compare sex/gender
#     if verified_data.get('sex') and verification.gender:
#         user_sex = verification.gender.lower()
#         verified_sex = verified_data['sex'].lower()
#         
#         logger.info(f"Comparing gender:")
#         logger.info(f"  User gender: '{user_sex}'")
#         logger.info(f"  Verified gender: '{verified_sex}'")
#         
#         if user_sex in verified_sex or verified_sex in user_sex:
#             matches.append("Gender matches")
#             logger.info(f"  ✅ Gender matches!")
#         else:
#             mismatches.append(f"Gender mismatch: '{user_sex}' vs '{verified_sex}'")
#             logger.info(f"  ❌ Gender mismatch!")
#     
#     # Calculate match score
#     total_checks = len(matches) + len(mismatches)
#     match_score = len(matches) / total_checks if total_checks > 0 else 0
#     
#     # Decision: Accept if at least 2 out of 3 key fields match (name, DOB, gender)
#     # Name is weighted more heavily
#     overall_match = len(matches) >= 2 and len(mismatches) == 0
#     
#     logger.info(f"=== VERIFICATION DECISION ===")
#     logger.info(f"Total matches: {len(matches)}")
#     logger.info(f"Total mismatches: {len(mismatches)}")
#     logger.info(f"Match score: {match_score:.2%}")
#     logger.info(f"Overall match: {overall_match}")
#     
#     if overall_match:
#         logger.info(f"✅ DECISION: AUTO-APPROVE")
#     else:
#         logger.info(f"❌ DECISION: AUTO-REJECT")
#         logger.info(f"Reason: {', '.join(mismatches) if mismatches else 'Insufficient matches'}")
#     
#     return {
#         'overall_match': overall_match,
#         'match_score': match_score,
#         'matches': matches,
#         'mismatches': mismatches,
#         'match_summary': ', '.join(matches) if matches else 'No matches',
#         'mismatch_details': ', '.join(mismatches) if mismatches else 'No mismatches'
#     }
# 
# 
# def calculate_similarity(str1: str, str2: str) -> float:
#     """Calculate similarity ratio between two strings."""
#     return SequenceMatcher(None, str1, str2).ratio()
# 
# 
# def normalize_name_for_comparison(name: str) -> str:
#     """
#     Normalize a name for better comparison.
#     Handles middle name initials vs full middle names.
#     
#     Example:
#     - "LADERA, John Albert C." -> "LADERA JOHN ALBERT C"
#     - "LADERA, JOHN ALBERT CUEBILLAS" -> "LADERA JOHN ALBERT CUEBILLAS"
#     
#     This allows "C." to match "CUEBILLAS" by comparing first/last + first letter of middle.
#     """
#     import re
#     
#     # Remove commas and extra spaces
#     name = re.sub(r'[,.]', ' ', name)
#     name = re.sub(r'\s+', ' ', name).strip().upper()
#     
#     # Split into parts
#     parts = name.split()
#     
#     # If we have more than 3 parts and any part is a single letter (initial),
#     # expand it for better matching
#     normalized_parts = []
#     for i, part in enumerate(parts):
#         if len(part) == 1 and i > 0:  # Single letter (not first name)
#             # It's likely a middle initial, keep just the first letter
#             normalized_parts.append(part)
#         elif len(part) > 1 and i > 1:  # Middle name or later
#             # For middle names, keep first letter for comparison
#             normalized_parts.append(part[0])
#         else:
#             normalized_parts.append(part)
#     
#     return ' '.join(normalized_parts)
# 
# 
# def normalize_date(date_str: str) -> str:
#     """
#     Normalize date string to YYYY-MM-DD format for comparison.
#     Handles multiple formats including:
#     - 'YYYY-MM-DD' (1995-01-09)
#     - 'September 01, 1995'
#     - 'MM/DD/YYYY'
#     - etc.
#     """
#     import re
#     from datetime import datetime
#     
#     if not date_str:
#         return ''
#     
#     date_str = str(date_str).strip()
#     
#     # List of formats to try
#     formats = [
#         '%Y-%m-%d',           # 1995-01-09
#         '%B %d, %Y',          # September 01, 1995
#         '%b %d, %Y',          # Sep 01, 1995
#         '%m/%d/%Y',           # 09/01/1995
#         '%d/%m/%Y',           # 01/09/1995
#         '%Y/%m/%d',           # 1995/09/01
#         '%d-%m-%Y',           # 01-09-1995
#         '%m-%d-%Y',           # 09-01-1995
#     ]
#     
#     # Try each format
#     for fmt in formats:
#         try:
#             parsed = datetime.strptime(date_str, fmt)
#             return parsed.strftime('%Y-%m-%d')
#         except ValueError:
#             continue
#     
#     # Try using dateutil as fallback (handles more formats)
#     try:
#         from dateutil import parser
#         parsed = parser.parse(date_str, fuzzy=True)
#         return parsed.strftime('%Y-%m-%d')
#     except (ValueError, TypeError, AttributeError, ImportError):
#         pass
#     
#     # Last resort: extract digits and try to make sense of it
#     digits = re.sub(r'\D', '', date_str)
#     if len(digits) == 8:  # YYYYMMDD or MMDDYYYY or DDMMYYYY
#         # Assume YYYYMMDD if starts with 19 or 20
#         if digits.startswith('19') or digits.startswith('20'):
#             return f"{digits[0:4]}-{digits[4:6]}-{digits[6:8]}"
#     
#     return date_str  # Return original if can't parse

        else:
            # PENDING - Manual Review Required (score 60-79%)
            logger.info(f"Marking for manual review - verification score: {overall_score:.1%}")
            
            with transaction.atomic():
                verification.status = 'pending'
                verification.save(update_fields=['status'])
                
                log.result = 'pending'
                log.notes += f"\n\nMarked for manual review: Score {overall_score:.1%} (threshold: 80% for auto-approve)"
                log.save(update_fields=['result', 'notes'])
                
                # Notify user
                Notification.objects.create(
                    user=user,
                    message=f"⏳ Your ID verification is under review. Verification score: {overall_score:.0%}. Our team will review your submission and respond within 24-48 hours.",
                    notif_type="verification_pending"
                )
            
            return {
                'success': True,
                'decision': 'pending',
                'match_score': overall_score,
                'reason': 'Score requires manual review'
            }
