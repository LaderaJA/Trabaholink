from django.views.generic import ListView, View, UpdateView
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from .models import Notification, NotificationSettings
from django.dispatch import receiver
from notifications.utils import send_notification_email
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save  

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
        Notification.auto_archive_old_notifications(self.request.user, days=30)
        
        # Exclude archived by default
        return Notification.objects.filter(
            user=self.request.user,
            is_archived=False
        ).order_by("-created_at")
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unread_count'] = Notification.objects.filter(
            user=self.request.user, is_read=False, is_archived=False
        ).count()
        context['read_count'] = Notification.objects.filter(
            user=self.request.user, is_read=True, is_archived=False
        ).count()
        context['archived_count'] = Notification.objects.filter(
            user=self.request.user, is_archived=True
        ).count()
        return context


class MarkNotificationAsReadView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        notification = get_object_or_404(Notification, id=kwargs["pk"], user=request.user)
        notification.mark_as_read()
        return JsonResponse({"status": "success"})


class MarkAllNotificationsAsReadView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return JsonResponse({"status": "success"})


class RecentNotificationsAPIView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        # Exclude archived from recent notifications
        notifications = Notification.objects.filter(
            user=request.user,
            is_archived=False
        ).order_by("-created_at")[:10]
        data = {
            "notifications": [
                {
                    "id": notif.id,
                    "message": notif.message,
                    "notif_type": notif.notif_type,
                    "is_read": notif.is_read,
                    "created_at": notif.created_at.isoformat(),
                    "target_url": notif.target_url,
                }
                for notif in notifications
            ]
        }
        return JsonResponse(data)


class DeleteNotificationView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        notification = get_object_or_404(Notification, id=kwargs["pk"], user=request.user)
        notification.delete()
        return JsonResponse({"status": "success"})


class ArchiveNotificationView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        notification = get_object_or_404(Notification, id=kwargs["pk"], user=request.user)
        notification.archive()
        return JsonResponse({"status": "success"})


class ArchiveAllReadView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        count = Notification.objects.filter(
            user=request.user,
            is_read=True,
            is_archived=False
        ).update(is_archived=True)
        return JsonResponse({"status": "success", "count": count})


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
        # Get or create notification settings for the user
        obj, created = NotificationSettings.objects.get_or_create(user=self.request.user)
        return obj
    
    def form_valid(self, form):
        messages.success(self.request, 'Notification settings updated successfully!')
        return super().form_valid(form)


@receiver(post_save, sender=CustomUser)
def create_notification_settings(sender, instance, created, **kwargs):
    """Create notification settings when a new user is created"""
    if created:
        NotificationSettings.objects.get_or_create(user=instance)
