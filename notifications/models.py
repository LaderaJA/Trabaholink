from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.urls import reverse
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

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
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    object_id = models.IntegerField(null=True, blank=True) 

    def save(self, *args, **kwargs):
        # Check if user has notification settings and if they want this type
        try:
            settings = self.user.notification_settings
            if not settings.should_notify(self.notif_type):
                return  # Don't save notification if user has disabled this type
        except (AttributeError, ObjectDoesNotExist):
            pass  # If no settings exist, create notification anyway
        
        super().save(*args, **kwargs)

        # Send real-time notification
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"notifications_{self.user.id}",
            {"type": "send_notification", "message": {"message": self.message, "type": self.notif_type}},
        )

    @property
    def target_url(self):
        """Return target URL with error handling for deleted objects"""
        if not self.object_id:
            return reverse('notifications:notification_list')

        try:
            from jobs.models import Contract, Job, JobApplication, Feedback

            type_map = {
                'announcement': ('announcements:announcement_detail', 'announcements.models', 'Announcement'),
                'job_post': ('jobs:job_detail', Job),
                'message': ('messaging:conversation_detail', 'messaging.models', 'Conversation'),
                # Dashboard-directed notifications
                'new_application_received': 'jobs:employer_dashboard',  # Employer gets notified -> employer dashboard
                'application_submitted': 'jobs:worker_dashboard',  # Worker confirmation -> worker dashboard
                # Schedule notifications
                'schedule_new': 'jobs:worker_dashboard',
                'schedule_conflict': 'jobs:worker_dashboard',
                'schedule_reminder': 'jobs:worker_dashboard',
                'schedule_deadline': 'jobs:worker_dashboard',
                # Application-related
                'application': ('jobs:job_application_detail', JobApplication),
                'application_update': ('jobs:job_application_detail', JobApplication),
                'job_application': ('jobs:job_application_detail', JobApplication),  # Added base job_application type
                'job_application_update': ('jobs:job_application_detail', JobApplication),
                'job_application_hire': ('jobs:job_application_detail', JobApplication),
                'job_application_deny': ('jobs:job_application_detail', JobApplication),
                # Contract-related
                'contract': ('jobs:contract_detail', Contract),
                'contract_update': ('jobs:contract_detail', Contract),
                'contract_updated': ('jobs:contract_negotiation', Contract),
                'contract_negotiation': ('jobs:contract_negotiation', Contract),
                'contract_draft_update': ('jobs:contract_negotiation', Contract),
                'contract_accept': ('jobs:contract_detail', Contract),
                'contract_accepted': ('jobs:contract_detail', Contract),
                'contract_acceptance': ('jobs:contract_detail', Contract),
                'contract_finalize': ('jobs:contract_detail', Contract),
                'contract_finalized': ('jobs:contract_detail', Contract),
                'contract_cancel': ('jobs:contract_detail', Contract),
                'contract_cancelled': ('jobs:contract_detail', Contract),
                'contract_completed': ('jobs:job_tracking', Contract),  # Direct to job tracking for review
                'contract_signature': ('jobs:contract_detail', Contract),
                'contract_start': ('jobs:job_tracking', Contract),
                'job_started': ('jobs:job_tracking', Contract),
                'progress_update': ('jobs:job_tracking', Contract),
                'progress_log': ('jobs:job_tracking', Contract),
                'job_completed': ('jobs:job_tracking', Contract),  # Direct to job tracking
                # Other
                'feedback': ('jobs:contract_feedback_detail', Feedback),
                'verification': 'users:ekyc_start',
                'verification_approved': 'users:profile_detail',
                'verification_rejected': 'users:ekyc_start',
            }

            target = type_map.get(self.notif_type)
            if not target:
                logger.warning(f"No URL mapping found for notification type: {self.notif_type}")
                return reverse('notifications:notification_list')

            # Handle simple string URLs (no object_id needed)
            if isinstance(target, str):
                try:
                    return reverse(target)
                except Exception as e:
                    logger.error(f"Error reversing URL '{target}': {e}")
                    return reverse('notifications:notification_list')
            
            # Handle tuple unpacking safely
            if len(target) == 2:
                url_name, model_info = target
            else:
                logger.error(f"Invalid target format for notification {self.id}: expected 2 values, got {len(target)}")
                return reverse('notifications:notification_list')
            
            if isinstance(model_info, tuple):
                if len(model_info) == 2:
                    module_path, model_name = model_info
                else:
                    logger.error(f"Invalid model_info format: expected 2 values, got {len(model_info)}")
                    return reverse('notifications:notification_list')
                try:
                    module = __import__(module_path, fromlist=[model_name])
                    model_cls = getattr(module, model_name)
                except (ImportError, AttributeError) as e:
                    logger.error(f"Error importing {module_path}.{model_name}: {e}")
                    return reverse('notifications:notification_list')
            else:
                model_cls = model_info

            # Check if object exists before creating URL
            try:
                if model_cls.objects.filter(pk=self.object_id).exists():
                    return reverse(url_name, args=[self.object_id])
                else:
                    logger.warning(f"Object {self.object_id} not found for notification {self.id} (type: {self.notif_type})")
                    # Return None to indicate broken link
                    return None
            except Exception as e:
                logger.error(f"Error checking object existence for notification {self.id}: {e}")
                return None

        except Exception as e:
            logger.error(f"Error getting notification target URL for notification {self.id}: {e}")

        return None

    @property
    def target_url_with_read(self):
        """Returns the notification list URL to mark as read before redirecting"""
        return reverse('notifications:notification_list') + f"?notification_id={self.id}"

    def mark_as_read(self):
        self.is_read = True
        self.save(update_fields=['is_read'])
    
    def archive(self):
        """Archive this notification"""
        self.is_archived = True
        self.save(update_fields=['is_archived'])
    
    @classmethod
    def auto_archive_old_notifications(cls, user, days=30):
        """Auto-archive notifications older than specified days"""
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=days)
        old_notifications = cls.objects.filter(
            user=user,
            created_at__lt=cutoff_date,
            is_archived=False
        )
        count = old_notifications.update(is_archived=True)
        return count
    
    @property
    def is_object_deleted(self):
        """Check if the related object has been deleted"""
        if not self.object_id:
            return False
        
        try:
            if self.notif_type == "announcement":
                from announcements.models import Announcement
                return not Announcement.objects.filter(id=self.object_id).exists()
            elif self.notif_type == "job_post":
                from jobs.models import Job
                return not Job.objects.filter(id=self.object_id).exists()
            elif self.notif_type == "message":
                from messaging.models import Conversation
                return not Conversation.objects.filter(id=self.object_id).exists()
            elif "application" in self.notif_type:
                from jobs.models import JobApplication
                return not JobApplication.objects.filter(id=self.object_id).exists()
            elif "contract" in self.notif_type:
                from jobs.models import Contract
                return not Contract.objects.filter(id=self.object_id).exists()
            elif self.notif_type == "progress_log":
                from jobs.models import ProgressLog
                return not ProgressLog.objects.filter(id=self.object_id).exists()
        except (ImportError, AttributeError, ValueError) as e:
            logger.warning(f"Error checking if notification object is deleted: {e}")
            return True
        
        return False
    
    def get_notif_type_display(self):
        """Return a human-readable notification type"""
        type_map = {
            'job_post': 'New Job',
            'announcement': 'Announcement',
            'message': 'New Message',
            'new_application_received': 'New Application',
            'application_submitted': 'Application Submitted',
            'schedule_new': 'Schedule Update',
            'schedule_conflict': 'Schedule Conflict',
            'schedule_reminder': 'Schedule Reminder',
            'schedule_deadline': 'Deadline Alert',
            'application': 'Application',
            'application_update': 'Application Update',
            'job_application_update': 'Application Update',
            'job_application_hire': 'Hired',
            'job_application_deny': 'Application Denied',
            'contract': 'Contract',
            'contract_update': 'Contract Update',
            'contract_finalize': 'Contract Finalized',
            'contract_finalized': 'Contract Finalized',
            'contract_completed': 'Job Completed - Review Required',
            'job_completed': 'Job Completed',
            'progress_log': 'Progress Update',
            'verification': 'Verification',
            'verification_approved': 'Verification Approved',
            'verification_rejected': 'Verification Rejected',
        }
        return type_map.get(self.notif_type, 'Notification')

    def __str__(self):
        return f"Notification for {self.user.username} at {self.created_at}"


class NotificationSettings(models.Model):
    """User notification preferences"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_settings")
    
    # Email notifications
    email_on_job_post = models.BooleanField(default=True, help_text="Email when new jobs are posted nearby")
    email_on_message = models.BooleanField(default=True, help_text="Email when you receive a message")
    email_on_application = models.BooleanField(default=True, help_text="Email when someone applies to your job")
    email_on_contract = models.BooleanField(default=True, help_text="Email on contract updates")
    email_on_announcement = models.BooleanField(default=True, help_text="Email on new announcements")
    
    # In-app notifications
    notify_job_post = models.BooleanField(default=True, help_text="Notify about new jobs nearby")
    notify_message = models.BooleanField(default=True, help_text="Notify about new messages")
    notify_application = models.BooleanField(default=True, help_text="Notify about job applications")
    notify_contract = models.BooleanField(default=True, help_text="Notify about contracts")
    notify_announcement = models.BooleanField(default=True, help_text="Notify about announcements")
    notify_application_updates = models.BooleanField(default=True, help_text="Notify about application status changes")
    
    # Notification frequency
    FREQUENCY_CHOICES = [
        ('instant', 'Instant'),
        ('hourly', 'Hourly Digest'),
        ('daily', 'Daily Digest'),
        ('weekly', 'Weekly Digest'),
    ]
    email_frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default='instant')
    
    # Do Not Disturb
    do_not_disturb = models.BooleanField(default=False, help_text="Pause all notifications")
    dnd_start_time = models.TimeField(null=True, blank=True, help_text="Do Not Disturb start time")
    dnd_end_time = models.TimeField(null=True, blank=True, help_text="Do Not Disturb end time")
    
    # Notification radius (in km)
    notification_radius = models.IntegerField(default=5, help_text="Radius in km for job notifications")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Notification Settings for {self.user.username}"
    
    def should_notify(self, notif_type):
        """Check if user should receive this type of notification"""
        if self.do_not_disturb:
            return False
        
        type_map = {
            'job_post': self.notify_job_post,
            'message': self.notify_message,
            'application': self.notify_application,
            'contract': self.notify_contract,
            'announcement': self.notify_announcement,
            'job_application_update': self.notify_application_updates,
            'job_application_hire': self.notify_application_updates,
            'job_application_deny': self.notify_application_updates,
            'contract_update': self.notify_contract,
            'contract_draft_update': self.notify_contract,
            'contract_cancel': self.notify_contract,
            'contract_accept': self.notify_contract,
            'contract_finalize': self.notify_contract,
            'progress_log': self.notify_contract,
        }
        return type_map.get(notif_type, True)


