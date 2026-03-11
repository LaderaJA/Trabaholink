"""
Custom template filters for user-related functionality.
"""
import os
from django import template

register = template.Library()


@register.filter(name='original_filename')
def original_filename(file_field):
    """
    Extract the original filename from a file field that uses UUID naming.
    
    For CV files stored as: user_cvs/{uuid}_{original_name}.ext
    This filter returns just the original_name.ext part.
    
    Usage: {{ user.cv_file|original_filename }}
    """
    if not file_field:
        return ''
    
    try:
        # Get the full filename from the path
        full_filename = os.path.basename(file_field.name)
        
        # Split by underscore to separate UUID from original name
        # Format: {uuid}_{original_name}.ext
        parts = full_filename.split('_', 1)
        
        if len(parts) > 1:
            # Return everything after the first underscore (original filename)
            return parts[1]
        else:
            # If no underscore found, return the full filename
            return full_filename
    except Exception:
        # If any error occurs, return the basename as fallback
        return os.path.basename(file_field.name)


@register.filter(name='file_extension')
def file_extension(file_field):
    """
    Get the file extension from a file field.
    
    Usage: {{ user.cv_file|file_extension }}
    Returns: 'pdf', 'doc', 'docx', etc.
    """
    if not file_field:
        return ''
    
    try:
        filename = os.path.basename(file_field.name)
        ext = os.path.splitext(filename)[1].lower()
        return ext.lstrip('.')  # Remove the leading dot
    except Exception:
        return ''


@register.filter(name='file_icon')
def file_icon(file_field):
    """
    Get the appropriate Bootstrap icon class for a file type.
    
    Usage: {{ user.cv_file|file_icon }}
    Returns: 'bi-file-earmark-pdf-fill', 'bi-file-earmark-word-fill', etc.
    """
    if not file_field:
        return 'bi-file-earmark'
    
    try:
        ext = file_extension(file_field)
        
        icon_map = {
            'pdf': 'bi-file-earmark-pdf-fill',
            'doc': 'bi-file-earmark-word-fill',
            'docx': 'bi-file-earmark-word-fill',
            'txt': 'bi-file-earmark-text-fill',
            'jpg': 'bi-file-earmark-image-fill',
            'jpeg': 'bi-file-earmark-image-fill',
            'png': 'bi-file-earmark-image-fill',
            'gif': 'bi-file-earmark-image-fill',
        }
        
        return icon_map.get(ext, 'bi-file-earmark')
    except Exception:
        return 'bi-file-earmark'


@register.filter(name='file_color')
def file_color(file_field):
    """
    Get the appropriate color for a file type icon.
    
    Usage: style="color: {{ user.cv_file|file_color }};"
    Returns: '#ef4444' for PDF, '#2563eb' for Word, etc.
    """
    if not file_field:
        return '#64748b'
    
    try:
        ext = file_extension(file_field)
        
        color_map = {
            'pdf': '#ef4444',      # Red for PDF
            'doc': '#2563eb',      # Blue for Word
            'docx': '#2563eb',     # Blue for Word
            'txt': '#64748b',      # Gray for text
            'jpg': '#059669',      # Green for images
            'jpeg': '#059669',
            'png': '#059669',
            'gif': '#059669',
        }
        
        return color_map.get(ext, '#64748b')
    except Exception:
        return '#64748b'


@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Get an item from a dictionary by key.
    
    Usage: {{ my_dict|get_item:my_key }}
    """
    if not dictionary:
        return None
    return dictionary.get(key)
