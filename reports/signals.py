"""
Signals for the reporting system.
Handles automatic deactivation of users and posts based on report thresholds.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from django.utils import timezone
from .models import Report
from notifications.models import Notification


# Thresholds for automatic deactivation
USER_REPORT_THRESHOLD = 5
POST_REPORT_THRESHOLD = 5


@receiver(post_save, sender=Report)
def handle_report_creation(sender, instance, created, **kwargs):
    """
    Signal handler that runs when a new report is created.
    Increments report counts and checks for automatic deactivation thresholds.
    """
    if not created:
        return
    
    # Use atomic transaction to prevent race conditions
    with transaction.atomic():
        if instance.reported_user:
            # Handle user report
            user = instance.reported_user
            # Lock the user row for update to prevent race conditions
            user = type(user).objects.select_for_update().get(pk=user.pk)
            
            # Count unique reports (unique reporters)
            unique_report_count = Report.objects.filter(
                reported_user=user,
                reporter__isnull=False
            ).values('reporter').distinct().count()
            
            # Update report count
            user.report_count = unique_report_count
            user.save(update_fields=['report_count'])
            
            # Check if threshold reached for automatic deactivation
            if unique_report_count >= USER_REPORT_THRESHOLD and user.is_active:
                user.is_active = False
                user.save(update_fields=['is_active'])
                
                # Create notification for the user
                Notification.objects.create(
                    user=user,
                    message=f"Your account has been automatically deactivated due to receiving {unique_report_count} reports. Please contact support for assistance.",
                    notif_type="account_deactivated"
                )
                
                # Create notification for admins
                from users.models import CustomUser
                admins = CustomUser.objects.filter(role='admin', is_active=True)
                for admin in admins:
                    Notification.objects.create(
                        user=admin,
                        message=f"User '{user.username}' has been automatically deactivated after reaching {unique_report_count} reports.",
                        notif_type="admin_alert"
                    )
        
        elif instance.reported_post:
            # Handle post report
            post = instance.reported_post
            # Lock the post row for update to prevent race conditions
            from jobs.models import Job
            post = Job.objects.select_for_update().get(pk=post.pk)
            
            # Count unique reports (unique reporters)
            unique_report_count = Report.objects.filter(
                reported_post=post,
                reporter__isnull=False
            ).values('reporter').distinct().count()
            
            # Update report count
            post.report_count = unique_report_count
            post.save(update_fields=['report_count'])
            
            # Check if threshold reached for automatic deactivation
            if unique_report_count >= POST_REPORT_THRESHOLD and post.is_active:
                post.is_active = False
                post.save(update_fields=['is_active'])
                
                # Create notification for the post owner
                Notification.objects.create(
                    user=post.owner,
                    message=f"Your job posting '{post.title}' has been automatically deactivated due to receiving {unique_report_count} reports. Please contact support for assistance.",
                    notif_type="post_deactivated"
                )
                
                # Create notification for admins
                from users.models import CustomUser
                admins = CustomUser.objects.filter(role='admin', is_active=True)
                for admin in admins:
                    Notification.objects.create(
                        user=admin,
                        message=f"Job posting '{post.title}' (ID: {post.id}) has been automatically deactivated after reaching {unique_report_count} reports.",
                        notif_type="admin_alert"
                    )
