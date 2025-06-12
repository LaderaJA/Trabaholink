from django.db import models
from django.contrib.auth import get_user_model
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.urls import reverse
from django.conf import settings

CustomUser = get_user_model()

class Notification(models.Model):
    NOTIF_TYPES = [
        ("job_post", "New Job Posting"),
        ("announcement", "New Announcement"),
        ("message", "New Message"),
        ("application", "New Job Application"),
        ("contract", "New Contract"),
        ("progress_log", "New Progress Log"),
        ("contract_update", "Contract Update"),
        ("job_application_update", "Job Application Update"),
        ("job_application_hire", "Job Application Hire"),
        ("job_application_deny", "Job Application Deny"),
        ("contract_draft_update", "Contract Draft Update"),
        ("contract_cancel", "Contract Cancel"),
        ("contract_accept", "Contract Accept"),
        ("contract_finalize", "Contract Finalize"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    message = models.TextField()
    notif_type = models.CharField(max_length=30) 
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    object_id = models.IntegerField(null=True, blank=True) 

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
        elif self.notif_type == "application" and self.object_id:
            return reverse('jobs:job_application_detail', args=[self.object_id])
        elif self.notif_type == "contract" and self.object_id:
            return reverse('jobs:contract_detail', args=[self.object_id])
        elif self.notif_type == "progress_log" and self.object_id:
            return reverse('jobs:progresslog_detail', args=[self.object_id])
        elif self.notif_type == "contract_update" and self.object_id:
            return reverse('jobs:contract_edit', args=[self.object_id])
        elif self.notif_type == "job_application_update" and self.object_id:
            return reverse('jobs:job_application_edit', args=[self.object_id])
        elif self.notif_type == "job_application_hire" and self.object_id:
            return reverse('jobs:job_application_hire', args=[self.object_id])
        elif self.notif_type == "job_application_deny" and self.object_id:
            return reverse('jobs:job_application_deny', args=[self.object_id])
        elif self.notif_type == "contract_draft_update" and self.object_id:
            return reverse('jobs:contract_draft_edit', args=[self.object_id])
        elif self.notif_type == "contract_cancel" and self.object_id:
            return reverse('jobs:contract_cancel', args=[self.object_id])
        elif self.notif_type == "contract_accept" and self.object_id:
            return reverse('jobs:accept_contract', args=[self.object_id])
        elif self.notif_type == "contract_finalize" and self.object_id:
            return reverse('jobs:finalize_contract', args=[self.object_id])
        return "#"

    @property
    def target_url_with_read(self):
        """Returns the target URL with an additional read parameter"""
        base_url = self.target_url
        if base_url != "#":
            return f"{base_url}?notification_id={self.id}"
        return base_url

    def mark_as_read(self):
        self.is_read = True
        self.save(update_fields=['is_read'])

    def __str__(self):
        return f"Notification for {self.user.username} at {self.created_at}"


