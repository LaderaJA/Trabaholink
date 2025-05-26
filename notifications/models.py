from django.db import models
from django.contrib.auth import get_user_model
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.urls import reverse

CustomUser = get_user_model()

class Notification(models.Model):
    NOTIF_TYPES = [
        ("job_post", "New Job Posting"),
        ("announcement", "New Announcement"),
        ("message", "New Message"),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="notifications")
    message = models.TextField()
    notif_type = models.CharField(max_length=30)  # Increased max_length to 30
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    object_id = models.IntegerField(null=True, blank=True)  # Unified ID field for related objects

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Send real-time notification
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"notifications_{self.user.id}",
            {"type": "send_notification", "message": {"message": self.message, "type": self.notif_type}},
        )

    @property
    def target_url(self):
        if self.notif_type == "announcement" and self.object_id:
            return reverse('announcements:announcement_detail', args=[self.object_id])
        elif self.notif_type == "job_post" and self.object_id:
            return reverse('jobs:job_detail', args=[self.object_id])
        elif self.notif_type == "message" and self.object_id:
            return reverse('messaging:conversation_detail', args=[self.object_id])
        return "#"

    def mark_as_read(self):
        self.is_read = True
        self.save(update_fields=['is_read'])

