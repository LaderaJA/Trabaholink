
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path("admin_dashboard/", include("admin_dashboard.urls", namespace="admin_dashboard")),
    path("", include("jobs.urls", namespace="jobs")),
    path('users/', include('users.urls')),
    path("messaging/", include("messaging.urls", namespace="messaging")),
    path("announcements/", include("announcements.urls", namespace="announcements")),
    path("notifications/", include("notifications.urls")),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)