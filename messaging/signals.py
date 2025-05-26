from django.db.models.signals import post_save
from django.dispatch import receiver
from messaging.models import Message
from notifications.models import Notification

@receiver(post_save, sender=Message)
def notify_user_on_new_message(sender, instance, created, **kwargs):
    if created:
        # Get the receiver as the other user in the conversation
        conversation = instance.conversation
        receiver = conversation.user1 if instance.sender != conversation.user1 else conversation.user2
        Notification.objects.create(
            user=receiver,
            notif_type="message",
            object_id=conversation.id,
            message=f"New message from {instance.sender.username}",
        )