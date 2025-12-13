from django.db import models
from django.conf import settings  
from django.db.models.signals import post_save
from django.dispatch import receiver
from notifications.utils import send_notification_email
from admin_dashboard.utils import load_banned_words
from better_profanity import profanity
from django.contrib.auth import get_user_model

User = get_user_model()

class Announcement(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    image = models.ImageField(upload_to="announcements/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    posted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField(blank=True, null=True, default="")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        banned_words = load_banned_words()

        profanity.load_censor_words([word for word in banned_words if ' ' not in word])
        self.content = profanity.censor(self.content)

        for phrase in banned_words:
            if ' ' in phrase:  
                self.content = self.content.replace(phrase, '*' * len(phrase))

        super().save(*args, **kwargs)

@receiver(post_save, sender=Announcement)
def notify_users_about_announcement(sender, instance, created, **kwargs):
    if created:
        try:
            all_users = User.objects.all()
            for user in all_users:
                try:
                    subject = "New Announcement from Trabaholink!"
                    message = f"{instance.title}\n\n{instance.description}"
                    send_notification_email(subject, message, user.email)
                except Exception as e:
                    # Log the error but don't stop the process
                    print(f"Failed to send email to {user.email}: {str(e)}")
                    continue
        except Exception as e:
            # If email sending fails completely, just log and continue
            print(f"Email notification failed: {str(e)}")
            pass
