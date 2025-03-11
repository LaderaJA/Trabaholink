from django.urls import path
from .views import AnnouncementListView, AnnouncementDetailView, AnnouncementCreateView

urlpatterns = [
    path("", AnnouncementListView.as_view(), name="announcement_list"),
    path("<int:pk>/", AnnouncementDetailView.as_view(), name="announcement_detail"),
    path("create/", AnnouncementCreateView.as_view(), name="announcement_create"),
]
