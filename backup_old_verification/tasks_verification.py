"""
Redesigned verification orchestrator with separated tasks.

Verification Flow:
1. OCR Extraction → Extract data from ID
2. Data Validation → Compare with user profile
3. Face Matching → Compare ID photo with selfie
4. PhilSys Web Verification → Verify with government portal (if passed step 2)
5. Final Decision → Determine verification status
"""
from celery import shared_task, chain
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def run_complete_verification(self, user_id: int, verification_id: int = None) -> Dict[str, Any]:
    """
    Main verification orchestrator - runs all verification steps in sequence.
    
    Steps:
    1. OCR Extraction (extract_id_data)
    2. Data Validation (validate_extracted_data)
    3. Face Matching (match_faces)
    4. PhilSys Web Verification (verify_philsys_web) - only if steps 1-3 pass
    5. Final Decision (finalize_verification)
    
    Args:
        user_id: User ID to verify
        verification_id: AccountVerification ID (optional)
    
    Returns:
        Final verification result
    """
    from users.models import CustomUser, AccountVerification, VerificationLog
    from users.services.verification.progress_tracker import VerificationProgressTracker
    from notifications.models import Notification
    
    tracker = VerificationProgressTracker(user_id)
    
    try:
        user = CustomUser.objects.get(pk=user_id)
        tracker.update("starting", 5, "Starting verification process...")
        
        logger.info(f"Starting complete verification for user {user_id}")
        
        # Step 1: OCR Extraction
        from users.tasks_ocr import extract_id_data
        tracker.update("ocr", 10, "Extracting data from ID...")
        ocr_result = extract_id_data(user_id)
        
        if not ocr_result.get('success'):
            return fail_verification(
                user, verification_id, tracker,
                reason="OCR extraction failed",
                details=ocr_result.get('error', 'Unknown error')
            )
        
        extracted_data = ocr_result.get('extracted_data', {})
        quality_score = ocr_result.get('quality_score', 0.0)
        
        logger.info(f"OCR completed for user {user_id}: quality={quality_score:.2f}")
        
        # NOTE: We no longer auto-reject on poor OCR quality
        # Let admin review - image may be valid but hard to read
        
        # Step 2a: Check if image is a valid ID document
        tracker.update("validation", 35, "Checking if image is a valid ID...")
        is_valid_id = is_valid_id_document(extracted_data)
        
        if not is_valid_id:
            return fail_verification(
                user, verification_id, tracker,
                reason="Invalid ID document",
                details="The submitted image does not appear to be a valid ID document. Please upload a clear photo of your government-issued ID."
            )
        
        # Step 2b: Check if ID type matches what user indicated
        tracker.update("validation", 38, "Checking ID type match...")
        id_type_matches = check_id_type_match(user, extracted_data)
        
        if not id_type_matches:
            return fail_verification(
                user, verification_id, tracker,
                reason="ID type mismatch",
                details=f"The submitted ID does not match the indicated type ({user.id_type}). Please upload the correct ID type or update your selection."
            )
        
        # Step 2c: Data Validation
        tracker.update("validation", 40, "Validating extracted data...")
        validation_result = validate_extracted_data(user, extracted_data)
        
        # NOTE: We no longer auto-reject on data validation failure
        # Let admin review cases with mismatched data
        logger.info(f"Data validation completed for user {user_id}: confidence={validation_result.get('confidence'):.2f}")
        
        # Step 3: Face Matching
        tracker.update("face_match", 60, "Comparing faces...")
        face_result = match_faces(user)
        
        similarity_score = face_result.get('similarity_score')
        
        if similarity_score is None:
            logger.warning(f"Face matching unavailable for user {user_id}")
        else:
            logger.info(f"Face matching completed for user {user_id}: similarity={similarity_score:.2f}")
        
        # NOTE: We no longer auto-reject on low face similarity
        # Let admin review cases with low similarity scores
        
        # Step 4: PhilSys Web Verification (only for PhilSys IDs and if user consented)
        philsys_result = None
        is_philsys = ocr_result.get('is_philsys', False)
        
        if is_philsys and getattr(user, 'philsys_verification_consent', False):
            tracker.update("philsys_web", 85, "Verifying with PhilSys portal...")
            
            from users.tasks_philsys_verify import verify_philsys_web
            philsys_result = verify_philsys_web(user_id, extracted_data)
            
            if philsys_result.get('success') and philsys_result.get('verified'):
                logger.info(f"PhilSys web verification passed for user {user_id}")
            elif philsys_result.get('success') and not philsys_result.get('skipped'):
                logger.warning(f"PhilSys web verification failed for user {user_id}: {philsys_result.get('reason')}")
                # NOTE: We no longer auto-reject on PhilSys failure
                # Let admin review - government portal may have issues
        
        # Step 5: Final Decision
        tracker.update("finalizing", 95, "Finalizing verification...")
        
        final_status = determine_final_status(
            quality_score=quality_score,
            validation_confidence=validation_result.get('confidence', 0.0),
            similarity_score=similarity_score,
            philsys_verified=philsys_result.get('verified') if philsys_result else None
        )
        
        # Save verification log
        notes = []
        notes.append(f"OCR Quality: {quality_score:.2f}")
        notes.append(f"Data Validation: {validation_result.get('confidence', 0.0):.2f}")
        notes.append(f"Matched Fields: {', '.join(validation_result.get('matched_fields', []))}")
        if similarity_score is not None:
            notes.append(f"Face Similarity: {similarity_score:.2f}")
        if philsys_result and not philsys_result.get('skipped'):
            notes.append(f"PhilSys Web Verified: {philsys_result.get('verified')}")
        notes.append(f"Final Status: {final_status}")
        
        VerificationLog.objects.create(
            user=user,
            extracted_data=extracted_data,
            similarity_score=similarity_score,
            process_type='automated',
            result=final_status,
            notes="\n".join(notes)
        )
        
        # Update user status - but don't overwrite if already verified by PhilSys auto-verification
        user.refresh_from_db()  # Get latest status
        
        # If user is already verified (e.g., by PhilSys auto-verification), don't downgrade to manual_review
        if user.verification_status == 'verified' and final_status == 'manual_review':
            logger.info(f"User {user_id} already verified (likely by PhilSys auto-verification), keeping verified status")
            final_status = 'verified'
        
        user.verification_status = final_status
        user.verification_score = similarity_score
        user.is_verified = (final_status == 'verified')
        user.is_verified_philsys = (philsys_result.get('verified') if philsys_result else False)
        user.save(update_fields=['verification_status', 'verification_score', 'is_verified', 'is_verified_philsys'])
        
        # Update AccountVerification if provided
        if verification_id:
            try:
                from django.utils import timezone
                from django.db import transaction
                
                # Use transaction to prevent race conditions
                with transaction.atomic():
                    # Refresh from database to get latest status with row lock
                    verification = AccountVerification.objects.select_for_update().get(pk=verification_id)
                    
                    # Don't downgrade if already approved (e.g., by PhilSys auto-verification)
                    if verification.status == 'approved':
                        logger.info(f"Verification {verification_id} already approved by PhilSys auto-verification, skipping pipeline update")
                        # Keep the approved status, don't change anything - exit early
                    else:
                        verification.status = {
                            'verified': 'approved',
                            'failed': 'rejected',
                            'manual_review': 'pending'
                        }.get(final_status, 'pending')
                        
                        # If auto-approved, set reviewed_at timestamp
                        if verification.status == 'approved':
                            verification.reviewed_at = timezone.now()
                            verification.save(update_fields=['status', 'reviewed_at'])
                        elif verification.status == 'rejected':
                            verification.reviewed_at = timezone.now()
                            verification.rejection_reason = '\n'.join(notes) if notes else 'Auto-rejected by system'
                            verification.save(update_fields=['status', 'reviewed_at', 'rejection_reason'])
                        else:
                            verification.save(update_fields=['status'])
            except AccountVerification.DoesNotExist:
                pass
        
        # Send notification
        send_verification_notification(user, final_status, notes)
        
        # Complete tracking
        status_messages = {
            'verified': '✅ Verification approved!',
            'failed': '❌ Verification failed',
            'manual_review': '⚠️ Requires manual review'
        }
        tracker.complete(final_status, status_messages.get(final_status, 'Verification completed'))
        
        logger.info(f"Verification completed for user {user_id}: status={final_status}")
        
        return {
            'success': True,
            'user_id': user_id,
            'status': final_status,
            'similarity_score': similarity_score,
            'quality_score': quality_score,
            'validation_confidence': validation_result.get('confidence'),
            'philsys_verified': philsys_result.get('verified') if philsys_result else None,
            'extracted_data': extracted_data
        }
        
    except Exception as e:
        logger.exception(f"Verification failed for user {user_id}")
        tracker.error(f"Verification error: {str(e)}")
        return {
            'success': False,
            'user_id': user_id,
            'status': 'failed',
            'error': str(e)
        }


def validate_extracted_data(user, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate extracted data against user profile."""
    from users.services.verification.data_validator import DataValidator
    
    validator = DataValidator(strict_mode=False)
    result = validator.validate(user, extracted_data)
    
    return {
        'is_valid': result.is_valid,
        'confidence': result.confidence_score,
        'matched_fields': result.matched_fields,
        'mismatches': result.mismatches,
        'warnings': result.warnings,
        'reason': f"{len(result.mismatches)} mismatches found" if result.mismatches else "Validation passed"
    }


def match_faces(user) -> Dict[str, Any]:
    """Match face from ID with selfie."""
    from users.services.verification.face_match import compute_similarity
    from users.services.verification.utils import load_image, save_temp_image
    import os
    
    try:
        id_image = load_image(user.id_image)
        selfie_image = load_image(user.selfie_image)
        
        id_path, _ = save_temp_image(id_image)
        selfie_path, _ = save_temp_image(selfie_image)
        
        try:
            similarity_score, debug_meta = compute_similarity(id_path, selfie_path)
            return {
                'success': True,
                'similarity_score': similarity_score,
                'debug_meta': debug_meta
            }
        finally:
            try:
                os.remove(id_path)
                os.remove(selfie_path)
            except (OSError, FileNotFoundError) as e:
                logger.debug(f"Failed to cleanup temporary files: {e}")
    
    except Exception as e:
        logger.exception("Face matching failed")
        return {
            'success': False,
            'similarity_score': None,
            'error': str(e)
        }


def is_valid_id_document(extracted_data: Dict[str, Any]) -> bool:
    """
    Check if the image is actually an ID document.
    Returns False if image appears to be random/non-ID content.
    """
    raw_text = extracted_data.get('raw_text', '').upper()
    
    # Check for common ID-related keywords
    id_keywords = [
        'REPUBLIC', 'PILIPINAS', 'PHILIPPINES', 'GOVERNMENT', 
        'NATIONAL', 'LICENSE', 'IDENTIFICATION', 'CARD',
        'PHILSYS', 'PSA', 'LTO', 'SSS', 'GSIS', 'UMID',
        'PASSPORT', 'DRIVER', 'VOTER', 'PRC', 'PROFESSIONAL',
        'BIRTH', 'CERTIFICATE', 'VALID', 'UNTIL', 'EXPIRES',
        'DATE OF BIRTH', 'SEX', 'ADDRESS', 'SIGNATURE'
    ]
    
    # Count how many ID keywords are found
    keyword_count = sum(1 for keyword in id_keywords if keyword in raw_text)
    
    # If we found at least 2 ID-related keywords, it's likely an ID
    if keyword_count >= 2:
        return True
    
    # Check if we extracted any structured ID data
    has_id_number = bool(extracted_data.get('id_number') or extracted_data.get('pcn'))
    has_name = bool(extracted_data.get('full_name') or extracted_data.get('first_name'))
    has_dob = bool(extracted_data.get('date_of_birth'))
    
    # If we extracted structured data, it's likely an ID
    if has_id_number or (has_name and has_dob):
        return True
    
    # If raw text is very short (< 50 chars), probably not an ID
    if len(raw_text.strip()) < 50:
        return False
    
    # Default to True (give benefit of doubt, let admin review)
    return True


def check_id_type_match(user, extracted_data: Dict[str, Any]) -> bool:
    """
    Check if the detected ID type matches what the user indicated.
    Returns False only if there's a clear mismatch.
    """
    indicated_type = (user.id_type or '').lower()
    raw_text = extracted_data.get('raw_text', '').upper()
    detected_type = extracted_data.get('id_type', '').lower()
    
    # Normalize indicated type
    if indicated_type in ['philsys', 'philsys_id', 'national_id', 'philsys id', 'national id']:
        indicated_type = 'philsys'
    elif indicated_type in ['drivers_license', "driver's license", 'drivers license', 'license']:
        indicated_type = 'drivers_license'
    elif indicated_type in ['passport']:
        indicated_type = 'passport'
    elif indicated_type in ['umid']:
        indicated_type = 'umid'
    elif indicated_type in ['sss']:
        indicated_type = 'sss'
    elif indicated_type in ['voters_id', 'voters id', "voter's id"]:
        indicated_type = 'voters_id'
    
    # Check for clear mismatches
    if indicated_type == 'philsys':
        # User said PhilSys, check if it's clearly NOT PhilSys
        if 'DRIVER' in raw_text and 'LICENSE' in raw_text:
            return False  # Clearly a driver's license, not PhilSys
        if 'PASSPORT' in raw_text and 'REPUBLIC' in raw_text:
            return False  # Clearly a passport, not PhilSys
    
    elif indicated_type == 'drivers_license':
        # User said Driver's License, check if it's clearly NOT a license
        if 'PHILSYS' in raw_text or 'PAMBANSANG PAGKAKAKILANLAN' in raw_text:
            return False  # Clearly PhilSys, not driver's license
        if 'PASSPORT' in raw_text:
            return False  # Clearly a passport
    
    elif indicated_type == 'passport':
        # User said Passport, check if it's clearly NOT a passport
        if 'DRIVER' in raw_text and 'LICENSE' in raw_text:
            return False  # Clearly a driver's license
        if 'PHILSYS' in raw_text:
            return False  # Clearly PhilSys
    
    # If we can't determine a clear mismatch, assume it matches
    # Let admin review if there are doubts
    return True


def determine_final_status(
    quality_score: float,
    validation_confidence: float,
    similarity_score: float = None,
    philsys_verified: bool = None,
    is_valid_id: bool = True,
    id_type_matches: bool = True
) -> str:
    """
    Determine final verification status based on all checks.
    
    NEW AUTO-REJECT RULES:
    - Only auto-reject if:
      1. Image is not an ID at all (is_valid_id = False)
      2. ID type doesn't match what user indicated (id_type_matches = False)
    
    VERIFICATION RULES:
    1. If PhilSys web verified AND face match good → verified
    2. If all scores high → verified
    3. Otherwise → manual_review (let admin decide)
    """
    # AUTO-REJECT ONLY if image is not an ID or wrong ID type
    if not is_valid_id:
        return 'failed'  # Image is not an ID document
    
    if not id_type_matches:
        return 'failed'  # ID type doesn't match what user indicated
    
    # If PhilSys web verification passed, that's strong evidence
    if philsys_verified:
        if similarity_score is None or similarity_score >= 0.5:
            return 'verified'
    
    # Check if all scores are good
    if quality_score >= 0.7 and validation_confidence >= 0.75:
        if similarity_score is None or similarity_score >= 0.7:
            return 'verified'
    
    # Everything else goes to manual review
    # Let admin decide on borderline cases, poor OCR, mismatched data, etc.
    
    # Default to manual review for edge cases
    return 'manual_review'


def fail_verification(user, verification_id, tracker, reason: str, details: str, mismatches: list = None):
    """Helper to fail verification with proper logging and notification."""
    from users.models import VerificationLog, AccountVerification
    from notifications.models import Notification
    
    notes = [f"Verification Failed: {reason}", f"Details: {details}"]
    if mismatches:
        notes.append("Mismatches:")
        for mismatch in mismatches:
            notes.append(f"  - {mismatch}")
    
    VerificationLog.objects.create(
        user=user,
        extracted_data={},
        similarity_score=None,
        process_type='automated',
        result='failed',
        notes="\n".join(notes)
    )
    
    user.verification_status = 'failed'
    user.is_verified = False
    user.save(update_fields=['verification_status', 'is_verified'])
    
    if verification_id:
        try:
            from django.utils import timezone
            verification = AccountVerification.objects.get(pk=verification_id)
            verification.status = 'rejected'
            verification.reviewed_at = timezone.now()
            verification.rejection_reason = '\n'.join(notes)
            verification.save(update_fields=['status', 'reviewed_at', 'rejection_reason'])
        except AccountVerification.DoesNotExist:
            pass
    
    Notification.objects.create(
        user=user,
        message=f"❌ Your identity verification could not be approved. Reason: {reason}. {details}. Please submit a new verification request with clear, valid documents.",
        notif_type="verification_rejected"
    )
    
    tracker.complete('failed', f"Verification failed: {reason}")
    
    return {
        'success': False,
        'user_id': user.id,
        'status': 'failed',
        'reason': reason,
        'details': details
    }


def send_verification_notification(user, status: str, notes: list):
    """Send notification to user about verification result."""
    from notifications.models import Notification
    
    if status == 'verified':
        Notification.objects.create(
            user=user,
            message="🎉 Great news! Your identity verification has been approved. You now have a verified badge on your profile.",
            notif_type="verification_approved"
        )
    elif status == 'failed':
        Notification.objects.create(
            user=user,
            message="⚠️ Your identity verification requires additional review. Our team will manually check your documents and notify you once the review is complete. This typically takes 24-48 hours.",
            notif_type="verification_rejected"
        )
    elif status == 'manual_review':
        Notification.objects.create(
            user=user,
            message="Your identity verification is under manual review. We'll notify you once the review is complete.",
            notif_type="verification_pending"
        )
