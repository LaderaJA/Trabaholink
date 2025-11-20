from django.utils import timezone
from django.core.cache import cache
from jobs.models import Job


class ExpiredJobsMiddleware:
    """
    Middleware to automatically deactivate expired jobs.
    Runs once every 5 minutes to avoid excessive database queries.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check if we should run the expiration check
        cache_key = 'last_job_expiration_check'
        last_check = cache.get(cache_key)
        
        if last_check is None:
            # Run the check
            try:
                Job.deactivate_expired_jobs()
            except Exception as e:
                # Log error but don't break the request
                print(f"Error deactivating expired jobs: {e}")
            
            # Cache for 5 minutes (300 seconds)
            cache.set(cache_key, timezone.now(), 300)
        
        response = self.get_response(request)
        return response
