from django.views.generic import ListView, View
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Notification
from django.dispatch import receiver
from notifications.utils import send_notification_email
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save  

CustomUser = get_user_model()

@receiver(post_save, sender=CustomUser)
def send_welcome_email(sender, instance, created, **kwargs):
    if created:  # Only send when a new user is created
        subject = "Welcome to Trabaholink!"
        message = f"Hello {instance.username},\n\nThank you for joining Trabaholink. Start exploring jobs today!"
        send_notification_email(subject, message, instance.email)

class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = "notifications/notification_list.html"
    context_object_name = "notifications"

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by("-created_at")


class MarkNotificationAsReadView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        notification = get_object_or_404(Notification, id=kwargs["pk"], user=request.user)
        notification.mark_as_read()
        return JsonResponse({"status": "success"})
