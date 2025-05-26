from django.db import models
from django.contrib.auth import get_user_model
from better_profanity import profanity
from admin_dashboard.utils import load_banned_words


User = get_user_model()

class Conversation(models.Model):
    """Represents a chat between two users."""
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="conversations_initiated")
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="conversations_received")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  

    class Meta:
        unique_together = ("user1", "user2")  
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["updated_at"]),
        ]

    @property
    def last_message(self):
        return self.messages.order_by("-created_at").first()

    @property
    def last_message_time(self):
        last_msg = self.last_message
        return last_msg.created_at if last_msg else None
    
    def __str__(self):
        return f"Conversation between {self.user1.username} and {self.user2.username}"

    

class Message(models.Model):
    """Stores chat messages between users."""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages", null=True, blank=True)
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField(blank=True, null=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    is_flagged = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        banned_words = load_banned_words()
        self.content = profanity.censor(self.content)
        for phrase in banned_words:
            if ' ' in phrase:  
                self.content = self.content.replace(phrase, '*' * len(phrase))

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Message from {self.sender.username}"

class BannedWord(models.Model):
    """Moderator can add words to be filtered from messages."""
    word = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.word
