"""Main verification pipeline orchestrating OCR, QR, and face matching."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Dict, Optional

from django.db import transaction

from users.models import CustomUser, VerificationLog

from .face_match import (
    SIMILARITY_THRESHOLD_MANUAL,
    SIMILARITY_THRESHOLD_VERIFIED,
    FaceMatchError,
    compute_similarity,
)
from .ocr import extract_id_text
from .qr import extract_qr_data
from .types import VerificationResult
from .utils import load_image, merge_data, save_temp_image
from .data_validator import DataValidator

# Try to import enhanced OCR
try:
    from .ocr_enhanced import extract_id_text_enhanced
    ENHANCED_OCR_AVAILABLE = True
except ImportError:
    ENHANCED_OCR_AVAILABLE = False

# Try to import PhilSys-specific OCR
try:
    from .ocr_philsys import extract_philsys_text
    PHILSYS_OCR_AVAILABLE = True
except ImportError:
    PHILSYS_OCR_AVAILABLE = False

# Try to import color-aware PhilSys OCR (for hologram overlays)
# DISABLED: Causes timeouts - needs debugging
# try:
#     from .ocr_philsys_color import extract_philsys_color_text
#     PHILSYS_COLOR_OCR_AVAILABLE = True
# except ImportError:
#     PHILSYS_COLOR_OCR_AVAILABLE = False
PHILSYS_COLOR_OCR_AVAILABLE = False  # Disabled - use grayscale PhilSys OCR instead

logger = logging.getLogger(__name__)


@dataclass
class VerificationConfig:
    """Runtime configuration for the verification pipeline."""

    enable_ocr: bool = True
    enable_qr: bool = True
    enable_face_match: bool = True
    enable_data_validation: bool = True
    enable_philsys_verification: bool = True  # New: PhilSys web verification
    use_enhanced_ocr: bool = True  # New: Use enhanced OCR if available
    strict_validation: bool = False
    verified_threshold: float = SIMILARITY_THRESHOLD_VERIFIED
    manual_review_threshold: float = SIMILARITY_THRESHOLD_MANUAL
    process_type: str = "auto"


class VerificationPipeline:
    """Run the eKYC verification pipeline for a user."""

    def __init__(self, config: Optional[VerificationConfig] = None):
        self.config = config or VerificationConfig()

    def run(self, user: CustomUser) -> VerificationResult:
        if not user.id_image or not user.selfie_image:
            raise ValueError("User must upload both ID and selfie images before verification")

        extracted_data: Dict[str, str] = {}
        similarity_score: Optional[float] = None
        data_validation_passed: bool = True
        data_confidence: float = 0.0
        notes: list[str] = []
        
        # Initialize progress tracker
        from .progress_tracker import VerificationProgressTracker
        tracker = VerificationProgressTracker(user.id)
        tracker.update("starting", 5, "Verification started")

        # OCR extraction
        if self.config.enable_ocr:
            tracker.update("ocr", 10, "Extracting text from ID...")
            try:
                id_pil = load_image(user.id_image)
                
                # Check if this is a PhilSys ID
                id_type_lower = (user.id_type or '').lower()
                is_philsys = id_type_lower in ['philsys', 'philsys_id', 'national_id', 'philsys id', 'national id']
                
                # Use color-aware PhilSys OCR for PhilSys IDs (highest priority - handles hologram)
                if is_philsys and PHILSYS_COLOR_OCR_AVAILABLE:
                    logger.info("Using color-aware PhilSys OCR (handles hologram overlay)")
                    ocr_data = extract_philsys_color_text(id_pil)
                    notes.append("Color-aware PhilSys OCR used (handles rainbow hologram + color channels)")
                # Fallback to grayscale PhilSys OCR
                elif is_philsys and PHILSYS_OCR_AVAILABLE:
                    logger.info("Using grayscale PhilSys-optimized OCR")
                    ocr_data = extract_philsys_text(id_pil)
                    notes.append("PhilSys-optimized OCR used (multiple PSM modes + preprocessing)")
                # Use enhanced OCR if available and enabled
                elif self.config.use_enhanced_ocr and ENHANCED_OCR_AVAILABLE:
                    logger.info("Using enhanced OCR with EasyOCR + Tesseract")
                    ocr_data = extract_id_text_enhanced(id_pil, user.id_type)
                    notes.append("Enhanced OCR used (EasyOCR + Tesseract + preprocessing)")
                else:
                    logger.info("Using standard Tesseract OCR")
                    ocr_data = extract_id_text(id_pil, user.id_type)
                    notes.append("Standard OCR used (Tesseract only)")
                
                extracted_data = merge_data(ocr_data, extracted_data)
                
                # Log OCR confidence if available
                if 'ocr_confidence' in ocr_data:
                    notes.append(f"OCR confidence: {ocr_data['ocr_confidence']}")
                
                tracker.update("ocr", 30, f"Extracted {len(extracted_data)} fields from ID")
                    
            except Exception as exc:  # pragma: no cover - error path
                logger.exception("OCR extraction failed for user %s", user.pk)
                notes.append(f"OCR failure: {exc}")
                tracker.update("ocr", 30, "OCR extraction failed")

        # QR extraction
        philsys_qr_detected = False
        if self.config.enable_qr:
            tracker.update("qr", 40, "Scanning QR code...")
            try:
                if 'id_pil' not in locals():
                    id_pil = load_image(user.id_image)
                qr_data = extract_qr_data(id_pil)
                extracted_data = merge_data(extracted_data, qr_data)
                
                # Check if PhilSys ID detected
                from .philsys_qr import is_philsys_id
                if is_philsys_id(user.id_type) and qr_data:
                    philsys_qr_detected = True
                    notes.append("PhilSys QR code detected")
                    
            except Exception as exc:  # pragma: no cover - error path
                logger.exception("QR extraction failed for user %s", user.pk)
                notes.append(f"QR failure: {exc}")

        # Data Validation - Compare extracted data with profile
        if self.config.enable_data_validation and extracted_data:
            tracker.update("validation", 50, "Validating extracted data...")
            try:
                validator = DataValidator(strict_mode=self.config.strict_validation)
                validation_result = validator.validate(user, extracted_data)
                
                data_validation_passed = validation_result.is_valid
                data_confidence = validation_result.confidence_score
                
                notes.append(f"Data validation: {'PASSED' if data_validation_passed else 'FAILED'}")
                notes.append(f"Data confidence: {data_confidence:.2f}")
                notes.append(f"Matched fields: {', '.join(validation_result.matched_fields) if validation_result.matched_fields else 'None'}")
                
                if validation_result.mismatches:
                    notes.append("Data mismatches found:")
                    for mismatch in validation_result.mismatches:
                        notes.append(f"  - {mismatch}")
                
                if validation_result.warnings:
                    for warning in validation_result.warnings:
                        notes.append(f"Warning: {warning}")
                
                # Auto-fail if data validation failed
                if not data_validation_passed:
                    logger.warning(
                        "Data validation failed for user %s: confidence=%.2f, mismatches=%d",
                        user.pk, data_confidence, len(validation_result.mismatches)
                    )
            except Exception as exc:
                logger.exception("Data validation failed for user %s", user.pk)
                notes.append(f"Data validation error: {exc}")

        # Face matching
        temp_paths = []

        if self.config.enable_face_match:
            tracker.update("face_match", 60, "Comparing faces...")
            try:
                id_temp_source = id_pil if 'id_pil' in locals() else load_image(user.id_image)
                id_path, _ = save_temp_image(id_temp_source)
                temp_paths.append(id_path)
                selfie_pil = load_image(user.selfie_image)
                selfie_path, _ = save_temp_image(selfie_pil)
                temp_paths.append(selfie_path)
                similarity_score, debug_meta = compute_similarity(id_path, selfie_path)
                notes.append(f"Face match meta: {debug_meta}")
                tracker.update("face_match", 80, f"Face similarity: {similarity_score:.2f}" if similarity_score else "Face match completed")
            except FaceMatchError as exc:
                logger.warning("Face match unavailable for user %s: %s", user.pk, exc)
                notes.append(f"Face match error: {exc}")
            except Exception as exc:  # pragma: no cover - error path
                logger.exception("Unexpected error during face match for user %s", user.pk)
                notes.append(f"Face match failure: {exc}")
            finally:
                for path in temp_paths:
                    try:
                        os.remove(path)
                    except OSError:
                        logger.debug("Failed to remove temp file %s", path)

        status = self._determine_status(similarity_score, data_validation_passed, data_confidence)
        overall_score = similarity_score or 0.0

        with transaction.atomic():
            VerificationLog.objects.create(
                user=user,
                extracted_data=extracted_data,
                similarity_score=similarity_score,
                process_type=self.config.process_type,
                result=status,
                notes="\n".join(notes),
            )

            user.verification_status = status
            user.verification_score = similarity_score
            user.verification_log = "\n".join(notes)
            user.save(update_fields=["verification_status", "verification_score", "verification_log"])
            
            # Send notification if verification was automatically rejected
            if status == 'failed':
                from notifications.models import Notification
                
                # Determine rejection reason
                if not data_validation_passed:
                    reason = "The information on your ID document does not match your profile information."
                elif similarity_score is not None and similarity_score < self.config.manual_review_threshold:
                    reason = "The face in your selfie does not match the face on your ID document."
                else:
                    reason = "Your verification could not be completed."
                
                Notification.objects.create(
                    user=user,
                    message=f"Your identity verification was automatically rejected. Reason: {reason} Please review your submission and try again with correct information.",
                    notif_type="verification_rejected"
                )

        result = VerificationResult(
            user=user,
            status=status,
            similarity_score=similarity_score,
            extracted_data=extracted_data,
            verification_score=overall_score,
            notes="\n".join(notes),
        )
        
        # Mark as complete
        status_messages = {
            'verified': 'Verification approved!',
            'failed': 'Verification failed',
            'manual_review': 'Requires manual review',
            'pending': 'Verification pending'
        }
        tracker.complete(status, status_messages.get(status, 'Verification completed'))

        logger.info("Verification completed for user %s with status %s", user.pk, status)
        return result

    def _determine_status(
        self, 
        similarity_score: Optional[float],
        data_validation_passed: bool = True,
        data_confidence: float = 0.0
    ) -> str:
        """
        Determine verification status based on face similarity and data validation.
        
        Rules:
        1. If data validation failed -> 'failed' (auto-reject)
        2. If face similarity is None -> 'manual_review'
        3. If both face and data are good -> 'verified'
        4. If face is good but data is borderline -> 'manual_review'
        5. If face is borderline -> 'manual_review'
        6. Otherwise -> 'failed'
        """
        # Auto-fail if data validation failed
        if not data_validation_passed:
            logger.info("Status: failed (data validation failed)")
            return 'failed'
        
        # If no face similarity score, require manual review
        if similarity_score is None:
            logger.info("Status: manual_review (no face similarity score)")
            return 'manual_review'
        
        # Both face and data must be good for auto-verification
        if similarity_score >= self.config.verified_threshold:
            if data_confidence >= 0.70:  # High data confidence
                logger.info("Status: verified (face=%.2f, data=%.2f)", similarity_score, data_confidence)
                return 'verified'
            else:
                # Face is good but data confidence is borderline
                logger.info("Status: manual_review (face good but data borderline: %.2f)", data_confidence)
                return 'manual_review'
        
        # Face similarity is borderline
        if similarity_score >= self.config.manual_review_threshold:
            logger.info("Status: manual_review (face borderline: %.2f)", similarity_score)
            return 'manual_review'
        
        # Face similarity too low
        logger.info("Status: failed (face similarity too low: %.2f)", similarity_score)
        return 'failed'
