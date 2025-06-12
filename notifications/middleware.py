from django.shortcuts import get_object_or_404
from .models import Notification

class NotificationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if there's a notification_id in the GET parameters
        notification_id = request.GET.get('notification_id')
        
        if notification_id and request.user.is_authenticated:
            try:
                notification = get_object_or_404(
                    Notification, 
                    id=notification_id,
                    user=request.user,
                    is_read=False
                )
                notification.mark_as_read()
            except:
                pass  # Silently fail if notification doesn't exist or is already read

        response = self.get_response(request)
        return response