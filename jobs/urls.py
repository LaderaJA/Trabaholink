from django.urls import path
from django.views.generic import TemplateView
from . import views
from .views import (
    JobListView, JobDetailView, JobCreateView, JobUpdateView, JobDeleteView, 
    JobApplicationDetailView, JobApplicationUpdateView, JobApplicationDeleteView, 
    JobApplicationCreateView, ContractDetailView, set_user_location, JobApplicationHireView, 
    JobApplicationDenyView, ContractUpdateView, ContractDraftUpdateView, 
    finalize_contract, cancel_contract, accept_contract, EmployerDashboardView, WorkerDashboardView,
    # JobOfferDetailView, accept_job_offer, reject_job_offer, create_job_offer,  # DEPRECATED
    ContractSignView,
    HomePageView, reconsider_application, FAQView, TermsOfServiceView, PrivacyPolicyView,
    # New redesigned workflow views
    accept_application_new, ContractNegotiationView, accept_contract_terms,
    JobTrackingView, post_progress_update, mark_job_completed, end_job, oppose_job_completion, feedback_form,
    ContractFeedbackDetailView,
    start_contract_work, employer_applications_view, employer_contracts_view, worker_applications_view, worker_contracts_view
)
from .views_availability import manage_availability, get_availability_api, check_availability_conflicts


app_name = "jobs"

urlpatterns = [
    path('', HomePageView.as_view(), name="home"),  
    path('jobs/', JobListView.as_view(), name="job_list"),
    path('faq/', FAQView.as_view(), name="faq"),
    path('terms-of-service/', TermsOfServiceView.as_view(), name="terms_of_service"),
    path('privacy-policy/', PrivacyPolicyView.as_view(), name="privacy_policy"),
    path('set-location/', set_user_location, name='set_user_location'),
    
    # Dashboard URLs
    path('dashboard/employer/', EmployerDashboardView.as_view(), name="employer_dashboard"),
    path('dashboard/worker/', WorkerDashboardView.as_view(), name="worker_dashboard"),
    
    # Job URLs
    path('<int:pk>/', JobDetailView.as_view(), name="job_detail"),
    path('create/', JobCreateView.as_view(), name="job_create"),
    path('<int:pk>/edit/', JobUpdateView.as_view(), name="job_edit"),
    path('<int:pk>/delete/', JobDeleteView.as_view(), name="job_delete"),
    path('<int:pk>/apply/', JobApplicationCreateView.as_view(), name="job_apply"),
    
    # Application URLs
    path('applications/<int:pk>/deny/', views.deny_application, name='deny_application'),
    path('job_application/<int:pk>/', views.JobApplicationDetailView.as_view(), name='job_application_detail'),
    path('job_application/<int:pk>/edit/', views.JobApplicationUpdateView.as_view(), name='job_application_edit'),
    path('job_application/<int:pk>/delete/', views.JobApplicationDeleteView.as_view(), name='job_application_delete'),
    path('application/<int:pk>/hire/', JobApplicationHireView.as_view(), name="job_application_hire"),
    path('application/<int:pk>/deny/', JobApplicationDenyView.as_view(), name="job_application_deny"),
    path('application/<int:pk>/reconsider/', reconsider_application, name="reconsider_application"),
    
    # Offer URLs - DEPRECATED (use new workflow instead)
    # path('application/<int:application_pk>/offer/create/', create_job_offer, name="create_job_offer"),
    # path('offer/<int:pk>/', JobOfferDetailView.as_view(), name="job_offer_detail"),
    # path('offer/<int:pk>/accept/', accept_job_offer, name="accept_job_offer"),
    # path('offer/<int:pk>/reject/', reject_job_offer, name="reject_job_offer"),
    
    # Contract URLs
    path('contract/<int:pk>/', ContractDetailView.as_view(), name="contract_detail"),
    path('contract/<int:pk>/sign/', ContractSignView.as_view(), name="contract_sign"),
    path('contract/<int:pk>/edit/', ContractUpdateView.as_view(), name="contract_edit"),
    path('contract/<int:pk>/draft/edit/', ContractDraftUpdateView.as_view(), name="contract_draft_edit"),
    path('contract/<int:pk>/draft/', ContractDetailView.as_view(), name="contract_draft_detail"),
    path('contract/<int:pk>/cancel/', cancel_contract, name="contract_cancel"),
    path('contract/<int:pk>/accept/', accept_contract, name="accept_contract"),
    path('contract/<int:pk>/finalize/', finalize_contract, name="finalize_contract"),
    
    # New redesigned workflow URLs
    path('application/<int:pk>/accept-new/', accept_application_new, name="accept_application_new"),
    path('contract/<int:pk>/negotiation/', ContractNegotiationView.as_view(), name="contract_negotiation"),
    path('contract/<int:pk>/accept-terms/', accept_contract_terms, name="accept_contract_terms"),
    path('contract/<int:pk>/tracking/', JobTrackingView.as_view(), name="job_tracking"),
    path('contract/<int:pk>/start/', start_contract_work, name="start_contract_work"),
    path('contract/<int:contract_pk>/progress/post/', post_progress_update, name="post_progress_update"),
    path('contract/<int:pk>/mark-completed/', mark_job_completed, name="mark_job_completed"),
    path('contract/<int:pk>/end-job/', end_job, name="end_job"),
    path('contract/<int:pk>/oppose-completion/', oppose_job_completion, name="oppose_job_completion"),
    path('contract/<int:contract_pk>/feedback/', feedback_form, name="feedback_form"),
    path('contract/<int:pk>/feedback/view/', ContractFeedbackDetailView.as_view(), name="contract_feedback_detail"),
    
    # Dashboard sub-pages
    path('employer/applications/', employer_applications_view, name="employer_applications"),
    path('employer/contracts/', employer_contracts_view, name="employer_contracts"),
    path('worker/applications/', worker_applications_view, name="worker_applications"),
    path('worker/contracts/', worker_contracts_view, name="worker_contracts"),
    
    # Calendar and Schedule APIs
    path('api/worker/calendar/', views.worker_calendar_api, name="worker_calendar_api"),
    path('api/schedule/check-conflict/', views.check_contract_conflict, name="api_check_conflict"),
    
    # Worker Availability Management
    path('availability/manage/', manage_availability, name="manage_availability"),
    path('api/availability/get/', get_availability_api, name="get_availability_api"),
    path('api/availability/check-conflicts/', check_availability_conflicts, name="check_availability_conflicts"),
    
    # Job Status Toggle
    path('<int:job_id>/toggle-status/', views.toggle_job_status, name="toggle_job_status"),
    
    # Map demo
    path('map-demo/', TemplateView.as_view(template_name='jobs/map_bacoor_only.html'), name='map_demo'),
]
