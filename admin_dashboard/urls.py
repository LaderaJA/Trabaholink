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
    path('moderated-words/', ModeratedWordListView.as_view(), name='moderated_word_list'),
    path('moderated-words/add/', ModeratedWordCreateView.as_view(), name='moderated_word_create'),
    path('moderated-words/<int:pk>/edit/', ModeratedWordUpdateView.as_view(), name='moderated_word_update'),
    path('moderated-words/<int:pk>/delete/', ModeratedWordDeleteView.as_view(), name='moderated_word_delete'),

    # Admin Announcement Management
    path('admin-announcements/', AnnouncementSummaryView.as_view(), name='admin_announcement_list'),
    path('admin-announcements/create/', AnnouncementCreateView.as_view(), name='admin_announcement_create'),
    path('admin-announcements/edit/<int:pk>/', AnnouncementUpdateView.as_view(), name='admin_announcement_edit'),
    path('admin-announcements/delete/<int:pk>/', AnnouncementDeleteView.as_view(), name='admin_announcement_delete'),

    # Pending Skills Management
    path('user/<int:pk>/pending_skills/', views.PendingSkillListView.as_view(), name='pending_skill_list'),
    path('skill/<int:pk>/update/', views.PendingSkillUpdateView.as_view(), name='pending_skill_update'),
]
