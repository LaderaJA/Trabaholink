from django.db import models
from django.core.exceptions import ValidationError
from users.models import CustomUser
from jobs.models import Job


class Report(models.Model):
    """
    Enhanced Report model for tracking reports against users or job postings.
    Each report must target either a user OR a post, not both.
    """
    reporter = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='reports_made',
        help_text="User who submitted the report",
        null=True,
        blank=True
    )
    reported_user = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='reports_received', 
        null=True, 
        blank=True,
        help_text="User being reported (if applicable)"
    )
    reported_post = models.ForeignKey(
        Job, 
        on_delete=models.CASCADE, 
        related_name='reports_received', 
        null=True, 
        blank=True,
        help_text="Job posting being reported (if applicable)"
    )
    reason = models.TextField(help_text="Reason for the report")
    screenshot = models.ImageField(
        upload_to='reports/screenshots/',
        null=True,
        blank=True,
        help_text="Screenshot or evidence supporting the report"
    )
    status = models.CharField(
        max_length=20, 
        choices=[
            ('pending', 'Pending'), 
            ('reviewed', 'Reviewed'),
            ('resolved', 'Resolved'),
            ('dismissed', 'Dismissed')
        ],
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports_reviewed',
        help_text="Admin who reviewed this report"
    )
    admin_notes = models.TextField(blank=True, help_text="Internal notes from admin")

    class Meta:
        unique_together = ('reporter', 'reported_user', 'reported_post')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['reported_user', 'status']),
            models.Index(fields=['reported_post', 'status']),
            models.Index(fields=['created_at']),
        ]

    def clean(self):
        """Ensure a report targets either a user OR a post, not both or neither."""
        if self.reported_user and self.reported_post:
            raise ValidationError("A report cannot target both a user and a post. Choose one.")
        if not self.reported_user and not self.reported_post:
            raise ValidationError("A report must target either a user or a post.")
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        if self.reported_user:
            return f"Report by {self.reporter.username} against user {self.reported_user.username}"
        elif self.reported_post:
            return f"Report by {self.reporter.username} against post '{self.reported_post.title}'"
        return f"Report #{self.pk}"
    
    @property
    def report_target(self):
        """Returns the target of the report (user or post)"""
        return self.reported_user or self.reported_post
    
    @property
    def report_type(self):
        """Returns the type of report"""
        if self.reported_user:
            return "User"
        elif self.reported_post:
            return "Post"
        return "Unknown"
