from django.core.mail import send_mail
from django.conf import settings

def send_notification_email(subject, message, recipient_email):
    """Send an email notification using SendGrid."""
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,  
        [recipient_email],
        fail_silently=False,
    )
