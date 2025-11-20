import os
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible

# Try to import python-magic, but make it optional
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False


@deconstructible
class CVFileValidator:
    """
    Validator for CV/Resume file uploads.
    Validates file extension, MIME type, and file size.
    """
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = ['.pdf', '.doc', '.docx']
    
    # Allowed MIME types
    ALLOWED_MIME_TYPES = [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    ]
    
    # Maximum file size (5MB)
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB in bytes
    
    def __init__(self, max_size=None, allowed_extensions=None):
        """
        Initialize validator with optional custom settings.
        
        Args:
            max_size: Maximum file size in bytes (default: 5MB)
            allowed_extensions: List of allowed file extensions (default: PDF, DOC, DOCX)
        """
        self.max_size = max_size or self.MAX_FILE_SIZE
        self.allowed_extensions = allowed_extensions or self.ALLOWED_EXTENSIONS
    
    def __call__(self, file):
        """
        Validate the uploaded file.
        
        Args:
            file: UploadedFile object
            
        Raises:
            ValidationError: If file doesn't meet validation criteria
        """
        # Check file size
        if file.size > self.max_size:
            size_mb = self.max_size / (1024 * 1024)
            raise ValidationError(
                f'File size must not exceed {size_mb}MB. Your file is {file.size / (1024 * 1024):.2f}MB.'
            )
        
        # Check file extension
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in self.allowed_extensions:
            raise ValidationError(
                f'File type not supported. Allowed types: {", ".join(self.allowed_extensions)}'
            )
        
        # Check MIME type (server-side validation for security)
        if MAGIC_AVAILABLE:
            try:
                # Read first 2048 bytes for MIME type detection
                file.seek(0)
                file_head = file.read(2048)
                file.seek(0)
                
                # Detect MIME type using python-magic
                mime = magic.from_buffer(file_head, mime=True)
                
                if mime not in self.ALLOWED_MIME_TYPES:
                    raise ValidationError(
                        f'Invalid file type detected. Please upload a valid PDF or Word document.'
                    )
            except Exception as e:
                # If magic library fails, skip MIME validation
                # but log the error for debugging
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f'MIME type validation failed: {str(e)}')
        else:
            # python-magic not installed, skip MIME validation
            # Extension validation is still performed above
            pass
    
    def __eq__(self, other):
        return (
            isinstance(other, CVFileValidator) and
            self.max_size == other.max_size and
            self.allowed_extensions == other.allowed_extensions
        )


def validate_cv_file(file):
    """
    Standalone function to validate CV files.
    Can be used directly in model field validators.
    """
    validator = CVFileValidator()
    validator(file)
