"""
Simplified Admin Views for Identity Verification
No auto-accept/reject logic - just display data
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from users.models import AccountVerification, CustomUser, VerificationLog
import logging
import json
import os
from django.conf import settings

logger = logging.getLogger(__name__)


class UserVerificationDetailSimpleView(LoginRequiredMixin, DetailView):
    """Simplified verification detail view - just shows data comparison"""
    model = AccountVerification
    template_name = 'admin_dashboard/user_verification_detail_simple.html'
    context_object_name = 'verification'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        verification = self.object
        user = verification.user
        
        # Get latest OCR data
        ocr_data = {}
        try:
            latest_log = VerificationLog.objects.filter(user=user).latest('created_at')
            if latest_log.extracted_data:
                ocr_data = latest_log.extracted_data
                logger.info(f"Loaded OCR data for user {user.id}: {list(ocr_data.keys())}")
        except VerificationLog.DoesNotExist:
            logger.info(f"No VerificationLog found for user {user.id}")
        
        context['ocr_data'] = ocr_data
        
        # Get PhilSys verification data
        philsys_data = {}
        try:
            # Check VerificationLog for PhilSys web verification data
            if latest_log and latest_log.extracted_data and 'philsys_web' in latest_log.extracted_data:
                philsys_web = latest_log.extracted_data['philsys_web']
                
                # Handle both old and new data structures
                # New structure: philsys_web.data contains the fields
                # Old structure: philsys_web directly contains the fields
                data_source = philsys_web.get('data', philsys_web)
                
                philsys_data = {
                    'verified': philsys_web.get('verified', False),
                    'last_name': data_source.get('last_name'),
                    'first_name': data_source.get('first_name'),
                    'middle_name': data_source.get('middle_name'),
                    'suffix': data_source.get('suffix'),
                    'name': data_source.get('name'),
                    'sex': data_source.get('sex'),
                    'date_of_birth': data_source.get('date_of_birth'),
                    'place_of_birth': data_source.get('place_of_birth'),
                    'pcn': data_source.get('pcn'),
                    'date_of_issuance': data_source.get('date_of_issuance'),
                    'best_capture_finger': data_source.get('best_capture_finger'),
                    'reason': philsys_web.get('reason'),
                    'verified_at': latest_log.created_at
                }
                logger.info(f"Loaded PhilSys web data: {list(philsys_data.keys())}")
        except Exception as e:
            logger.error(f"Error loading PhilSys data: {e}")
        
        context['philsys_data'] = philsys_data
        
        # Get face recognition data
        face_data = {}
        try:
            # Get the latest verification log with similarity score
            face_log = VerificationLog.objects.filter(
                user=user,
                similarity_score__isnull=False
            ).order_by('-created_at').first()
            
            if face_log:
                face_data = {
                    'similarity_score': face_log.similarity_score,
                    'verified_at': face_log.created_at,
                    'result': face_log.result,
                    'notes': face_log.notes
                }
                logger.info(f"Loaded face recognition data for user {user.id}: score={face_log.similarity_score}")
        except Exception as e:
            logger.error(f"Error loading face recognition data: {e}")
        
        context['face_data'] = face_data
        
        return context


@login_required
@require_POST
def approve_verification_simple(request, pk):
    """Approve verification - no auto-logic, just manual approval"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)
    
    try:
        verification = AccountVerification.objects.get(pk=pk)
        user = verification.user
        
        # Update verification status
        verification.status = 'approved'
        verification.reviewed_by = request.user
        verification.reviewed_at = timezone.now()
        verification.save()
        
        # Update user verification status
        user.identity_verification_status = 'verified'
        user.verification_status = 'verified'  # Update this field too
        user.is_verified = True
        user.save()
        
        # Send notification to user
        from notifications.models import Notification
        Notification.objects.create(
            user=user,
            message=f"🎉 Great news! Your identity verification has been approved by {request.user.get_full_name() or request.user.username}. You now have a verified badge on your profile and can access all platform features.",
            notif_type="verification_approved"
        )
        
        logger.info(f"Verification {pk} approved by {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'message': 'Verification approved successfully'
        })
        
    except AccountVerification.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Verification not found'}, status=404)
    except Exception as e:
        logger.exception(f"Error approving verification {pk}: {e}")
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@require_POST
def reject_verification_simple(request, pk):
    """Reject verification with reason"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)
    
    try:
        verification = AccountVerification.objects.get(pk=pk)
        user = verification.user
        
        # Get rejection reason from request
        data = json.loads(request.body)
        reason = data.get('reason', 'No reason provided')
        
        # Update verification status
        verification.status = 'rejected'
        verification.reviewed_by = request.user
        verification.rejection_reason = reason
        verification.reviewed_at = timezone.now()
        verification.save()
        
        # Update user verification status
        user.identity_verification_status = 'rejected'
        user.verification_status = 'failed'  # Update this field too
        user.is_verified = False
        user.save()
        
        # Send notification to user
        from notifications.models import Notification
        Notification.objects.create(
            user=user,
            message=f"❌ Your identity verification was rejected by {request.user.get_full_name() or request.user.username}. Reason: {reason}. Please review the feedback carefully and submit a new verification request with the required corrections.",
            notif_type="verification_rejected"
        )
        
        logger.info(f"Verification {pk} rejected by {request.user.username}: {reason}")
        
        return JsonResponse({
            'success': True,
            'message': 'Verification rejected successfully'
        })
        
    except AccountVerification.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Verification not found'}, status=404)
    except Exception as e:
        logger.exception(f"Error rejecting verification {pk}: {e}")
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@require_POST
def reprocess_ocr_simple(request, pk):
    """Re-run OCR extraction only - no verification logic"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)
    
    try:
        verification = AccountVerification.objects.get(pk=pk)
        
        # Check if verification has ID image
        if not verification.id_image_front:
            return JsonResponse({
                'success': False,
                'message': 'Verification has no ID image uploaded'
            }, status=400)
        
        # Trigger OCR extraction task (using enhanced version)
        from users.tasks_verification import verify_id_with_ocr_v2
        
        task = verify_id_with_ocr_v2.delay(verification.id)
        
        logger.info(f"OCR extraction started for verification {verification.id}, task {task.id}")
        
        return JsonResponse({
            'success': True,
            'message': 'OCR extraction started',
            'task_id': task.id
        })
        
    except AccountVerification.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Verification not found'}, status=404)
    except Exception as e:
        logger.exception(f"Error reprocessing OCR for verification {pk}: {e}")
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        }, status=500)


@login_required
@require_POST
def verify_philsys_simple(request, pk):
    """
    Trigger offline PhilSys ID verification (QR + OCR + Face matching)
    Uses the new auto_verify_philsys task instead of Playwright portal automation
    """
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)
    
    try:
        verification = AccountVerification.objects.get(pk=pk)
        user = verification.user
        
        # Check if verification has required images
        if not verification.id_image_back:
            return JsonResponse({
                'success': False,
                'message': 'No ID back image found. Verification requires ID back (with QR code).'
            }, status=400)
        
        if not verification.id_image_front:
            return JsonResponse({
                'success': False,
                'message': 'No ID front image found. Verification requires ID front.'
            }, status=400)
        
        if not verification.selfie_image:
            return JsonResponse({
                'success': False,
                'message': 'No selfie image found. Verification requires selfie for face matching.'
            }, status=400)
        
        # Import the new offline verification task
        from users.tasks_philsys_auto import auto_verify_philsys
        
        # Queue Celery task for offline verification (QR + OCR + Face)
        result = auto_verify_philsys.delay(verification_id=verification.id)
        
        return JsonResponse({
            'success': True,
            'message': f'Offline verification queued! Task ID: {result.id}\n\nProcessing: QR + OCR + Face matching\nTime: 30s - 5min (background)\n\nUser will receive notification when complete.',
            'task_id': result.id
        })
        
    except AccountVerification.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Verification not found'}, status=404)
    except Exception as e:
        logger.exception(f"Error starting offline verification for {pk}: {e}")
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        }, status=500)
