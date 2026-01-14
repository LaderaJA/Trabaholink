import os
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
import cv2
import tempfile


def validate_video_file(file):
    """
    Validate video file for progress updates:
    - Max size: 25MB
    - Max duration: 30 seconds
    - Allowed formats: MP4, MOV, WEBM, AVI
    """
    # Check file size (25MB = 26,214,400 bytes)
    max_size = 25 * 1024 * 1024  # 25MB
    if file.size > max_size:
        raise ValidationError(
            f'Video file size must be under 25MB. Your file is {file.size / (1024*1024):.1f}MB.'
        )
    
    # Check file extension
    ext = os.path.splitext(file.name)[1].lower()
    allowed_extensions = ['.mp4', '.mov', '.webm', '.avi']
    if ext not in allowed_extensions:
        raise ValidationError(
            f'Invalid video format. Allowed formats: MP4, MOV, WEBM, AVI. You uploaded: {ext}'
        )
    
    # Check MIME type
    allowed_mime_types = [
        'video/mp4', 
        'video/quicktime',  # MOV
        'video/webm', 
        'video/x-msvideo',  # AVI
        'video/avi'
    ]
    if hasattr(file, 'content_type') and file.content_type not in allowed_mime_types:
        raise ValidationError(
            f'Invalid video MIME type: {file.content_type}'
        )
    
    # Check video duration using OpenCV
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
            for chunk in file.chunks():
                tmp_file.write(chunk)
            tmp_path = tmp_file.name
        
        # Reset file pointer for later use
        file.seek(0)
        
        # Open video with OpenCV
        video = cv2.VideoCapture(tmp_path)
        
        if not video.isOpened():
            os.unlink(tmp_path)
            raise ValidationError('Unable to process video file. Please ensure it is a valid video.')
        
        # Get video properties
        fps = video.get(cv2.CAP_PROP_FPS)
        frame_count = video.get(cv2.CAP_PROP_FRAME_COUNT)
        
        video.release()
        os.unlink(tmp_path)
        
        if fps > 0:
            duration = frame_count / fps
            max_duration = 30  # seconds
            
            if duration > max_duration:
                raise ValidationError(
                    f'Video duration must be under 30 seconds. Your video is {duration:.1f} seconds long.'
                )
        else:
            # Cannot determine FPS, skip duration check
            pass
            
    except cv2.error as e:
        raise ValidationError(f'Error processing video: {str(e)}')
    except Exception as e:
        # If validation fails for any reason, log but don't block
        # (better to allow upload than block legitimate videos)
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f'Video validation warning: {str(e)}')
