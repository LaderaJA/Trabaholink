from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model

CustomUser = get_user_model()


@receiver(post_save, sender=CustomUser)
def send_welcome_email(sender, instance, created, **kwargs):
    if created:
        send_mail(
            "Welcome to Trabaholink!",
            "Thank you for signing up. Stay tuned for job opportunities and announcements.",
            settings.DEFAULT_FROM_EMAIL,
            [instance.email],
            fail_silently=False,
        )
