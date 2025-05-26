from django.db.models.signals import post_save
from django.dispatch import receiver
from jobs.models import JobApplication
from notifications.models import Notification

@receiver(post_save, sender=JobApplication)
def notify_job_owner_on_application(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            user=instance.job.owner,
            notif_type="job_post",
            object_id=instance.job.id,
            message=f"New application from {instance.worker.username} for your job: {instance.job.title}",
        )
