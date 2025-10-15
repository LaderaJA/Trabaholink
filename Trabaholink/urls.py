from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.contrib.staticfiles.views import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path("admin_dashboard/", include("admin_dashboard.urls", namespace="admin_dashboard")),
    path("", include("jobs.urls", namespace="jobs")),
    path('users/', include('users.urls')),
    path("messaging/", include("messaging.urls", namespace="messaging")),
    path("announcements/", include("announcements.urls", namespace="announcements")),
    path("notifications/", include("notifications.urls")),
    path("services/", include("services.urls", namespace="services")),
    path('posts/', include('posts.urls', namespace='posts')),
    # API URLs
    path('api/jobs/', include('jobs.api_urls', namespace='jobs_api')),
    # Allauth URLs
    path('accounts/', include('allauth.urls')),
    # Favicon
    path('favicon.ico', RedirectView.as_view(url='/static/images/favicon.ico', permanent=True)),
]

# Serve static files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [
        path('static/<path:path>', serve, {'document_root': settings.STATIC_ROOT or settings.STATICFILES_DIRS[0]}),
    ]