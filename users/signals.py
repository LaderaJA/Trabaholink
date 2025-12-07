from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .activity_logger import log_activity

CustomUser = get_user_model()

# NOTE: Welcome emails have been removed. 
# Only OTP verification emails are sent during registration.
# This ensures emails are only used for authentication purposes.


@receiver(post_save, sender=CustomUser)
def create_user_guide_status(sender, instance, created, **kwargs):
    """
    Automatically create a UserGuideStatus record when a new user is created.
    
    This ensures every user has guide preferences from the moment they register.
    Auto-popup is enabled by default for new users.
    """
    if created:
        from .models import UserGuideStatus
        UserGuideStatus.objects.get_or_create(
            user=instance,
            defaults={
                'auto_popup_enabled': True,
                'pages_completed': {},
                'total_guides_viewed': 0,
            }
        )


@receiver(post_save, sender=CustomUser)
def save_user_guide_status(sender, instance, **kwargs):
    """
    Ensure guide status exists when user is saved.
    Handles edge cases where signal might have been missed.
    """
    if not hasattr(instance, 'guide_status'):
        from .models import UserGuideStatus
        UserGuideStatus.objects.get_or_create(
            user=instance,
            defaults={
                'auto_popup_enabled': True,
                'pages_completed': {},
                'total_guides_viewed': 0,
            }
        )


@receiver(post_save, sender=CustomUser)
def log_profile_update(sender, instance, created, **kwargs):
    """Log when a user updates their profile"""
    if not created and hasattr(instance, '_profile_updated'):
        log_activity(
            user=instance,
            activity_type='profile_updated',
            description=f"Updated profile information",
            related_object=instance
        )


@receiver(post_save, sender='users.Skill')
def log_skill_added(sender, instance, created, **kwargs):
    """Log when a skill is added"""
    if created:
        log_activity(
            user=instance.user,
            activity_type='skill_added',
            description=f"Added new skill: {instance.name}",
            related_object=instance
        )


@receiver(post_save, sender='users.Skill')
def log_skill_verified(sender, instance, created, **kwargs):
    """Log when a skill is verified"""
    if not created and instance.status == 'verified':
        log_activity(
            user=instance.user,
            activity_type='skill_verified',
            description=f"Skill verified: {instance.name}",
            related_object=instance
        )
