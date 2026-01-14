from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.contrib.staticfiles.views import serve
from django.http import HttpResponse
from django.views.decorators.http import require_GET
from django.views.decorators.cache import cache_control
import os
from .health_views import health_check, health_check_detailed

@require_GET
@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
def service_worker(request):
    """Serve the service worker from root path with correct scope"""
    sw_path = os.path.join(settings.BASE_DIR, 'static', 'js', 'sw.js')
    try:
        with open(sw_path, 'r', encoding='utf-8') as f:
            sw_content = f.read()
        return HttpResponse(sw_content, content_type='application/javascript')
    except FileNotFoundError:
        return HttpResponse('Service Worker not found', status=404)

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
    path('reports/', include('reports.urls', namespace='reports')),
    # API URLs
    path('api/jobs/', include('jobs.api_urls', namespace='jobs_api')),
    # Allauth URLs
    path('accounts/', include('allauth.urls')),
    # Internationalization
    path('i18n/', include('django.conf.urls.i18n')),
    # Health check endpoints for Docker
    path('health/', health_check, name='health_check'),
    path('health/detailed/', health_check_detailed, name='health_check_detailed'),
    # Service Worker - must be at root for proper scope
    path('sw.js', service_worker, name='service_worker'),
    # Favicon
    path('favicon.ico', RedirectView.as_view(url='/static/images/favicon.ico', permanent=True)),
]

# Serve static files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [
        path('static/<path:path>', serve, {'document_root': settings.STATIC_ROOT or settings.STATICFILES_DIRS[0]}),
    ]