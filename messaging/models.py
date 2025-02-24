from django.db import models
from django.contrib.auth import get_user_model
from better_profanity import profanity 

User = get_user_model()

class Conversation(models.Model):
    """Represents a chat between two users."""
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="conversations_initiated")
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="conversations_received")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Conversation between {self.user1.username} and {self.user2.username}"
    

class Message(models.Model):
    """Stores chat messages between users."""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages",null=True, blank=True)
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_flagged = models.BooleanField(default=False)  # If message contains banned words

    def save(self, *args, **kwargs):
        """Check for banned words before saving."""
        profanity.load_censor_words([word.word for word in BannedWord.objects.all()])  # Load custom banned words
        if profanity.contains_profanity(self.content):
            self.is_flagged = True  # Flag message if it contains banned words
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Message from {self.sender.username}"

class BannedWord(models.Model):
    """Moderator can add words to be filtered from messages."""
    word = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.word
