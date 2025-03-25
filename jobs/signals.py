from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Job
from notifications.models import Notification

@receiver(post_save, sender=Job)
def notify_users_about_new_job(sender, instance, created, **kwargs):
    if created:  
        nearby_users = instance.get_nearby_users() 
        for user in nearby_users:
            Notification.objects.create(
                user=user,
                message=f"New job posted near you: {instance.title}",
                notification_type="job_post"
            )
