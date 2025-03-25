from django.db import models
from django.conf import settings  
from django.db.models.signals import post_save
from django.dispatch import receiver
from notifications.utils import send_notification_email
from users.models import CustomUser
from django.apps import apps
from django.contrib.auth import get_user_model

CustomUser = get_user_model()

@receiver(post_save, sender=None) 
def notify_users_about_announcement(sender, instance, created, **kwargs):
    if created:
        Announcement = apps.get_model('announcements', 'Announcement') 
        if isinstance(instance, Announcement): 
            all_users = CustomUser.objects.all()
            for user in all_users:
                subject = "New Announcement from Trabaholink!"
                message = f"{instance.title}\n\n{instance.description}"
                send_notification_email(subject, message, user.email)  

class Announcement(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    image = models.ImageField(upload_to="announcements/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    posted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return self.title
