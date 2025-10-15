from users.views import (
    RegisterView, UserLoginView, UserLogoutView, UserProfileDetailView,
    UserProfileUpdateView, UserProfileDeleteView, ChangePasswordView,
    PrivacySettingsView, SkillVerificationView, search_users,
    VerificationStartView, VerificationStep1View, VerificationStep2View,
    VerificationStep3View, VerificationStep4View, VerificationPendingView,
    VerificationSuccessView, VerificationFailedView
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
    path('profile/<int:pk>/edit/', UserProfileUpdateView.as_view(), name='profile_edit'),
    path('profile/<int:pk>/delete/', UserProfileDeleteView.as_view(), name='profile_delete'),
    path('change_password/', ChangePasswordView.as_view(), name='change_password'),
    path('privacy_settings/', PrivacySettingsView.as_view(), name='privacy_settings'),

    # Password Reset Views (Django built-in)
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    path('submit/', SkillVerificationView.as_view(), name='submit_skill_verification'),
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
    
    # User Search API
    path('api/search/', search_users, name='user_search_api'),
    
    # eKYC Verification URLs
    path('verification/start/', VerificationStartView.as_view(), name='ekyc_start'),
    path('verification/step1/', VerificationStep1View.as_view(), name='ekyc_step1'),
    path('verification/step2/', VerificationStep2View.as_view(), name='ekyc_step2'),
    path('verification/step3/', VerificationStep3View.as_view(), name='ekyc_step3'),
    path('verification/step4/', VerificationStep4View.as_view(), name='ekyc_step4'),
    path('verification/pending/', VerificationPendingView.as_view(), name='ekyc_pending'),
    path('verification/success/', VerificationSuccessView.as_view(), name='ekyc_success'),
    path('verification/failed/', VerificationFailedView.as_view(), name='ekyc_failed'),
]
