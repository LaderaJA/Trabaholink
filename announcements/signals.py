import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from announcements.models import Announcement
from notifications.models import Notification

logger = logging.getLogger(__name__)
CustomUser = get_user_model()

@receiver(post_save, sender=Announcement)
def notify_users_about_announcement(sender, instance, created, **kwargs):
    if not isinstance(instance, Announcement):
        logger.warning("Skipping signal: Instance is not an Announcement.")
        return  # Prevent errors during migrations

    if created:
        logger.info(f"New announcement created: {instance.title}")
        all_users = CustomUser.objects.all()
        for user in all_users:
            Notification.objects.create(
                user=user,
                message=f"New announcement: {instance.title}",
                # notification_type="announcement"
            )
