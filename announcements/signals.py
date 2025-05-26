from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from announcements.models import Announcement
from notifications.models import Notification

CustomUser = get_user_model()

@receiver(post_save, sender=Announcement)
def notify_users_about_announcement(sender, instance, created, **kwargs):
    if created:
        for user in CustomUser.objects.exclude(id=instance.posted_by_id):
            Notification.objects.create(
                user=user,
                notif_type="announcement",
                object_id=instance.id,
                message=f"New announcement: {instance.title}",
            )
