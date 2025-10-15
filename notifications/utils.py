from django.core.mail import send_mail
from django.conf import settings

def send_notification_email(subject, message, recipient_email):
    """Send an email notification using SendGrid."""
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,  
            [recipient_email],
            fail_silently=True,
        )
    except Exception as e:
        # Log the error but don't crash the application
        print(f"Failed to send email to {recipient_email}: {str(e)}")
        pass
