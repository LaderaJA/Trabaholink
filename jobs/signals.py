from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from jobs.models import JobApplication, Contract
from notifications.models import Notification
from datetime import datetime, timedelta
from django.utils import timezone

@receiver(post_save, sender=JobApplication)
def notify_job_owner_on_application(sender, instance, created, **kwargs):
    """Notify job owner when someone applies, with real-time applicant count update"""
    if created:
        # Get current applicant count
        applicant_count = instance.job.applications.count()
        
        # Notify job owner - link to employer dashboard
        Notification.objects.create(
            user=instance.job.owner,
            notif_type="new_application_received",
            object_id=instance.job.id,
            message=f"🎯 New application from {instance.worker.get_full_name() or instance.worker.username} for '{instance.job.title}'! You now have {applicant_count} applicant{'s' if applicant_count != 1 else ''}.",
        )
        
        # Notify applicant - link to worker dashboard
        Notification.objects.create(
            user=instance.worker,
            notif_type="application_submitted",
            object_id=instance.id,
            message=f"✅ Your application for '{instance.job.title}' has been submitted successfully! The employer will review it soon.",
        )


@receiver(post_save, sender=Contract)
def notify_contract_schedule_updates(sender, instance, created, **kwargs):
    """Notify users about contract schedule-related events"""
    
    # Skip if contract doesn't have a start date yet
    if not instance.start_date:
        return
    
    # Only send notifications for active contracts
    if instance.status not in ['Accepted', 'In Progress', 'Finalized', 'Awaiting Review']:
        return
    
    # Notification 1: New contract scheduled (only when first created with dates)
    if created and instance.start_date:
        # Notify worker about new scheduled contract
        Notification.objects.create(
            user=instance.worker,
            notif_type="schedule_new",
            object_id=instance.id,
            message=f"📅 New contract scheduled: '{instance.job.title}' starting {instance.start_date.strftime('%b %d, %Y')}. Check your calendar to avoid conflicts.",
        )
        
        # Notify client/employer
        Notification.objects.create(
            user=instance.client,
            notif_type="schedule_new",
            object_id=instance.id,
            message=f"📅 Contract scheduled with {instance.worker.get_full_name() or instance.worker.username} for '{instance.job.title}' starting {instance.start_date.strftime('%b %d, %Y')}.",
        )
        
        # Check for schedule conflicts for the worker
        from .schedule_utils import check_schedule_conflicts
        has_conflict, conflicting_contracts, warning_message = check_schedule_conflicts(
            worker_id=instance.worker.id,
            start_date=instance.start_date,
            end_date=instance.end_date,
            start_time=instance.start_time,
            end_time=instance.end_time,
            exclude_contract_id=instance.id
        )
        
        if has_conflict:
            Notification.objects.create(
                user=instance.worker,
                notif_type="schedule_conflict",
                object_id=instance.id,
                message=f"⚠️ Schedule Conflict Warning: Your new contract '{instance.job.title}' overlaps with {len(conflicting_contracts)} existing contract(s). Please review your schedule.",
            )
    
    # Note: Start/end date reminders are handled by the daily Celery task
    # to avoid duplicate notifications on every save
