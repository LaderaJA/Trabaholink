from django.db import models
from django.contrib.auth import get_user_model
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json

CustomUser = get_user_model()

class Notification(models.Model):
    NOTIF_TYPES = [
        ("job_post", "New Job Posting"),
        ("announcement", "New Announcement"),
        ("message", "New Message"),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="notifications")
    message = models.TextField()
    notif_type = models.CharField(max_length=20, choices=NOTIF_TYPES)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Send real-time notification
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"notifications_{self.user.id}",
            {"type": "send_notification", "message": {"message": self.message, "type": self.notif_type}},
        )

