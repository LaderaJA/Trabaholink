from django.urls import path
from .views import (
    ServicePostListView,
    ServicePostDetailView,
    ServicePostCreateView,
    ServicePostUpdateView,
    deactivate_service_post,
)

app_name = "services"

urlpatterns = [
    path("create/", ServicePostCreateView.as_view(), name="servicepost_create"),
    path("edit/<slug:slug>/", ServicePostUpdateView.as_view(), name="servicepost_update"),
    path("deactivate/<slug:slug>/", deactivate_service_post, name="deactivate_service_post"),
    path("<slug:slug>/", ServicePostDetailView.as_view(), name="servicepost_detail"),
    path("", ServicePostListView.as_view(), name="servicepost_list"),
]

