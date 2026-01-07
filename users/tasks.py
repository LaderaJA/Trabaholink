"""Asynchronous tasks for the users app."""
from __future__ import annotations

import logging
from typing import Dict, Any

from celery import shared_task
from django.utils import timezone

from users.models import CustomUser, PhilSysVerification
from users.services.verification import VerificationPipeline
from users.services.verification.philsys_qr import PhilSysQRExtractor, is_philsys_id
# DISABLED: PhilSysWebValidator uses Playwright which violates terms of use
# from users.services.verification.philsys_web_validator import PhilSysWebValidator
from users.services.verification.encryption import (
    encrypt_qr_payload, 
    hash_qr_payload, 
    mask_pcn
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=2)
def run_verification_pipeline(self, user_id: int, verification_id: int = None) -> Dict[str, Any]:
    """
    Execute the complete verification pipeline asynchronously in background.
    
    NEW REDESIGNED FLOW:
    1. OCR Extraction → Extract clean data from ID
    2. Data Validation → Compare with user profile  
    3. Face Matching → Compare ID photo with selfie
    4. PhilSys Web Verification → Verify with https://verify.philsys.gov.ph/ (if passed steps 1-3)
    5. Final Decision → Determine verification status
    
    Args:
        user_id: ID of the user being verified
        verification_id: ID of AccountVerification record (optional)
    
    Returns:
        Dict with status and details
    """
    from users.tasks_verification import verify_id_with_ocr_v2, verify_face_match_v2, complete_verification_v2
    from users.models import AccountVerification, VerificationLog
    from notifications.models import Notification
    
    try:
        logger.info(f"Starting enhanced verification V2 for user {user_id}")
        
        # Get or create verification record
        if verification_id:
            verification = AccountVerification.objects.get(id=verification_id, user_id=user_id)
        else:
            # Get the latest pending verification
            verification = AccountVerification.objects.filter(
                user_id=user_id,
                status='pending'
            ).first()
            
            if not verification:
                logger.error(f"No pending verification found for user {user_id}")
                return {
                    'status': 'error',
                    'user_id': user_id,
                    'message': 'No pending verification found'
                }
        
        # Run enhanced verification pipeline
        # For PhilSys IDs: Skip OCR (uses QR code extraction in auto_verify_philsys task)
        # For other IDs: Run OCR → Face Match → Complete
        from celery import chain
        
        # Check if this is a PhilSys ID
        user = CustomUser.objects.get(pk=user_id)
        if is_philsys_id(user.id_type):
            # PhilSys IDs don't need OCR - QR extraction handles data
            logger.info(f"PhilSys ID detected for user {user_id} - skipping OCR task")
            verification_chain = chain(
                verify_face_match_v2.si(verification.id),
                complete_verification_v2.si(verification.id)
            )
        else:
            # Standard verification with OCR
            logger.info(f"Standard ID type for user {user_id} - running full OCR pipeline")
            verification_chain = chain(
                verify_id_with_ocr_v2.si(verification.id),
                verify_face_match_v2.si(verification.id),
                complete_verification_v2.si(verification.id)
            )
        
        # Apply async without blocking (don't call .get()!)
        verification_chain.apply_async()
        
        logger.info(f"Enhanced verification V2 pipeline started for user {user_id}, verification {verification.id}")
        
        # Return immediately without waiting for results
        return {
            'status': 'started',
            'user_id': user_id,
            'verification_id': verification.id,
            'message': 'Verification pipeline started successfully'
        }
        
    except CustomUser.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {
            'status': 'error',
            'user_id': user_id,
            'message': 'User not found'
        }
    except Exception as e:
        logger.exception(f"Verification pipeline failed for user {user_id}: {e}")
        
        # Send error notification to user
        try:
            user = CustomUser.objects.get(pk=user_id)
            Notification.objects.create(
                user=user,
                message="We encountered an error while processing your verification. Our team has been notified and will review your submission manually.",
                notif_type="verification_error"
            )
        except Exception as e:
            logger.warning(f"Failed to create error notification for user {user.id}: {e}")
        
        raise  # Re-raise for Celery retry


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,  # Max 10 minutes between retries
    max_retries=2,
    rate_limit='10/m'  # Max 10 PhilSys verifications per minute
)
def run_philsys_verification(
    self, 
    user_id: int, 
    id_image_path: str,
    user_consented: bool = False,
    ip_address: str = None,
    user_agent: str = None
) -> Dict[str, Any]:
    """
    Execute PhilSys QR verification asynchronously.
    
    Args:
        user_id: User ID to verify
        id_image_path: Path to the PhilSys ID image
        user_consented: Whether user consented to web verification
        ip_address: User's IP address for audit
        user_agent: User's browser user agent for audit
        
    Returns:
        Dict with verification result status and details
    """
    logger.info(f"Starting PhilSys verification for user {user_id}")
    
    try:
        # Get user
        user = CustomUser.objects.get(pk=user_id)
        
        # Check if user has PhilSys ID type
        if not is_philsys_id(user.id_type):
            logger.warning(f"User {user_id} does not have PhilSys ID type: {user.id_type}")
            return {
                'success': False,
                'status': 'error',
                'message': 'ID type is not PhilSys'
            }
        
        # Check consent
        if not user_consented:
            logger.warning(f"User {user_id} did not consent to PhilSys verification")
            return {
                'success': False,
                'status': 'error',
                'message': 'User consent required for PhilSys verification'
            }
        
        # Step 1: Extract QR code from image
        logger.info(f"Extracting QR code from image for user {user_id}")
        extractor = PhilSysQRExtractor()
        qr_result = extractor.extract_qr_from_image(id_image_path)
        
        if not qr_result.success:
            logger.error(f"QR extraction failed for user {user_id}: {qr_result.error_message}")
            
            # Create failed verification record
            PhilSysVerification.objects.create(
                user=user,
                status='failed',
                verified=False,
                verification_message=qr_result.error_message or "QR code extraction failed",
                error_details=qr_result.error_message,
                user_consented=user_consented,
                consent_timestamp=timezone.now() if user_consented else None,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            return {
                'success': False,
                'status': 'failed',
                'message': qr_result.error_message
            }
        
        logger.info(f"QR extraction successful for user {user_id}")
        
        # Step 2: Encrypt and hash QR payload
        qr_encrypted = encrypt_qr_payload(qr_result.qr_data)
        qr_hash = hash_qr_payload(qr_result.qr_data)
        pcn_masked_value = mask_pcn(qr_result.pcn) if qr_result.pcn else ""
        pcn_hash_value = hash_qr_payload(qr_result.pcn) if qr_result.pcn else ""
        
        # Step 3: Create PhilSysVerification record
        philsys_verification = PhilSysVerification.objects.create(
            user=user,
            qr_payload_encrypted=qr_encrypted,
            qr_payload_hash=qr_hash,
            pcn_masked=pcn_masked_value,
            pcn_hash=pcn_hash_value,
            status='processing',
            verified=False,
            preprocessing_applied=qr_result.preprocessing_applied,
            extracted_fields=qr_result.extracted_fields,
            user_consented=user_consented,
            consent_timestamp=timezone.now() if user_consented else None,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Step 4: Verify QR code via PhilSys website
        logger.info(f"Starting web verification for user {user_id}")
        # DISABLED: PhilSysWebValidator uses Playwright automation
        # validator = PhilSysWebValidator(headless=True, timeout=30000)
        logger.warning("PhilSys web validation disabled - use offline verification instead")
        
        try:
            web_result = validator.verify_qr_code(
                qr_data=qr_result.qr_data,
                pcn=qr_result.pcn,
                save_screenshot=True
            )
            
            # Update verification record with web result
            philsys_verification.status = web_result.verification_status
            philsys_verification.verified = web_result.verified
            philsys_verification.verification_message = web_result.message
            philsys_verification.verification_timestamp = web_result.timestamp
            philsys_verification.response_time = web_result.response_time
            philsys_verification.error_details = web_result.error_details or ""
            philsys_verification.screenshot_path = web_result.screenshot_path or ""
            philsys_verification.save()
            
            # If verified, update user model
            if web_result.verified:
                logger.info(f"PhilSys verification successful for user {user_id}")
                user.is_verified_philsys = True
                user.philsys_verified_at = timezone.now()
                user.philsys_pcn_masked = pcn_masked_value
                user.save(update_fields=[
                    'is_verified_philsys', 
                    'philsys_verified_at', 
                    'philsys_pcn_masked'
                ])
                
                # Send notification
                from notifications.models import Notification
                Notification.objects.create(
                    user=user,
                    message="Your PhilSys ID has been successfully verified! You now have a PhilSys verification badge on your profile.",
                    notif_type="philsys_verified"
                )
                
                return {
                    'success': True,
                    'status': 'verified',
                    'message': 'PhilSys ID verified successfully',
                    'pcn_masked': pcn_masked_value
                }
            else:
                logger.warning(f"PhilSys verification failed for user {user_id}: {web_result.message}")
                
                # Send notification
                from notifications.models import Notification
                Notification.objects.create(
                    user=user,
                    message=f"PhilSys ID verification failed: {web_result.message}. Please try again with a clearer image.",
                    notif_type="philsys_verification_failed"
                )
                
                return {
                    'success': False,
                    'status': web_result.verification_status,
                    'message': web_result.message
                }
                
        except Exception as e:
            logger.exception(f"Web verification error for user {user_id}: {e}")
            
            # Update verification record with error
            philsys_verification.status = 'error'
            philsys_verification.verified = False
            philsys_verification.error_details = str(e)
            philsys_verification.save()
            
            # Increment retry counter
            philsys_verification.increment_retry()
            
            # Re-raise for Celery retry mechanism
            raise
    
    except CustomUser.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {
            'success': False,
            'status': 'error',
            'message': 'User not found'
        }
    
    except Exception as e:
        logger.exception(f"PhilSys verification task failed for user {user_id}: {e}")
        
        # If max retries exceeded, mark as error
        if self.request.retries >= self.max_retries:
            logger.error(f"Max retries exceeded for user {user_id}")
            
            try:
                user = CustomUser.objects.get(pk=user_id)
                from notifications.models import Notification
                Notification.objects.create(
                    user=user,
                    message="PhilSys ID verification encountered an error. Please try again later or contact support.",
                    notif_type="philsys_verification_error"
                )
            except Exception as e:
                logger.warning(f"Failed to create PhilSys error notification for user {user.id}: {e}")
        
        return {
            'success': False,
            'status': 'error',
            'message': str(e)
        }


# Import new task modules to ensure they're discovered by Celery
from users import tasks_philsys_verify, tasks_verification  # noqa: F401, E402
