from admin_dashboard.models import ModeratedWord
import re

def check_for_banned_words(text):
    """
    Check if text contains any banned words.
    Returns: (is_flagged, flagged_words)
    """
    if not text:
        return False, []
    
    text_lower = text.lower()
    banned_words = ModeratedWord.objects.filter(is_banned=True)
    flagged_words = []
    
    for word_obj in banned_words:
        word = word_obj.word.lower()
        # Use word boundaries to match whole words
        pattern = r'\b' + re.escape(word) + r'\b'
        if re.search(pattern, text_lower, re.IGNORECASE):
            flagged_words.append(word_obj.word)
            # Increment flagged count
            word_obj.flagged_count = (word_obj.flagged_count or 0) + 1
            word_obj.save()
    
    return len(flagged_words) > 0, flagged_words

def sanitize_text(text):
    """
    Replace banned words with asterisks.
    """
    if not text:
        return text
    
    banned_words = ModeratedWord.objects.filter(is_banned=True)
    sanitized = text
    
    for word_obj in banned_words:
        word = word_obj.word
        # Replace with asterisks of same length
        replacement = '*' * len(word)
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        sanitized = pattern.sub(replacement, sanitized)
    
    return sanitized
