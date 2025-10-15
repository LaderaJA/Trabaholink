from django.urls import path
from .views import (
    ServicePostListView,
    ServicePostDetailView,
    ServicePostCreateView,
    ServicePostUpdateView,
    ServicePostDeleteView,
    MyServicesListView,
    deactivate_service_post,
)

app_name = "services"

urlpatterns = [
    path("", ServicePostListView.as_view(), name="servicepost_list"),
    path("create/", ServicePostCreateView.as_view(), name="servicepost_create"),
    path("my-services/", MyServicesListView.as_view(), name="my_services"),
    path("<slug:slug>/", ServicePostDetailView.as_view(), name="servicepost_detail"),
    path("<slug:slug>/edit/", ServicePostUpdateView.as_view(), name="servicepost_update"),
    path("<slug:slug>/delete/", ServicePostDeleteView.as_view(), name="servicepost_delete"),
    path("<slug:slug>/deactivate/", deactivate_service_post, name="deactivate_service_post"),
]

