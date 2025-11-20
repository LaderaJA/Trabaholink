from django import template

register = template.Library()


@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Template filter to access dictionary values by key.
    Usage: {{ dictionary|get_item:key }}
    """
    if dictionary is None:
        return None
    try:
        return dictionary.get(int(key), 0)
    except (ValueError, TypeError, AttributeError):
        return 0


@register.filter(name='mul')
def mul(value, arg):
    """
    Template filter to multiply two numbers.
    Usage: {{ value|mul:arg }}
    """
    try:
        return int(value) * int(arg)
    except (ValueError, TypeError):
        return 0


@register.filter(name='div')
def div(value, arg):
    """
    Template filter to divide two numbers.
    Usage: {{ value|div:arg }}
    """
    try:
        numerator = int(value)
        denominator = int(arg)
        if denominator == 0:
            return 0
        return numerator // denominator
    except (ValueError, TypeError):
        return 0


@register.filter(name='censor_flagged_words')
def censor_flagged_words(text, flagged_words_str):
    """
    Template filter to censor flagged words in text.
    Usage: {{ review.comment|censor_flagged_words:review.flagged_words }}
    """
    if not text or not flagged_words_str:
        return text
    
    import re
    
    # Parse the flagged words string
    # Assumes format like "word1, word2, word3" or just "word"
    if isinstance(flagged_words_str, str):
        flagged_words = [word.strip().lower() for word in flagged_words_str.split(',') if word.strip()]
    else:
        return text
    
    censored_text = text
    for word in flagged_words:
        # Create a case-insensitive pattern that matches whole words
        pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
        # Replace with asterisks of the same length
        replacement = '*' * len(word)
        censored_text = pattern.sub(replacement, censored_text)
    
    return censored_text
