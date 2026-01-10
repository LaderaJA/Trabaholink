"""
HTML sanitization utilities for user-generated content.
Uses bleach library to clean HTML from rich text editors like Quill.js
"""
import bleach


def sanitize_html(html_content):
    """
    Sanitize HTML content to prevent XSS attacks while preserving safe formatting.
    
    Args:
        html_content (str): Raw HTML content from rich text editor
        
    Returns:
        str: Sanitized HTML content with only allowed tags and attributes
    """
    if not html_content:
        return ""
    
    # Define allowed HTML tags (Quill.js outputs)
    allowed_tags = [
        'p', 'br', 'strong', 'em', 'u', 's',  # Basic formatting
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',   # Headers
        'ol', 'ul', 'li',                      # Lists
        'a',                                   # Links
        'blockquote', 'pre',                   # Quotes and code
    ]
    
    # Define allowed attributes for specific tags
    allowed_attributes = {
        'a': ['href', 'title', 'rel'],
        '*': ['class'],  # Allow class attribute on all tags for Quill styling
    }
    
    # Define allowed protocols for links
    allowed_protocols = ['http', 'https', 'mailto']
    
    # Clean the HTML
    cleaned_html = bleach.clean(
        html_content,
        tags=allowed_tags,
        attributes=allowed_attributes,
        protocols=allowed_protocols,
        strip=True  # Strip disallowed tags instead of escaping
    )
    
    return cleaned_html


def strip_html(html_content):
    """
    Completely strip all HTML tags and return plain text.
    Useful for generating plain text versions or previews.
    
    Args:
        html_content (str): HTML content
        
    Returns:
        str: Plain text with all HTML tags removed
    """
    if not html_content:
        return ""
    
    # Remove all HTML tags
    plain_text = bleach.clean(html_content, tags=[], strip=True)
    
    # Clean up extra whitespace
    plain_text = ' '.join(plain_text.split())
    
    return plain_text
