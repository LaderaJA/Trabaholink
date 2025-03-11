
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path("", include("jobs.urls")),
    path('users/', include('users.urls')),
    path("messaging/", include("messaging.urls")),
    path("announcements/", include("announcements.urls")),
    path("admin_dashboard/", include("admin_dashboard.urls")),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)