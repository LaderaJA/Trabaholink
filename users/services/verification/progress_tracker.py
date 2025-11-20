"""
Progress tracking for verification pipeline.
Allows real-time monitoring of verification progress in admin dashboard.
"""
from django.core.cache import cache
from typing import Dict, Optional
import time


class VerificationProgressTracker:
    """Track verification progress using Redis cache."""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.cache_key = f"verification_progress_{user_id}"
        self.start_time = time.time()
    
    def update(self, step: str, progress: int, message: str = ""):
        """
        Update verification progress.
        
        Args:
            step: Current step name (e.g., "ocr", "face_match", "validation")
            progress: Progress percentage (0-100)
            message: Optional status message
        """
        elapsed = int(time.time() - self.start_time)
        
        data = {
            'step': step,
            'progress': progress,
            'message': message,
            'elapsed_seconds': elapsed,
            'timestamp': time.time()
        }
        
        # Store in cache for 5 minutes
        cache.set(self.cache_key, data, timeout=300)
    
    def complete(self, status: str, message: str = ""):
        """Mark verification as complete."""
        elapsed = int(time.time() - self.start_time)
        
        data = {
            'step': 'complete',
            'progress': 100,
            'status': status,
            'message': message,
            'elapsed_seconds': elapsed,
            'timestamp': time.time()
        }
        
        # Store for 10 minutes so admin can see final status
        cache.set(self.cache_key, data, timeout=600)
    
    def error(self, error_message: str):
        """Mark verification as failed."""
        elapsed = int(time.time() - self.start_time)
        
        data = {
            'step': 'error',
            'progress': 0,
            'status': 'failed',
            'message': error_message,
            'elapsed_seconds': elapsed,
            'timestamp': time.time()
        }
        
        cache.set(self.cache_key, data, timeout=600)
    
    @staticmethod
    def get_progress(user_id: int) -> Optional[Dict]:
        """Get current progress for a user."""
        cache_key = f"verification_progress_{user_id}"
        return cache.get(cache_key)
    
    @staticmethod
    def clear_progress(user_id: int):
        """Clear progress data for a user."""
        cache_key = f"verification_progress_{user_id}"
        cache.delete(cache_key)
