from django.urls import path
from . import views
from .views import (ModeratedWordListView, ModeratedWordCreateView, ModeratedWordUpdateView, ModeratedWordDeleteView,
                     AnnouncementSummaryView, AnnouncementCreateView, AnnouncementUpdateView, AnnouncementDeleteView)
from users.views import UserLogoutView  

app_name = 'admin_dashboard'

urlpatterns = [
    path('', views.DashboardMainView.as_view(), name='dashboard_main'),
    # User Management
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user_detail'),
    path('users/<int:pk>/delete/', views.UserDeleteView.as_view(), name='user_delete'),
    path('logout/', UserLogoutView.as_view(), name='logout'),

    # Report Management
    path('reports/', views.ReportListView.as_view(), name='report_list'),
    path('reports/<int:pk>/', views.ReportDetailView.as_view(), name='report_detail'),
    path('reports/<int:pk>/resolve/', views.resolve_report, name='resolve_report'),
    path('submit-report/', views.submit_report, name='submit_report'),
    path('update-report-status/', views.update_report_status, name='update_report_status'),

    # Flagged Chats Management
    path('flagged-chats/', views.FlaggedChatListView.as_view(), name='flagged_chat_list'),
    path('flagged-chats/<int:pk>/', views.FlaggedChatDetailView.as_view(), name='flagged_chat_detail'),
    path('moderation/chats/<int:pk>/resolve/', views.resolve_flagged_chat, name='resolve_flagged_chat'),
    path('moderation/chats/<int:pk>/delete/', views.delete_flagged_chat, name='delete_flagged_chat'),
    path('moderated-words/', ModeratedWordListView.as_view(), name='moderated_word_list'),
    path('moderated-words/add/', ModeratedWordCreateView.as_view(), name='moderated_word_create'),
    path('moderated-words/<int:pk>/edit/', ModeratedWordUpdateView.as_view(), name='moderated_word_update'),
    path('moderated-words/<int:pk>/delete/', ModeratedWordDeleteView.as_view(), name='moderated_word_delete'),

    # Admin Announcement Management
    path('admin-announcements/', AnnouncementSummaryView.as_view(), name='admin_announcement_list'),
    path('admin-announcements/create/', AnnouncementCreateView.as_view(), name='admin_announcement_create'),
    path('admin-announcements/edit/<int:pk>/', AnnouncementUpdateView.as_view(), name='admin_announcement_update'),
    path('admin-announcements/delete/<int:pk>/', AnnouncementDeleteView.as_view(), name='admin_announcement_delete'),
    path('announcements/<int:pk>/toggle/', views.toggle_announcement_status, name='toggle_announcement_status'),
    path('announcements/<int:pk>/details/', views.get_announcement_details, name='get_announcement_details'),

    # User Verification Management
    path('identity-verifications/', views.UserVerificationListView.as_view(), name='user_verification_list'),
    path('identity-verifications/<int:pk>/approve/', views.approve_identity_verification, name='approve_identity_verification'),
    path('identity-verifications/<int:pk>/reject/', views.reject_identity_verification, name='reject_identity_verification'),
    path('skill/<int:pk>/update/', views.PendingSkillUpdateView.as_view(), name='pending_skill_update'),
    
    # New AJAX endpoints
    path('users/<int:pk>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),
    path('users/<int:pk>/send-warning/', views.send_user_warning, name='send_user_warning'),
    path('users/<int:pk>/suspend/', views.suspend_user, name='suspend_user'),
    path('users/<int:pk>/ban/', views.ban_user, name='ban_user'),
    path('moderation/words/<int:pk>/toggle/', views.toggle_word_status, name='toggle_word_status'),
    
    # Job Management
    path('jobs/', views.JobListView.as_view(), name='job_list'),
    path('jobs/<int:pk>/', views.JobDetailView.as_view(), name='job_detail'),
    path('jobs/<int:pk>/toggle/', views.toggle_job_status, name='toggle_job_status'),
    path('jobs/<int:pk>/delete/', views.delete_job, name='delete_job'),
    path('jobs/<int:pk>/archive/', views.archive_job, name='archive_job'),
    path('jobs/<int:pk>/flag/', views.flag_job, name='flag_job'),
    
    # Service Management
    path('services/', views.ServiceListView.as_view(), name='service_list'),
    path('services/<int:pk>/', views.ServiceDetailView.as_view(), name='service_detail'),
    path('services/<int:pk>/approve/', views.approve_service, name='approve_service'),
    path('services/<int:pk>/reject/', views.reject_service, name='reject_service'),
    path('services/<int:pk>/flag/', views.flag_service, name='flag_service'),
    path('services/<int:pk>/delete/', views.delete_service_admin, name='delete_service_admin'),
    
    # Report Detail Actions
    path('reports/<int:pk>/delete-content/', views.delete_reported_content, name='delete_reported_content'),
    path('reports/<int:pk>/save-notes/', views.save_report_notes, name='save_report_notes'),
    
    # Announcement Detail
    path('admin-announcements/<int:pk>/', views.AnnouncementDetailView.as_view(), name='admin_announcement_detail'),
    path('announcements/<int:pk>/republish/', views.republish_announcement, name='republish_announcement'),
    path('announcements/<int:pk>/duplicate/', views.duplicate_announcement, name='duplicate_announcement'),
    
    # Skill Verification Management
    path('skill-verifications/', views.SkillVerificationListView.as_view(), name='skill_verification_list'),
    path('skill-verifications/<int:pk>/', views.SkillVerificationDetailView.as_view(), name='skill_verification_detail'),
    path('skill-verifications/<int:pk>/approve/', views.approve_skill_verification, name='approve_skill_verification'),
    path('skill-verifications/<int:pk>/reject/', views.reject_skill_verification, name='reject_skill_verification'),
    
    # Settings
    path('settings/', views.SettingsView.as_view(), name='settings'),
]
