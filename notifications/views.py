from django.views.generic import ListView, View, UpdateView
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from .models import Notification, NotificationSettings
from django.dispatch import receiver
from notifications.utils import send_notification_email
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
import logging

logger = logging.getLogger(__name__)  

CustomUser = get_user_model()

@receiver(post_save, sender=CustomUser)
def send_welcome_email(sender, instance, created, **kwargs):
    if created:  # Only send when a new user is created
        try:
            subject = "Welcome to Trabaholink!"
            message = f"Hello {instance.username},\n\nThank you for joining Trabaholink. Start exploring jobs today!"
            send_notification_email(subject, message, instance.email)
        except Exception as e:
            print(f"Failed to send welcome notification to {instance.email}: {str(e)}")
            pass

class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = "notifications/notification_list.html"
    context_object_name = "notifications"

    def get_queryset(self):
        # Auto-archive old notifications (30+ days)
        try:
            Notification.auto_archive_old_notifications(self.request.user, days=30)
        except Exception as e:
            logger.error(f"Error auto-archiving notifications for user {self.request.user.id}: {str(e)}")
        
        # Exclude archived by default
        return Notification.objects.filter(
            user=self.request.user,
            is_archived=False
        ).order_by("-created_at")
    
    def get(self, request, *args, **kwargs):
        # Handle notification_id query parameter for direct access
        notification_id = request.GET.get('notification_id')
        if notification_id:
            try:
                # Try to get the notification
                try:
                    notification = Notification.objects.get(id=notification_id)
                    
                    # Check if it belongs to the current user
                    if notification.user != request.user:
                        logger.warning(f"User {request.user.id} tried to access notification {notification_id} belonging to user {notification.user.id}")
                        messages.error(request, "You don't have permission to view this notification.")
                        return redirect('notifications:notification_list')
                    
                except Notification.DoesNotExist:
                    logger.warning(f"Notification {notification_id} does not exist")
                    messages.error(request, "This notification no longer exists.")
                    return redirect('notifications:notification_list')
                
                # Mark as read
                notification.mark_as_read()
                logger.info(f"Marked notification {notification_id} as read for user {request.user.id}")
                
                # Check if the related object still exists
                if notification.is_object_deleted:
                    logger.warning(f"Notification {notification_id} references deleted object")
                    messages.warning(request, f"The content related to this notification is no longer available.")
                    # Auto-archive broken notification
                    try:
                        notification.archive()
                        logger.info(f"Auto-archived notification {notification_id} with broken reference")
                    except Exception as archive_error:
                        logger.error(f"Error auto-archiving notification {notification_id}: {str(archive_error)}")
                    return redirect('notifications:notification_list')
                
                # Get target URL
                try:
                    target_url = notification.target_url
                    
                    if target_url is None:
                        # Broken link - object was deleted
                        logger.warning(f"Notification {notification_id} has broken link (target_url is None)")
                        messages.warning(request, "The content for this notification is no longer available.")
                        # Auto-archive broken notification
                        try:
                            notification.archive()
                            logger.info(f"Auto-archived notification {notification_id} with broken link")
                        except Exception as archive_error:
                            logger.error(f"Error auto-archiving notification {notification_id}: {str(archive_error)}")
                        return redirect('notifications:notification_list')
                    elif target_url:
                        # Valid URL - redirect to target
                        return redirect(target_url)
                    else:
                        # Empty string or falsy value - stay on notification list
                        messages.info(request, f"Notification: {notification.message}")
                        
                except Exception as url_error:
                    # Error getting target URL (e.g., deleted objects, broken references)
                    logger.error(f"Error getting target URL for notification {notification_id}: {str(url_error)}")
                    messages.warning(request, "The link for this notification is no longer available.")
                    # Auto-archive problematic notification
                    try:
                        notification.archive()
                        logger.info(f"Auto-archived notification {notification_id} with URL error")
                    except Exception as archive_error:
                        logger.error(f"Error auto-archiving notification {notification_id}: {str(archive_error)}")
                    return redirect('notifications:notification_list')
                    
            except ValueError:
                logger.warning(f"Invalid notification_id format: {notification_id}")
                messages.error(request, "Invalid notification ID format.")
                return redirect('notifications:notification_list')
            except Exception as e:
                logger.error(f"Unexpected error accessing notification {notification_id}: {str(e)}")
                messages.error(request, "An error occurred while accessing the notification.")
                return redirect('notifications:notification_list')
        
        return super().get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['unread_count'] = Notification.objects.filter(
                user=self.request.user, is_read=False, is_archived=False
            ).count()
            context['read_count'] = Notification.objects.filter(
                user=self.request.user, is_read=True, is_archived=False
            ).count()
            context['archived_count'] = Notification.objects.filter(
                user=self.request.user, is_archived=True
            ).count()
        except Exception as e:
            logger.error(f"Error getting notification counts for user {self.request.user.id}: {str(e)}")
            context['unread_count'] = 0
            context['read_count'] = 0
            context['archived_count'] = 0
        return context


class MarkNotificationAsReadView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            notification = get_object_or_404(Notification, id=kwargs["pk"], user=request.user)
            notification.mark_as_read()
            return JsonResponse({"status": "success", "message": "Notification marked as read"})
        except Http404:
            logger.warning(f"Notification {kwargs.get('pk')} not found for user {request.user.id}")
            return JsonResponse({"status": "error", "message": "Notification not found"}, status=404)
        except Exception as e:
            logger.error(f"Error marking notification {kwargs.get('pk')} as read: {str(e)}")
            return JsonResponse({"status": "error", "message": "An error occurred"}, status=500)


class MarkAllNotificationsAsReadView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            count = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
            return JsonResponse({"status": "success", "message": f"{count} notifications marked as read", "count": count})
        except Exception as e:
            logger.error(f"Error marking all notifications as read for user {request.user.id}: {str(e)}")
            return JsonResponse({"status": "error", "message": "An error occurred"}, status=500)


class RecentNotificationsAPIView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            # Exclude archived from recent notifications
            notifications = Notification.objects.filter(
                user=request.user,
                is_archived=False
            ).order_by("-created_at")[:10]
            
            notification_list = []
            for notif in notifications:
                try:
                    target_url = notif.target_url
                    # Use notification list URL if target is broken
                    if target_url is None:
                        target_url = reverse('notifications:notification_list') + f"?notification_id={notif.id}"
                    
                    notification_list.append({
                        "id": notif.id,
                        "message": notif.message,
                        "notif_type": notif.notif_type,
                        "is_read": notif.is_read,
                        "created_at": notif.created_at.isoformat(),
                        "target_url": target_url,
                        "is_broken": notif.is_object_deleted,
                    })
                except Exception as notif_error:
                    logger.error(f"Error processing notification {notif.id}: {str(notif_error)}")
                    # Include notification with fallback URL
                    notification_list.append({
                        "id": notif.id,
                        "message": notif.message,
                        "notif_type": notif.notif_type,
                        "is_read": notif.is_read,
                        "created_at": notif.created_at.isoformat(),
                        "target_url": reverse('notifications:notification_list'),
                        "is_broken": True,
                    })
            
            data = {"notifications": notification_list}
            return JsonResponse(data)
        except Exception as e:
            logger.error(f"Error fetching recent notifications for user {request.user.id}: {str(e)}")
            return JsonResponse({"error": "An error occurred while fetching notifications"}, status=500)


class DeleteNotificationView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            notification = get_object_or_404(Notification, id=kwargs["pk"], user=request.user)
            notification.delete()
            return JsonResponse({"status": "success", "message": "Notification deleted"})
        except Http404:
            logger.warning(f"Notification {kwargs.get('pk')} not found for deletion by user {request.user.id}")
            return JsonResponse({"status": "error", "message": "Notification not found"}, status=404)
        except Exception as e:
            logger.error(f"Error deleting notification {kwargs.get('pk')}: {str(e)}")
            return JsonResponse({"status": "error", "message": "An error occurred"}, status=500)


class ArchiveNotificationView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            notification = get_object_or_404(Notification, id=kwargs["pk"], user=request.user)
            notification.archive()
            return JsonResponse({"status": "success", "message": "Notification archived"})
        except Http404:
            logger.warning(f"Notification {kwargs.get('pk')} not found for archiving by user {request.user.id}")
            return JsonResponse({"status": "error", "message": "Notification not found"}, status=404)
        except Exception as e:
            logger.error(f"Error archiving notification {kwargs.get('pk')}: {str(e)}")
            return JsonResponse({"status": "error", "message": "An error occurred"}, status=500)


class ArchiveAllReadView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            count = Notification.objects.filter(
                user=request.user,
                is_read=True,
                is_archived=False
            ).update(is_archived=True)
            return JsonResponse({"status": "success", "message": f"{count} notifications archived", "count": count})
        except Exception as e:
            logger.error(f"Error archiving all read notifications for user {request.user.id}: {str(e)}")
            return JsonResponse({"status": "error", "message": "An error occurred"}, status=500)


class NotificationSettingsView(LoginRequiredMixin, UpdateView):
    model = NotificationSettings
    template_name = "notifications/notification_settings.html"
    fields = [
        'email_on_job_post', 'email_on_message', 'email_on_application', 
        'email_on_contract', 'email_on_announcement',
        'notify_job_post', 'notify_message', 'notify_application',
        'notify_contract', 'notify_announcement', 'notify_application_updates',
        'email_frequency', 'do_not_disturb', 'dnd_start_time', 'dnd_end_time',
        'notification_radius'
    ]
    success_url = reverse_lazy('notifications:notification_settings')
    
    def get_object(self, queryset=None):
        try:
            # Get or create notification settings for the user
            obj, created = NotificationSettings.objects.get_or_create(user=self.request.user)
            if created:
                logger.info(f"Created notification settings for user {self.request.user.id}")
            return obj
        except Exception as e:
            logger.error(f"Error getting notification settings for user {self.request.user.id}: {str(e)}")
            messages.error(self.request, 'An error occurred while loading notification settings.')
            raise
    
    def form_valid(self, form):
        try:
            messages.success(self.request, 'Notification settings updated successfully!')
            return super().form_valid(form)
        except Exception as e:
            logger.error(f"Error updating notification settings for user {self.request.user.id}: {str(e)}")
            messages.error(self.request, 'An error occurred while updating notification settings.')
            return self.form_invalid(form)


@receiver(post_save, sender=CustomUser)
def create_notification_settings(sender, instance, created, **kwargs):
    """Create notification settings when a new user is created"""
    if created:
        NotificationSettings.objects.get_or_create(user=instance)
