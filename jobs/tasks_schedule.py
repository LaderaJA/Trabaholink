"""
Celery tasks for contract schedule notifications and reminders.
"""
from celery import shared_task
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q
from jobs.models import Contract
from notifications.models import Notification
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_daily_schedule_reminders():
    """
    Daily task to check contracts and send reminders for:
    - Contracts starting tomorrow
    - Contracts ending in 3 days
    - Contracts ending tomorrow
    """
    today = timezone.now().date()
    tomorrow = today + timedelta(days=1)
    three_days = today + timedelta(days=3)
    
    logger.info(f"Running daily schedule reminders for {today}")
    
    # Get active contracts
    active_contracts = Contract.objects.filter(
        status__in=['Accepted', 'In Progress', 'Finalized', 'Awaiting Review']
    ).select_related('worker', 'client', 'job')
    
    # Contracts starting tomorrow
    starting_tomorrow = active_contracts.filter(start_date=tomorrow)
    
    for contract in starting_tomorrow:
        # Check if notification already sent today
        existing_notification = Notification.objects.filter(
            user=contract.worker,
            object_id=contract.id,
            notif_type="schedule_reminder",
            created_at__date=today
        ).exists()
        
        if not existing_notification:
            Notification.objects.create(
                user=contract.worker,
                notif_type="schedule_reminder",
                object_id=contract.id,
                message=f"⏰ Reminder: Your contract '{contract.job.title}' starts tomorrow ({contract.start_date.strftime('%b %d, %Y')}). Get ready!",
            )
            
            Notification.objects.create(
                user=contract.client,
                notif_type="schedule_reminder",
                object_id=contract.id,
                message=f"⏰ Reminder: Contract with {contract.worker.get_full_name() or contract.worker.username} for '{contract.job.title}' starts tomorrow.",
            )
            
            logger.info(f"Sent start reminder for contract {contract.id}")
    
    # Contracts ending in 3 days
    ending_in_three = active_contracts.filter(end_date=three_days)
    
    for contract in ending_in_three:
        existing_notification = Notification.objects.filter(
            user=contract.worker,
            object_id=contract.id,
            notif_type="schedule_deadline",
            created_at__date=today,
            message__contains="3 days"
        ).exists()
        
        if not existing_notification:
            Notification.objects.create(
                user=contract.worker,
                notif_type="schedule_deadline",
                object_id=contract.id,
                message=f"⏳ Deadline Alert: Your contract '{contract.job.title}' ends in 3 days ({contract.end_date.strftime('%b %d, %Y')}). Please complete all work.",
            )
            
            logger.info(f"Sent 3-day deadline reminder for contract {contract.id}")
    
    # Contracts ending tomorrow
    ending_tomorrow = active_contracts.filter(end_date=tomorrow)
    
    for contract in ending_tomorrow:
        existing_notification = Notification.objects.filter(
            user=contract.worker,
            object_id=contract.id,
            notif_type="schedule_deadline",
            created_at__date=today,
            message__contains="tomorrow"
        ).exists()
        
        if not existing_notification:
            Notification.objects.create(
                user=contract.worker,
                notif_type="schedule_deadline",
                object_id=contract.id,
                message=f"🚨 Urgent: Your contract '{contract.job.title}' ends tomorrow! Please ensure all deliverables are submitted.",
            )
            
            Notification.objects.create(
                user=contract.client,
                notif_type="schedule_deadline",
                object_id=contract.id,
                message=f"🚨 Reminder: Contract with {contract.worker.get_full_name() or contract.worker.username} for '{contract.job.title}' ends tomorrow.",
            )
            
            logger.info(f"Sent urgent deadline reminder for contract {contract.id}")
    
    logger.info(f"Daily schedule reminders completed. Start: {starting_tomorrow.count()}, End-3d: {ending_in_three.count()}, End-1d: {ending_tomorrow.count()}")
    
    return {
        'success': True,
        'contracts_starting': starting_tomorrow.count(),
        'contracts_ending_3d': ending_in_three.count(),
        'contracts_ending_1d': ending_tomorrow.count(),
    }


@shared_task
def check_contract_conflicts(contract_id):
    """
    Check for schedule conflicts for a specific contract.
    Called when a contract is created or updated with new dates.
    """
    try:
        contract = Contract.objects.select_related('worker', 'client', 'job').get(id=contract_id)
        
        if not contract.start_date:
            return {'success': False, 'reason': 'No start date'}
        
        from jobs.schedule_utils import check_schedule_conflicts
        
        has_conflict, conflicting_contracts, warning_message = check_schedule_conflicts(
            worker_id=contract.worker.id,
            start_date=contract.start_date,
            end_date=contract.end_date,
            start_time=contract.start_time,
            end_time=contract.end_time,
            exclude_contract_id=contract.id
        )
        
        if has_conflict:
            # Send notification about conflict
            Notification.objects.create(
                user=contract.worker,
                notif_type="schedule_conflict",
                object_id=contract.id,
                message=f"⚠️ Schedule Conflict: '{contract.job.title}' overlaps with {len(conflicting_contracts)} existing contract(s). Please review your calendar.",
            )
            
            logger.warning(f"Schedule conflict detected for contract {contract_id}")
            
            return {
                'success': True,
                'has_conflict': True,
                'conflicting_count': len(conflicting_contracts)
            }
        
        return {'success': True, 'has_conflict': False}
        
    except Contract.DoesNotExist:
        logger.error(f"Contract {contract_id} not found")
        return {'success': False, 'reason': 'Contract not found'}
