from django.urls import path
from .views import (
    NotificationListView, 
    MarkNotificationAsReadView,
    MarkAllNotificationsAsReadView,
    RecentNotificationsAPIView,
    NotificationSettingsView,
    DeleteNotificationView,
    ArchiveNotificationView,
    ArchiveAllReadView
)

app_name = "notifications"

urlpatterns = [
    path("", NotificationListView.as_view(), name="notification_list"),
    path("mark-as-read/<int:pk>/", MarkNotificationAsReadView.as_view(), name="mark_notification_as_read"),
    path("mark-all-read/", MarkAllNotificationsAsReadView.as_view(), name="mark_all_read"),
    path("delete/<int:pk>/", DeleteNotificationView.as_view(), name="delete_notification"),
    path("archive/<int:pk>/", ArchiveNotificationView.as_view(), name="archive_notification"),
    path("archive-all-read/", ArchiveAllReadView.as_view(), name="archive_all_read"),
    path("api/recent/", RecentNotificationsAPIView.as_view(), name="recent_notifications_api"),
    path("settings/", NotificationSettingsView.as_view(), name="notification_settings"),
]
