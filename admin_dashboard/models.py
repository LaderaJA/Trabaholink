from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

# Note: Report model has been moved to reports app
# Import it with: from reports.models import Report

# Flagged Chat Model
class FlaggedChat(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('reviewed', 'Reviewed'),
        ('resolved', 'Resolved'),
    ]

    chat_message = models.ForeignKey(
        'messaging.Conversation', 
        on_delete=models.CASCADE,
        related_name='flagged_chats'
    )
    flagged_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='flagged_chats')
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Flagged by {self.flagged_by} - {self.status}"

# Dashboard Settings Model (Optional for Admin Preferences)
class DashboardSettings(models.Model):
    admin_user = models.OneToOneField(User, on_delete=models.CASCADE)
    show_announcements = models.BooleanField(default=True)
    show_reports = models.BooleanField(default=True)
    show_flagged_chats = models.BooleanField(default=True)

    def __str__(self):
        return f"Settings for {self.admin_user.username}"

class ModeratedWord(models.Model):
    word = models.CharField(max_length=100, unique=True)
    flagged_count = models.PositiveIntegerField(default=0)
    is_banned = models.BooleanField(default=False)

    def __str__(self):
        return self.word

    @classmethod
    def get_banned_words(cls):
        """Fetch all banned words from the database."""
        return list(cls.objects.filter(is_banned=True).values_list('word', flat=True))

