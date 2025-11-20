from django.shortcuts import get_object_or_404
from django.http import Http404
from .models import Notification
import logging

logger = logging.getLogger(__name__)


class NotificationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if there's a notification_id in the GET parameters
        notification_id = request.GET.get('notification_id')
        
        if notification_id and request.user.is_authenticated:
            try:
                notification = Notification.objects.get(
                    id=notification_id,
                    user=request.user
                )
                
                # Only mark as read if not already read
                if not notification.is_read:
                    notification.mark_as_read()
                    logger.debug(f"Marked notification {notification_id} as read via middleware")
                    
            except Notification.DoesNotExist:
                logger.warning(f"Notification {notification_id} does not exist (middleware)")
            except ValueError:
                logger.warning(f"Invalid notification_id format: {notification_id} (middleware)")
            except Exception as e:
                logger.error(f"Error in notification middleware for notification {notification_id}: {str(e)}")

        response = self.get_response(request)
        return response