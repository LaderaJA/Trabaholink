from django import template
from admin_dashboard.models import ModeratedWord
import re

register = template.Library()

@register.filter(name='censor_text')
def censor_text(text):
    """
    Censor banned words in text for display.
    Usage: {{ content|censor_text }}
    """
    if not text:
        return text
    
    # Get all banned words
    banned_words = ModeratedWord.objects.filter(is_banned=True).values_list('word', flat=True)
    
    censored = text
    for word in banned_words:
        # Create case-insensitive pattern with word boundaries
        pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
        # Replace with asterisks
        replacement = '*' * len(word)
        censored = pattern.sub(replacement, censored)
    
    return censored

@register.filter(name='has_banned_words')
def has_banned_words(text):
    """
    Check if text contains banned words.
    Usage: {% if content|has_banned_words %}...{% endif %}
    """
    if not text:
        return False
    
    banned_words = ModeratedWord.objects.filter(is_banned=True).values_list('word', flat=True)
    
    for word in banned_words:
        pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
        if pattern.search(text):
            return True
    
    return False


@register.filter(name='multiply')
def multiply(value, arg):
    """
    Multiply the value by the argument.
    Usage: {{ value|multiply:100 }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0
