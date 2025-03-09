from django.urls import path
from .views import RegisterView, UserLoginView, UserLogoutView, UserProfileDetailView, UserProfileUpdateView, UserProfileDeleteView, ChangePasswordView, PrivacySettingsView

from django.contrib.auth import views as auth_views

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('profile/', UserProfileDetailView.as_view(), name='profile'),
    path('profile/edit/', UserProfileUpdateView.as_view(), name='profile_edit'),
    path('profile/delete/', UserProfileDeleteView.as_view(), name='profile_delete'),
    path('change_password/', ChangePasswordView.as_view(), name='change_password'),
    path('privacy_settings/', PrivacySettingsView.as_view(), name='privacy_settings'),

    # Password Reset Views (Django built-in)
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
]
