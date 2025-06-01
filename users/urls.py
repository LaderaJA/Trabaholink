from users.views import (
    RegisterView, UserLoginView, UserLogoutView, UserProfileDetailView,
    UserProfileUpdateView, UserProfileDeleteView, ChangePasswordView,
    PrivacySettingsView, submit_skill_verification
)
from . import views
from django.urls import path
from django.contrib.auth import views as auth_views
from .views import UserLocationUpdateView, IdentityVerificationView, SkipIdentityVerificationView


urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('profile/<int:pk>/', UserProfileDetailView.as_view(), name='profile'),
    path('profile/edit/', UserProfileUpdateView.as_view(), name='profile_edit'),
    path('profile/<int:pk>/delete/', UserProfileDeleteView.as_view(), name='profile_delete'),
    path('change_password/', ChangePasswordView.as_view(), name='change_password'),
    path('privacy_settings/', PrivacySettingsView.as_view(), name='privacy_settings'),

    # Password Reset Views (Django built-in)
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    path('submit/', views.submit_skill_verification, name='submit_skill_verification'),
    path('skill/<int:pk>/', views.SkillDetailView.as_view(), name='skill_detail'),
    path('skill/<int:pk>/edit/', views.SkillUpdateView.as_view(), name='skill_edit'),
    path('skill/<int:pk>/delete/', views.SkillDeleteView.as_view(), name='skill_delete'),

    path('gallery/add/', views.CompletedJobGalleryCreateView.as_view(), name='gallery_add'),
    path('gallery/<int:pk>/edit/', views.CompletedJobGalleryUpdateView.as_view(), name='gallery_edit'),
    path('gallery/<int:pk>/delete/', views.CompletedJobGalleryDeleteView.as_view(), name='gallery_delete'),

    path('set-location/', UserLocationUpdateView.as_view(), name="set_location"),

    # Identity Verification Views
    path('verify-identity/<int:pk>', IdentityVerificationView.as_view(), name='identity_verification'),
    path('verify-identity/skip/', SkipIdentityVerificationView.as_view(), name='skip_identity_verification'),
]
