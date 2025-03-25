from django.urls import path
from .views import NotificationListView, MarkNotificationAsReadView

app_name = "notifications"

urlpatterns = [
    path("", NotificationListView.as_view(), name="notification_list"),
    path("mark-as-read/<int:pk>/", MarkNotificationAsReadView.as_view(), name="mark_notification_as_read"),
]
