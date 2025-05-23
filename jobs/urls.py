from django.urls import path
from . import views
from .views import HomePageView, JobListView, JobCreateView, JobUpdateView, JobDeleteView, JobDetailView, JobApplicationCreateView, ContractDetailView, set_user_location


app_name = "jobs"

urlpatterns = [
    path('', HomePageView.as_view(), name="home"),  
    path('jobs/', JobListView.as_view(), name="job_list"),
    path('set-location/', set_user_location, name='set_user_location'),
    path('<int:pk>/', JobDetailView.as_view(), name="job_detail"),
    path('create/', JobCreateView.as_view(), name="job_create"),
    path('<int:pk>/edit/', JobUpdateView.as_view(), name="job_edit"),
    path('<int:pk>/delete/', JobDeleteView.as_view(), name="job_delete"),
    path('<int:pk>/apply/', JobApplicationCreateView.as_view(), name="job_apply"),
    path('contract/<int:pk>/', ContractDetailView.as_view(), name="contract_detail"),
    path('applications/<int:pk>/deny/', views.deny_application, name='deny_application'),
]

