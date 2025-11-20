"""
Activity Logger for TrabahoLink
Tracks user activities across the platform
"""
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone


class ActivityLog(models.Model):
    """
    Tracks user activities across the platform
    """
    ACTIVITY_TYPES = [
        # Job-related activities
        ('job_posted', 'Posted a Job'),
        ('job_updated', 'Updated a Job'),
        ('job_deleted', 'Deleted a Job'),
        ('job_applied', 'Applied to a Job'),
        
        # Application-related
        ('application_submitted', 'Submitted Application'),
        ('application_accepted', 'Application Accepted'),
        ('application_rejected', 'Application Rejected'),
        
        # Contract-related
        ('contract_created', 'Contract Created'),
        ('contract_signed', 'Signed Contract'),
        ('contract_started', 'Started Working'),
        ('contract_completed', 'Completed Contract'),
        ('contract_cancelled', 'Cancelled Contract'),
        
        # Service-related
        ('service_created', 'Created Service'),
        ('service_updated', 'Updated Service'),
        ('service_deleted', 'Deleted Service'),
        
        # Feedback-related
        ('feedback_given', 'Gave Feedback'),
        ('feedback_received', 'Received Feedback'),
        
        # Profile-related
        ('profile_updated', 'Updated Profile'),
        ('skill_added', 'Added Skill'),
        ('skill_verified', 'Skill Verified'),
        
        # Payment-related
        ('payment_sent', 'Payment Sent'),
        ('payment_received', 'Payment Received'),
    ]
    
    user = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.CASCADE,
        related_name='activity_logs'
    )
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPES)
    description = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    
    # Generic relation to any model
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Additional metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp', 'user']),
            models.Index(fields=['user', 'activity_type']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_activity_type_display()} at {self.timestamp}"
    
    @property
    def icon(self):
        """Return Bootstrap icon class for activity type"""
        icon_map = {
            'job_posted': 'bi-briefcase-fill',
            'job_updated': 'bi-pencil-square',
            'job_deleted': 'bi-trash-fill',
            'job_applied': 'bi-file-earmark-text-fill',
            'application_submitted': 'bi-send-fill',
            'application_accepted': 'bi-check-circle-fill',
            'application_rejected': 'bi-x-circle-fill',
            'contract_created': 'bi-file-earmark-plus-fill',
            'contract_signed': 'bi-pen-fill',
            'contract_started': 'bi-play-circle-fill',
            'contract_completed': 'bi-check2-circle',
            'contract_cancelled': 'bi-x-octagon-fill',
            'service_created': 'bi-tools',
            'service_updated': 'bi-gear-fill',
            'service_deleted': 'bi-trash-fill',
            'feedback_given': 'bi-chat-left-text-fill',
            'feedback_received': 'bi-chat-right-text-fill',
            'profile_updated': 'bi-person-fill',
            'skill_added': 'bi-star-fill',
            'skill_verified': 'bi-patch-check-fill',
            'payment_sent': 'bi-cash-coin',
            'payment_received': 'bi-cash-stack',
        }
        return icon_map.get(self.activity_type, 'bi-circle-fill')
    
    @property
    def color_class(self):
        """Return color class for activity type"""
        color_map = {
            'job_posted': 'primary',
            'job_updated': 'info',
            'job_deleted': 'danger',
            'job_applied': 'success',
            'application_submitted': 'primary',
            'application_accepted': 'success',
            'application_rejected': 'danger',
            'contract_created': 'primary',
            'contract_signed': 'success',
            'contract_started': 'info',
            'contract_completed': 'success',
            'contract_cancelled': 'danger',
            'service_created': 'primary',
            'service_updated': 'info',
            'service_deleted': 'danger',
            'feedback_given': 'primary',
            'feedback_received': 'success',
            'profile_updated': 'info',
            'skill_added': 'primary',
            'skill_verified': 'success',
            'payment_sent': 'warning',
            'payment_received': 'success',
        }
        return color_map.get(self.activity_type, 'secondary')


# Helper function to log activities
def log_activity(user, activity_type, description, related_object=None, metadata=None):
    """
    Helper function to create activity logs
    
    Args:
        user: CustomUser instance
        activity_type: str from ACTIVITY_TYPES choices
        description: str description of the activity
        related_object: Optional model instance related to this activity
        metadata: Optional dict with additional metadata
    
    Returns:
        ActivityLog instance
    """
    activity_data = {
        'user': user,
        'activity_type': activity_type,
        'description': description,
        'metadata': metadata or {},
    }
    
    if related_object:
        activity_data['content_object'] = related_object
    
    return ActivityLog.objects.create(**activity_data)
