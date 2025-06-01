from django.urls import path
from .views import CombinedPostListView

app_name = "posts"

urlpatterns = [
    path("", CombinedPostListView.as_view(), name="combined_list"),
]