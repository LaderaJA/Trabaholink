from django.urls import path
from . import views
from .views import HomePageView, JobListView, JobCreateView, JobUpdateView, JobDeleteView, JobDetailView, JobApplicationCreateView, ContractDetailView, set_user_location, JobApplicationHireView, JobApplicationDenyView, ContractUpdateView, ProgressLogCreateView, ContractDraftUpdateView, finalize_contract, cancel_contract, accept_contract


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
    path('contract/<int:pk>/edit/', ContractUpdateView.as_view(), name="contract_edit"),
    path('contract/<int:contract_pk>/progresslog/add/', ProgressLogCreateView.as_view(), name="progresslog_add"),
    path('contract/<int:pk>/', ContractDetailView.as_view(), name="contract_detail"),
    path('applications/<int:pk>/deny/', views.deny_application, name='deny_application'),
    path('job_application/<int:pk>/', views.JobApplicationDetailView.as_view(), name='job_application_detail'),
    path('job_application/<int:pk>/edit/', views.JobApplicationUpdateView.as_view(), name='job_application_edit'),
    path('job_application/<int:pk>/delete/', views.JobApplicationDeleteView.as_view(), name='job_application_delete'),
    path('application/<int:pk>/hire/', JobApplicationHireView.as_view(), name="job_application_hire"),
    path('application/<int:pk>/deny/', JobApplicationDenyView.as_view(), name="job_application_deny"),
    path('contract/<int:pk>/draft/edit/', ContractDraftUpdateView.as_view(), name="contract_draft_edit"),
    path('contract/<int:pk>/draft/', ContractDetailView.as_view(), name="contract_draft_detail"),
    path('contract/<int:pk>/cancel/', cancel_contract, name="contract_cancel"),
    path('contract/<int:pk>/accept/', accept_contract, name="accept_contract"),
    path('contract/<int:pk>/finalize/', finalize_contract, name="finalize_contract"),
]

