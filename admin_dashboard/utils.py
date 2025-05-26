from better_profanity import profanity
from admin_dashboard.models import ModeratedWord

def load_banned_words():
    """Load banned words from the database into the profanity filter."""
    banned_words = ModeratedWord.objects.values_list('word', flat=True)
    print("Banned words loaded:", list(banned_words)) 
    profanity.load_censor_words([word for word in banned_words if ' ' not in word])  # Load single words only
    return list(banned_words)  