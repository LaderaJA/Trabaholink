"""
Enhanced ID Verification Tasks V2
Uses improved OCR and face recognition modules
"""
from celery import shared_task
import logging
from django.core.files.base import ContentFile
from PIL import Image
import io
import os

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def verify_id_with_ocr_v2(self, verification_id):
    """
    Enhanced OCR-based ID verification task.
    Uses PhilSysOCRV2 for better accuracy.
    
    Args:
        verification_id: ID of the AccountVerification to process
        
    Returns:
        dict: Verification results with extracted data
    """
    from users.models import AccountVerification, VerificationLog
    from users.services.verification.ocr_philsys import PhilSysOCRV2
    
    try:
        logger.info(f"Starting enhanced OCR verification for verification {verification_id}")
        
        # Get verification record
        verification = AccountVerification.objects.get(id=verification_id)
        user = verification.user
        
        # Check if ID image exists
        if not verification.id_image_front:
            logger.error(f"Verification {verification_id} has no ID image")
            verification.status = 'rejected'
            verification.rejection_reason = 'No ID image provided'
            verification.save()
            return {
                'success': False,
                'error': 'No ID image found'
            }
        
        # Load ID image
        id_image_path = verification.id_image_front.path
        logger.info(f"Processing ID image: {id_image_path}")
        
        image = Image.open(id_image_path)
        logger.info(f"Loaded image: {image.size} {image.mode}")
        
        # Initialize enhanced OCR
        ocr = PhilSysOCRV2()
        
        # Extract data
        logger.info("Extracting data with enhanced OCR...")
        extracted_data = ocr.extract_philsys_data(image)
        
        logger.info(f"OCR extraction complete. Quality: {extracted_data.get('extraction_quality', 'unknown')}")
        logger.info(f"Fields extracted: {extracted_data.get('fields_extracted_count', 0)}/4")
        
        # Save extraction log
        log = VerificationLog.objects.create(
            user=user,
            extracted_data=extracted_data,
            result='completed',
            notes=f'Enhanced OCR V2 extraction completed. Quality: {extracted_data.get("extraction_quality", "unknown")}'
        )
        
        logger.info(f"Saved VerificationLog {log.id} for user {user.id}")
        
        # Compare extracted data with user profile
        matches = {}
        mismatches = {}
        
        # Compare name
        if 'full_name' in extracted_data:
            user_name = f"{user.last_name}, {user.first_name} {user.middle_name}".upper()
            extracted_name = extracted_data['full_name'].upper()
            
            # Calculate name similarity
            from difflib import SequenceMatcher
            similarity = SequenceMatcher(None, user_name, extracted_name).ratio()
            
            if similarity >= 0.75:
                matches['name'] = f"Match: {similarity:.0%}"
            else:
                mismatches['name'] = f"Mismatch: User='{user_name}', ID='{extracted_name}' ({similarity:.0%})"
        
        # Compare date of birth
        if 'date_of_birth' in extracted_data and user.date_of_birth:
            user_dob = user.date_of_birth.strftime('%Y-%m-%d')
            extracted_dob = extracted_data['date_of_birth']
            
            if user_dob == extracted_dob:
                matches['date_of_birth'] = 'Match'
            else:
                mismatches['date_of_birth'] = f"Mismatch: User='{user_dob}', ID='{extracted_dob}'"
        
        # Compare sex
        if 'sex' in extracted_data and user.gender:
            user_sex = user.gender.capitalize()
            extracted_sex = extracted_data['sex']
            
            if user_sex == extracted_sex:
                matches['sex'] = 'Match'
            else:
                mismatches['sex'] = f"Mismatch: User='{user_sex}', ID='{extracted_sex}'"
        
        # Calculate match score
        total_comparisons = len(matches) + len(mismatches)
        match_score = len(matches) / total_comparisons if total_comparisons > 0 else 0
        
        logger.info(f"Data comparison: {len(matches)} matches, {len(mismatches)} mismatches, score: {match_score:.2%}")
        
        # Update verification status based on results
        extraction_quality = extracted_data.get('extraction_quality', 'poor')
        
        if extraction_quality in ['excellent', 'good'] and match_score >= 0.75:
            verification.status = 'approved'
            verification.notes = f'Auto-approved: OCR quality={extraction_quality}, match score={match_score:.0%}'
            logger.info(f"Auto-approved verification {verification_id}")
        elif extraction_quality == 'poor' or match_score < 0.5:
            verification.status = 'pending'
            verification.notes = f'Manual review required: OCR quality={extraction_quality}, match score={match_score:.0%}'
            logger.info(f"Verification {verification_id} requires manual review")
        else:
            verification.status = 'pending'
            verification.notes = f'Manual review recommended: OCR quality={extraction_quality}, match score={match_score:.0%}'
            logger.info(f"Verification {verification_id} pending manual review")
        
        verification.save()
        
        return {
            'success': True,
            'verification_id': verification_id,
            'user_id': user.id,
            'extraction_quality': extraction_quality,
            'fields_extracted': extracted_data.get('fields_extracted_count', 0),
            'match_score': match_score,
            'matches': matches,
            'mismatches': mismatches,
            'status': verification.status,
            'log_id': log.id
        }
        
    except AccountVerification.DoesNotExist:
        logger.error(f"Verification {verification_id} not found")
        return {
            'success': False,
            'error': 'Verification not found'
        }
        
    except Exception as e:
        logger.exception(f"Enhanced OCR verification failed for verification {verification_id}: {e}")
        
        # Retry on failure
        try:
            raise self.retry(exc=e, countdown=60)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for verification {verification_id}")
            
            # Mark as requiring manual review
            try:
                verification = AccountVerification.objects.get(id=verification_id)
                verification.status = 'pending'
                verification.rejection_reason = f'OCR processing error: {str(e)[:200]}'
                verification.save()
            except Exception:
                pass
            
            return {
                'success': False,
                'error': str(e)
            }


@shared_task(bind=True, max_retries=3)
def verify_face_match_v2(self, verification_id):
    """
    Enhanced face matching verification task.
    Uses FaceMatcherV2 for improved accuracy.
    
    Args:
        verification_id: ID of the AccountVerification to process
        
    Returns:
        dict: Face matching results with similarity score
    """
    from users.models import AccountVerification
    from users.services.verification.face_match import FaceMatcherV2, SIMILARITY_THRESHOLD_VERIFIED
    
    try:
        logger.info(f"Starting enhanced face matching for verification {verification_id}")
        
        # Get verification record
        verification = AccountVerification.objects.get(id=verification_id)
        user = verification.user
        
        # Check if both images exist
        if not verification.id_image_front or not verification.selfie_image:
            logger.error(f"Verification {verification_id} missing images")
            return {
                'success': False,
                'error': 'Missing ID or selfie image'
            }
        
        # Get image paths
        id_path = verification.id_image_front.path
        selfie_path = verification.selfie_image.path
        
        logger.info(f"Comparing faces: ID={id_path}, Selfie={selfie_path}")
        
        # Initialize face matcher
        matcher = FaceMatcherV2()
        
        # Compute similarity
        similarity, metadata = matcher.compute_similarity(id_path, selfie_path)
        
        logger.info(f"Face matching complete: similarity={similarity:.4f}, method={metadata.get('method')}")
        logger.info(f"Metadata: {metadata}")
        
        # Determine verification result
        if similarity >= SIMILARITY_THRESHOLD_VERIFIED:
            result = 'verified'
            notes = f'Auto-verified: Face match {similarity:.0%} (threshold: {SIMILARITY_THRESHOLD_VERIFIED:.0%})'
            logger.info(f"Face match verified for verification {verification_id}")
        elif similarity >= 0.40:
            result = 'manual_review'
            notes = f'Manual review: Face match {similarity:.0%} (threshold: {SIMILARITY_THRESHOLD_VERIFIED:.0%})'
            logger.info(f"Face match requires manual review for verification {verification_id}")
        else:
            result = 'rejected'
            notes = f'Face mismatch: Similarity {similarity:.0%} too low'
            logger.warning(f"Face match rejected for verification {verification_id}")
        
        # Update verification record
        verification.face_match_score = similarity
        verification.face_match_metadata = metadata
        
        if result == 'verified' and verification.status == 'pending':
            verification.status = 'approved'
            verification.notes = notes
        elif result == 'rejected':
            verification.status = 'rejected'
            verification.rejection_reason = notes
        else:
            # Manual review needed
            if not verification.notes:
                verification.notes = notes
        
        verification.save()
        
        return {
            'success': True,
            'verification_id': verification_id,
            'user_id': user.id,
            'similarity': similarity,
            'result': result,
            'method': metadata.get('method'),
            'confidence': metadata.get('confidence'),
            'metadata': metadata,
            'status': verification.status
        }
        
    except AccountVerification.DoesNotExist:
        logger.error(f"Verification {verification_id} not found")
        return {
            'success': False,
            'error': 'Verification not found'
        }
        
    except Exception as e:
        logger.exception(f"Enhanced face matching failed for verification {verification_id}: {e}")
        
        # Retry on failure
        try:
            raise self.retry(exc=e, countdown=60)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for verification {verification_id}")
            
            # Mark as requiring manual review
            try:
                verification = AccountVerification.objects.get(id=verification_id)
                if verification.status == 'pending':
                    verification.notes = f'Face matching error: {str(e)[:200]}. Manual review required.'
                    verification.save()
            except Exception:
                pass
            
            return {
                'success': False,
                'error': str(e)
            }


@shared_task
def complete_verification_v2(verification_id):
    """
    Complete verification process combining OCR and face matching results.
    
    Args:
        verification_id: ID of the AccountVerification to finalize
    """
    from users.models import AccountVerification
    from notifications.models import Notification
    
    try:
        logger.info(f"Finalizing verification {verification_id}")
        
        verification = AccountVerification.objects.get(id=verification_id)
        user = verification.user
        
        # Check if verification is already finalized
        if verification.status in ['approved', 'rejected']:
            logger.info(f"Verification {verification_id} already finalized: {verification.status}")
            return {
                'success': True,
                'status': verification.status
            }
        
        # If still pending, require manual review
        if verification.status == 'pending':
            Notification.objects.create(
                user=user,
                message="Your ID verification is being reviewed. You will be notified once complete.",
                notif_type="verification_pending"
            )
            
            logger.info(f"Verification {verification_id} requires manual review")
            return {
                'success': True,
                'status': 'manual_review_required'
            }
        
        # Update user verification status if approved
        if verification.status == 'approved':
            user.is_verified = True
            user.save()
            
            Notification.objects.create(
                user=user,
                message="Congratulations! Your account has been verified successfully.",
                notif_type="verification_approved"
            )
            
            logger.info(f"User {user.id} verified successfully")
        
        return {
            'success': True,
            'verification_id': verification_id,
            'status': verification.status,
            'user_verified': user.is_verified
        }
        
    except Exception as e:
        logger.exception(f"Error finalizing verification {verification_id}: {e}")
        return {
            'success': False,
            'error': str(e)
        }
