"""
Activity logging signals for job-related actions
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from users.activity_logger import log_activity


@receiver(post_save, sender='jobs.Job')
def log_job_activity(sender, instance, created, **kwargs):
    """Log job creation and updates"""
    if created:
        log_activity(
            user=instance.owner,
            activity_type='job_posted',
            description=f"Posted a new job: {instance.title}",
            related_object=instance,
            metadata={'job_id': instance.id, 'job_title': instance.title}
        )


@receiver(post_save, sender='jobs.JobApplication')
def log_application_activity(sender, instance, created, **kwargs):
    """Log job application submissions"""
    if created:
        log_activity(
            user=instance.worker,
            activity_type='job_applied',
            description=f"Applied to: {instance.job.title}",
            related_object=instance,
            metadata={'job_id': instance.job.id, 'job_title': instance.job.title}
        )
    else:
        # Log status changes
        if instance.status == 'accepted':
            log_activity(
                user=instance.worker,
                activity_type='application_accepted',
                description=f"Application accepted for: {instance.job.title}",
                related_object=instance,
                metadata={'job_id': instance.job.id, 'job_title': instance.job.title}
            )
        elif instance.status == 'rejected':
            log_activity(
                user=instance.worker,
                activity_type='application_rejected',
                description=f"Application rejected for: {instance.job.title}",
                related_object=instance,
                metadata={'job_id': instance.job.id, 'job_title': instance.job.title}
            )


@receiver(post_save, sender='jobs.Contract')
def log_contract_activity(sender, instance, created, **kwargs):
    """Log contract-related activities"""
    if created:
        # Log for both client and worker
        log_activity(
            user=instance.client,
            activity_type='contract_created',
            description=f"Created contract for: {instance.job.title}",
            related_object=instance,
            metadata={'contract_id': instance.id, 'job_title': instance.job.title}
        )
        log_activity(
            user=instance.worker,
            activity_type='contract_created',
            description=f"Received contract for: {instance.job.title}",
            related_object=instance,
            metadata={'contract_id': instance.id, 'job_title': instance.job.title}
        )
    else:
        # Log status changes
        if instance.status == 'Finalized':
            log_activity(
                user=instance.worker,
                activity_type='contract_signed',
                description=f"Signed contract for: {instance.job.title}",
                related_object=instance,
                metadata={'contract_id': instance.id, 'job_title': instance.job.title}
            )
        elif instance.status == 'In Progress':
            log_activity(
                user=instance.worker,
                activity_type='contract_started',
                description=f"Started working on: {instance.job.title}",
                related_object=instance,
                metadata={'contract_id': instance.id, 'job_title': instance.job.title}
            )
        elif instance.status == 'Completed':
            # Log for both client and worker
            log_activity(
                user=instance.worker,
                activity_type='contract_completed',
                description=f"Completed contract for: {instance.job.title}",
                related_object=instance,
                metadata={'contract_id': instance.id, 'job_title': instance.job.title}
            )
            log_activity(
                user=instance.client,
                activity_type='contract_completed',
                description=f"Contract completed: {instance.job.title}",
                related_object=instance,
                metadata={'contract_id': instance.id, 'job_title': instance.job.title}
            )
        elif instance.status == 'Cancelled':
            log_activity(
                user=instance.client,
                activity_type='contract_cancelled',
                description=f"Cancelled contract for: {instance.job.title}",
                related_object=instance,
                metadata={'contract_id': instance.id, 'job_title': instance.job.title}
            )


@receiver(post_save, sender='jobs.Feedback')
def log_feedback_activity(sender, instance, created, **kwargs):
    """Log feedback submissions"""
    if created:
        log_activity(
            user=instance.giver,
            activity_type='feedback_given',
            description=f"Gave feedback for contract (Rating: {instance.rating}/5)",
            related_object=instance,
            metadata={
                'contract_id': instance.contract.id,
                'rating': instance.rating,
                'receiver': instance.receiver.username
            }
        )
        log_activity(
            user=instance.receiver,
            activity_type='feedback_received',
            description=f"Received feedback (Rating: {instance.rating}/5)",
            related_object=instance,
            metadata={
                'contract_id': instance.contract.id,
                'rating': instance.rating,
                'giver': instance.giver.username
            }
        )
