from django.urls import path
from .views import (
    ServicePostListView,
    ServicePostDetailView,
    ServicePostCreateView,
    ServicePostUpdateView,
    ServicePostDeleteView,
    MyServicesListView,
    deactivate_service_post,
    # Review views
    create_service_review,
    update_service_review,
    delete_service_review,
    report_service_review,
    moderate_service_review,
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
    
    # Review URLs
    path("<slug:slug>/review/create/", create_service_review, name="review_create"),
    path("review/<int:review_id>/edit/", update_service_review, name="review_update"),
    path("review/<int:review_id>/delete/", delete_service_review, name="review_delete"),
    path("review/<int:review_id>/report/", report_service_review, name="review_report"),
    path("review/<int:review_id>/moderate/", moderate_service_review, name="review_moderate"),
]

