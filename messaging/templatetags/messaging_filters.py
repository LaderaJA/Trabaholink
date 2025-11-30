from django import template
import os

register = template.Library()

@register.filter
def is_image(filename):
    """Check if a file is an image based on extension"""
    if not filename:
        return False
    
    # Get the extension (handles paths like 'chat_files/image.jpg')
    ext = os.path.splitext(filename)[1].lower()
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
    return ext in image_extensions

@register.filter
def get_extension(filename):
    """Get file extension for debugging"""
    if not filename:
        return ''
    return os.path.splitext(filename)[1].lower()
